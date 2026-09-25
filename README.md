# FarmLab Investigator

MVP acadêmico para importar e validar seis arquivos CSV agrícolas antes de executar análises rastreáveis.

## Pré-requisitos

- Python 3.11 ou superior;
- Node.js 20 ou superior;
- pnpm 10 ou superior.

## Backend

```powershell
cd backend
uv sync --locked
uv run uvicorn app.main:app --reload
```

A API fica disponível em `http://127.0.0.1:8000` e o health check em `http://127.0.0.1:8000/api/health`.

## Frontend

```powershell
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

O Vite abre a interface em `http://127.0.0.1:5173` e encaminha `/api` para o backend local.

## Validação de dados

`POST /api/datasets` recebe os seis CSVs no campo multipart repetido `files`. O pacote pronto é mantido somente em memória.

O `quality_score` começa em 100, desconta 5 pontos por aviso (até 40) e 20 pontos por erro (até 100). O valor é apenas informativo: qualquer erro mantém o pacote bloqueado independentemente da pontuação.

### Fluxo manual da Semana 1

1. Inicie backend e frontend em terminais separados.
2. Abra `http://127.0.0.1:5173`.
3. Selecione os seis CSVs sintéticos de `backend/tests/fixtures/manual/`.
4. Clique em **Validar pacote**.
5. Confirme os quatro talhões, o aviso de produtividade e o botão **Continuar** habilitado.

Essas fixtures são artificiais e pequenas. O pacote acadêmico real da apresentação deve permanecer fora do Git.

## Testes

```powershell
cd backend
uv run pytest

cd ../frontend
pnpm test
pnpm build
```

O escopo atual termina na importação e validação. Ferramentas analíticas, Gemini, harness e relatório ainda não foram implementados.

## Estado atual

Os comandos do frontend e da suíte completa serão adicionados conforme os componentes forem inicializados.

Não coloque `.env`, chaves de API ou CSVs privados no repositório. Use apenas fixtures artificiais pequenas nos testes.
