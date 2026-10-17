"""Lazy, synchronous Gemini transport; tool execution belongs to the harness."""

import math
from types import TracebackType

from google import genai
from google.genai import errors, types
import httpx

from app.config import Settings, get_settings


_MESSAGES = {
    "missing_api_key": "Gemini não configurado. Defina GEMINI_API_KEY no ambiente do backend.",
    "authentication_error": "A chave do Gemini foi recusada. Confira GEMINI_API_KEY no backend.",
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


class GeminiClient:
    """One client per operation/investigation; use ``with`` to release connections.

    Construction and context entry do not create the SDK client or make requests.
    HTTP timeouts apply per request. The orchestrator owns the total
    investigation deadline and the single rate-limit retry specified by the MVP.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings if settings is not None else get_settings()
        self._client: genai.Client | None = None
        self._closed = False

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

    def _get_client(self) -> genai.Client:
        if self._client is None:
            if not self._settings.gemini_configured:
                raise GeminiError("missing_api_key")
            assert self._settings.gemini_api_key is not None
            try:
                self._client = genai.Client(
                    enterprise=False,
                    api_key=self._settings.gemini_api_key.get_secret_value().strip(),
                    http_options=self._http_options(),
                )
            except ValueError:
                raise GeminiError("configuration_error") from None
        return self._client

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
        effective_config = config.model_copy(deep=True) if config is not None else types.GenerateContentConfig()
        effective_config.http_options = self._http_options(timeout_seconds)
        # Function calls must be returned to the harness for validation/execution.
        effective_config.automatic_function_calling = types.AutomaticFunctionCallingConfig(disable=True)
        try:
            return self._get_client().models.generate_content(
                model=self.model,
                contents=contents,
                config=effective_config,
            )
        except errors.APIError as error:
            raise _translate_api_error(error) from None
        except httpx.TimeoutException:
            raise GeminiError("timeout") from None
        except httpx.RequestError:
            raise GeminiError("network_error") from None

    def close(self) -> None:
        self._closed = True
        if self._client is not None:
            client, self._client = self._client, None
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
