# Versão congelada da apresentação

**Identificação:** `apresentacao-w4-2026-10-18` (tag Git local, na branch `feat/lorena`). Esta entrega reúne W4.01–W4.15 sobre a base W3 `20b0e6f`. O commit apontado pela tag contém este registro. Não houve push.

## Validação final — 18/10/2026

| Verificação | Resultado |
| --- | --- |
| Backend completo, com build presente | **880 passaram**, 9 ignorados, 3 avisos existentes; 47,48 s |
| Frontend completo | **164 passaram**, 16 arquivos de teste |
| Build Vite | Aprovado; 30 módulos |
| Compatibilidade Python | 49 pacotes compatíveis; versões instaladas correspondem ao `uv.lock` |
| Dependências diretas frontend | Versões instaladas correspondem ao `pnpm-lock.yaml` |
| Formatação do diff | `git diff --check` aprovado |
| Dados e segredos no conteúdo versionado | Nenhum `.env` real, dado privado ou relatório local; somente fixtures sintéticas e `.env.example` |

Os nove testes ignorados exigem o pacote acadêmico privado, indisponível neste ambiente. Os três avisos são de depreciação em Starlette/TestClient, AnyIO e google-genai. Não foram atualizadas dependências no congelamento. As suítes usam provedor simulado; os testes reais do Gemini e da interface estão registrados nas W4.13/W4.14.

Comandos finais, executados a partir de seus respectivos diretórios:

```powershell
# frontend
pnpm test
pnpm build

# backend (usar uma nova pasta temporária em cada repetição)
.\.venv\Scripts\python.exe -m pytest --basetemp=.local/pytest-w4-15-freeze-a --tb=short
uv --cache-dir .local/uv-freeze-cache pip check --python .venv/Scripts/python.exe
```

O cache local do uv evita o diretório de cache bloqueado no ambiente restrito. O inventário do frontend foi lido dos `package.json` instalados, pois `pnpm list` encontrou indisponibilidade no banco SQLite do ambiente; os testes e o build funcionaram normalmente.

## Ambiente registrado

| Componente | Versão |
| --- | --- |
| Sistema | Windows 11, build 26300 |
| Python | 3.14.7 |
| Node.js | 24.19.0 |
| pnpm | 11.25.0 |
| uv | 0.12.10 |
| FastAPI / Uvicorn | 0.141.1 / 0.53.0 |
| google-genai / httpx | 2.31.0 / 0.28.1 |
| Pydantic / pydantic-settings | 2.13.5 / 2.15.0 |
| pandas / NumPy / Shapely | 2.3.3 / 2.5.3 / 2.1.2 |
| pytest | 8.4.2 |
| Chart.js | 4.5.1 |
| Vite / Vitest / happy-dom | 7.3.6 / 3.2.7 / 20.14.6 |

O inventário completo dos 49 pacotes Python, dependências diretas frontend e hashes SHA-256 dos manifests, lockfiles e build está em [VERSAO_APRESENTACAO.json](VERSAO_APRESENTACAO.json). Os lockfiles registram a resolução das dependências transitivas.

## Executar a apresentação

Siga [ROTEIRO_DEMONSTRACAO.md](ROTEIRO_DEMONSTRACAO.md). O pacote ensaiado está em `demo-data/apresentacao-sintetica/` e é **sintético**, com sete CSVs e 2.851 bytes. As cópias locais e os relatórios de reserva estão fora do Git; em outra máquina, recrie o pacote a partir de `backend/tests/fixtures/manual/` e gere seus relatórios.

Para reproduzir a versão em outro checkout, use a tag, instale com `uv sync --locked` no backend e `pnpm install --frozen-lockfile` no frontend, configure a chave somente no backend e execute `pnpm build`. A configuração local `.env` e o build não fazem parte do commit. Use um processo FastAPI, `APP_ENV=development` para a comparação e o limite de geração descrito no roteiro.

Os ensaios operacionais da W4.14 ficaram em 60,4 s com Gemini, 42,6 s com fallback sem chave e 59,7 s com fallback por timeout, sem fala humana cronometrada. Ainda cabe ao apresentador ensaiar a fala e abrir manualmente os HTMLs de reserva: o navegador integrado bloqueou a visualização offline por URL `file:`. Não há garantia de latência ou de aceitação de toda resposta futura do modelo; o fallback continua identificado.

## Regra do congelamento

Não adicionar funcionalidades nem atualizar dependências nesta versão sem necessidade crítica. Se surgir uma correção indispensável, registrar o problema, alterar somente o necessário, repetir os testes pertinentes e criar outra identificação de entrega. **Não mover nem sobrescrever esta tag.**

A W4 está encerrada. Este congelamento é local; compartilhar o commit e a tag com o remoto exige uma etapa de publicação separada.
