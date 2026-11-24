"""Lazy, synchronous Gemini transport; tool execution belongs to the harness."""

import math
from queue import Empty, Queue
from threading import Thread
from time import monotonic, sleep
from types import TracebackType
from typing import Callable

from google import genai
from google.genai import errors, types
import httpx

from app.config import Settings, get_settings


_MESSAGES = {
    "missing_api_key": (
        "Gemini não configurado. Defina GEMINI_API_KEY ou uma chave reserva no ambiente do backend."
    ),
    "authentication_error": "As chaves disponíveis do Gemini foram recusadas. Confira a configuração do backend.",
    "permission_denied": "O Gemini negou acesso. Confira as permissões e restrições da chave.",
    "model_not_found": "O modelo do Gemini não está disponível. Confira GEMINI_MODEL e o acesso ao modelo.",
    "rate_limit": "O limite de requisições ou a cota do Gemini foi atingido. Tente novamente mais tarde.",
    "timeout": "O Gemini excedeu o tempo limite da requisição. Tente novamente mais tarde.",
    "unavailable": "O serviço do Gemini está indisponível. Tente novamente mais tarde.",
    "network_error": "Não foi possível comunicar com o Gemini. Confira a conexão de rede.",
    "invalid_request": "O Gemini recusou a requisição. Confira o modelo e os parâmetros enviados.",
    "configuration_error": "Não foi possível configurar o cliente Gemini. Confira a configuração do backend.",
    "api_error": "O Gemini retornou um erro inesperado ao processar a requisição.",
}


class GeminiError(Exception):
    """Safe application error, without provider bodies, prompts or credentials."""

    def __init__(self, code: str, *, status_code: int | None = None) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(_MESSAGES[code])


def _translate_api_error(error: errors.APIError) -> GeminiError:
    # Invalid API keys may arrive as HTTP 400 with a structured ErrorInfo reason.
    payload = error.details
    if isinstance(payload, dict):
        payload = payload.get("error", payload)
    details = payload.get("details", []) if isinstance(payload, dict) else []
    invalid_key = isinstance(details, list) and any(
        isinstance(detail, dict) and detail.get("reason") == "API_KEY_INVALID"
        for detail in details
    )
    if error.code == 401 or (error.code == 400 and invalid_key):
        code = "authentication_error"
    elif error.code == 403:
        code = "permission_denied"
    elif error.code == 404:
        code = "model_not_found"
    elif error.code == 429:
        code = "rate_limit"
    elif error.code in (408, 504):
        code = "timeout"
    elif 500 <= error.code < 600:
        code = "unavailable"
    elif 400 <= error.code < 500:
        code = "invalid_request"
    else:
        code = "api_error"
    return GeminiError(code, status_code=error.code)


_PERMANENT_KEY_ERRORS = frozenset({"authentication_error", "permission_denied", "configuration_error"})
_TRANSIENT_KEY_ERRORS = frozenset({"rate_limit", "timeout", "unavailable", "network_error", "api_error"})
_ROTATABLE_KEY_ERRORS = _PERMANENT_KEY_ERRORS | _TRANSIENT_KEY_ERRORS
# A quota error normally persists for the whole quota window, but short 5xx and
# network failures often disappear on the next request.  After every configured
# key has been tried once, allow one small second round for those failures while
# preserving the investigation's original deadline.
_SHORT_RETRY_ERRORS = frozenset({"timeout", "unavailable", "network_error", "api_error"})
_SHORT_RETRY_DELAY_SECONDS = 1.0
_ATTEMPT_TIMEOUT_SECONDS = 40.0


class GeminiClient:
    """Pool-aware client for one operation/investigation; close it after use.

    Construction and context entry do not create the SDK client or make requests.
    Up to three SDK clients are created lazily, one per configured key. Every
    logical generation starts at the next healthy key. Key-related failures
    rotate within the same call while preserving its remaining timeout.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        progress_sink: Callable[[dict], None] | None = None,
    ) -> None:
        self._settings = settings if settings is not None else get_settings()
        self._keys = self._settings.gemini_api_keys
        self._clients: dict[int, genai.Client] = {}
        self._disabled_slots: set[int] = set()
        self._cooldown_until: dict[int, float] = {}
        self._next_slot = 0
        self._closed = False
        self._progress_sink = progress_sink

    def _emit(self, stage: str, message: str, **details) -> None:
        if self._progress_sink is None:
            return
        try:
            self._progress_sink({"stage": stage, "message": message, **details})
        except Exception:
            # Observability must never cancel or change an analysis.
            pass

    @property
    def model(self) -> str:
        return self._settings.gemini_model

    def _http_options(self, timeout_seconds: float | None = None) -> types.HttpOptions:
        timeout_ms = self._settings.gemini_timeout_seconds * 1000
        if timeout_seconds is not None:
            if (isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float))
                    or not math.isfinite(timeout_seconds) or timeout_seconds <= 0):
                raise ValueError("O timeout da chamada deve ser positivo e finito.")
            timeout_ms = min(timeout_ms, max(1, int(timeout_seconds * 1000)))
        return types.HttpOptions(
            timeout=timeout_ms,
            # Do not let SDK retries multiply the harness's call/time budgets.
            retry_options=types.HttpRetryOptions(attempts=1),
        )

    def _get_client(self, slot: int) -> genai.Client:
        client = self._clients.get(slot)
        if client is None:
            try:
                client = genai.Client(
                    enterprise=False,
                    api_key=self._keys[slot].get_secret_value(),
                    http_options=self._http_options(),
                )
            except ValueError:
                raise GeminiError("configuration_error") from None
            self._clients[slot] = client
        return client

    def _available_slots(self, attempted: set[int], now: float) -> list[int]:
        if not self._keys:
            raise GeminiError("missing_api_key")
        count = len(self._keys)
        ordered = [(self._next_slot + offset) % count for offset in range(count)]
        return [
            slot for slot in ordered
            if slot not in attempted
            and slot not in self._disabled_slots
            and self._cooldown_until.get(slot, 0.0) <= now
        ]

    def _mark_failure(self, slot: int, error: GeminiError, now: float) -> None:
        if error.code in _PERMANENT_KEY_ERRORS:
            self._disabled_slots.add(slot)
        elif error.code in _TRANSIENT_KEY_ERRORS:
            self._cooldown_until[slot] = now + self._settings.gemini_key_cooldown_seconds

    def generate_content(
        self,
        contents: types.ContentListUnion,
        *,
        config: types.GenerateContentConfig | None = None,
        timeout_seconds: float | None = None,
    ) -> types.GenerateContentResponse:
        """Send prepared context/evidence; callers must never supply raw CSVs."""
        if self._closed:
            raise RuntimeError("O cliente Gemini já foi fechado.")
        # Validate before any SDK client is constructed.
        self._http_options(timeout_seconds)
        total_timeout = min(
            float(self._settings.gemini_timeout_seconds),
            float(timeout_seconds) if timeout_seconds is not None else math.inf,
        )
        started = monotonic()
        attempted: set[int] = set()
        last_error: GeminiError | None = None
        short_retry_used = False

        while True:
            remaining = total_timeout - (monotonic() - started)
            if remaining <= 0:
                raise GeminiError("timeout")
            slots = self._available_slots(attempted, monotonic())
            if not slots:
                if (
                    last_error is not None
                    and last_error.code in _SHORT_RETRY_ERRORS
                    and not short_retry_used
                ):
                    remaining = total_timeout - (monotonic() - started)
                    # Never sleep through the public deadline.  A tiny remaining
                    # budget is better reported as the original provider error.
                    delay = min(_SHORT_RETRY_DELAY_SECONDS, max(0.0, remaining / 4))
                    if delay > 0.05:
                        sleep(delay)
                        short_retry_used = True
                        # Cooldown protects later logical calls.  This explicit
                        # retry round is deliberately allowed to probe each key
                        # once more after the short backoff.
                        for attempted_slot in attempted:
                            self._cooldown_until.pop(attempted_slot, None)
                        attempted.clear()
                        continue
                if last_error is not None:
                    raise last_error
                # All configured keys are disabled or cooling down from a prior call.
                raise GeminiError("unavailable")
            slot = slots[0]
            attempted.add(slot)
            self._next_slot = (slot + 1) % len(self._keys)
            self._emit(
                "gemini_key_attempt",
                f"Consultando o Gemini com a chave {slot + 1} de {len(self._keys)}.",
                key_slot=slot + 1,
                configured_key_count=len(self._keys),
            )

            effective_config = (
                config.model_copy(deep=True) if config is not None else types.GenerateContentConfig()
            )
            attempt_timeout = min(remaining, _ATTEMPT_TIMEOUT_SECONDS)
            effective_config.http_options = self._http_options(attempt_timeout)
            # Function calls must be returned to the harness for validation/execution.
            effective_config.automatic_function_calling = types.AutomaticFunctionCallingConfig(disable=True)
            try:
                outcome: Queue[tuple[bool, object]] = Queue(maxsize=1)

                def invoke() -> None:
                    try:
                        value = self._get_client(slot).models.generate_content(
                            model=self.model,
                            contents=contents,
                            config=effective_config,
                        )
                        outcome.put((True, value))
                    except BaseException as error:
                        outcome.put((False, error))

                Thread(target=invoke, daemon=True).start()
                try:
                    succeeded, value = outcome.get(timeout=attempt_timeout)
                except Empty:
                    raise GeminiError("timeout") from None
                if not succeeded:
                    raise value
                result = value
                self._emit(
                    "gemini_key_succeeded",
                    f"A chave {slot + 1} respondeu corretamente.",
                    key_slot=slot + 1,
                    configured_key_count=len(self._keys),
                )
                return result
            except errors.APIError as error:
                translated = _translate_api_error(error)
            except httpx.TimeoutException:
                translated = GeminiError("timeout")
            except httpx.RequestError:
                translated = GeminiError("network_error")
            except GeminiError as error:
                translated = error

            last_error = translated
            self._emit(
                "gemini_key_failed",
                f"A chave {slot + 1} falhou ({translated.code}).",
                key_slot=slot + 1,
                configured_key_count=len(self._keys),
                error_code=translated.code,
            )
            if translated.code not in _ROTATABLE_KEY_ERRORS:
                raise translated
            self._mark_failure(slot, translated, monotonic())

    def close(self) -> None:
        self._closed = True
        clients, self._clients = list(self._clients.values()), {}
        for client in clients:
            client.close()

    def __enter__(self) -> "GeminiClient":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
