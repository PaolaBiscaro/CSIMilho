# FarmLab Investigator

MVP acadêmico para importar e validar sete arquivos CSV agrícolas, com foco descritivo em análise de solo, antes de executar análises rastreáveis.

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

`POST /api/datasets` deve receber os sete CSVs no campo multipart repetido `files`. O pacote pronto é mantido somente em memória.

Arquivos obrigatórios:

1. `fields.csv`;
2. `ndvi_metadata.csv`;
3. `service_orders.csv`;
4. `service_orders_fields.csv`;
5. `LAYER_MAP_PLANTING.csv`;
6. `LAYER_MAP_FERTILIZATION.csv`;
7. `soil_analysis.csv`.

`soil_analysis.csv` é tratado no escopo geral do dataset. Ele não possui chave ou coordenada para ligar amostras a talhões. As colunas sem sufixo são chamadas de **Conjunto 1** e as colunas `_2`, de **Conjunto 2**, sem presumir profundidade.

O `quality_score` começa em 100, desconta 5 pontos por aviso (até 40) e 20 pontos por erro (até 100). O valor é apenas informativo: qualquer erro mantém o pacote bloqueado independentemente da pontuação.

### Fluxo manual da Semana 1

1. Inicie backend e frontend em terminais separados.
2. Abra `http://127.0.0.1:5173`.
3. Selecione os sete CSVs sintéticos de `backend/tests/fixtures/manual/`.
4. Clique em **Validar pacote**.
5. Confirme os quatro talhões, a quantidade de amostras de solo, os avisos e o botão **Continuar** habilitado.

Essas fixtures são artificiais e pequenas. O pacote acadêmico real da apresentação deve permanecer fora do Git.

## Testes

```powershell
cd backend
uv run pytest

cd ../frontend
pnpm test
pnpm build
```

## Identidade visual

A identidade usa `#895129` como cor principal. Os demais tons, cores semânticas e regras de contraste ficam centralizados em `frontend/src/styles/tokens.css`, conforme o `SPEC.md`.

O layout segue uma linguagem de dashboard: aplicação sobre canvas claro, cabeçalho horizontal, navegação em pílulas e grade de cards brancos. As referências visuais orientam composição e densidade, mas a paleta marrom do FarmLab permanece obrigatória.

## Comparação e gráficos locais — Semana 2

A tela **Comparação** usa os pares retornados pelo upload, atualiza a pergunta ao trocar os talhões e mostra os cinco critérios e as análises disponíveis. Pares com finalidade ou cultura incompatível são bloqueados; a ordem inversa dos pares válidos é permitida.

Com `APP_ENV=development` (padrão), a comparação consulta `POST /api/diagnostics/tools`. Este endpoint executa somente as sete ferramentas determinísticas do registry e retorna uma evidência tipada. Ele responde `404` nos demais ambientes, incluindo `presentation` e `production`; não aceita caminhos ou DataFrames e não chama serviços externos.

Exemplo de corpo após importar um pacote (substitua os IDs pelos retornados pela API):

```json
{
  "tool": "validate_comparison",
  "arguments": {
    "dataset_id": "UUID_DO_UPLOAD",
    "target_field_id": "ID_ALVO",
    "reference_field_id": "ID_REFERENCIA",
    "period": "full_season"
  }
}
```

O registry está em `backend/app/harness/registry.py`; apesar do diretório previsto no SPEC, ele é apenas um catálogo e executor local, sem harness de IA. As seis análises estão em `backend/app/analytics/`. Parâmetros de período também aceitam `{ "start": "2025-01-01", "end": "2025-02-01" }`; a interface desta etapa oferece a safra completa.

Para conferir a interface:

1. Abra **Comparação** sem upload para explorar os pares fictícios, ou importe os sete CSVs artificiais e clique em **Continuar** para consultar a comparabilidade local.
2. Verifique que Grão × Silagem mantém o botão bloqueado.
3. Clique em **Ver gráficos demonstrativos** com um par permitido.
4. Explore **Solo**: distribuição, Conjunto 1 × Conjunto 2 e composição de textura; altere família, métrica e conjunto.
5. Abra **Gráfico NDVI** para a trajetória pareada. Todos os gráficos possuem tabela acessível, legenda/tooltip, contagem, unidade e fonte.

A tela **Investigação** permanece uma prévia identificada, com dados fictícios de `frontend/src/mocks/analytics-preview.json`, derivados das fixtures manuais e conferidos pelos testes do backend. Os gráficos usam Chart.js e apenas apresentam os valores prontos; não calculam estatísticas no navegador e não representam o pacote importado. As instâncias anteriores são destruídas ao mudar filtro, aba ou página.

Solo mantém escopo geral do dataset. Unidades desconhecidas aparecem explicitamente, e não há mapa, tendência temporal, profundidade ou classificação agronômica inventada. A textura usa percentuais normalizados no backend somente para amostras cuja soma original esteja entre 95 e 105; a soma original também aparece na tabela.

## Estado atual

W2.01–W2.14 estão concluídas. O pacote real foi validado em 2026-10-13: oito amostras de solo, 29 datas NDVI pareadas, gap −0,024985204049, população 61.306,27/63.629,03 plantas/ha e calagem 57,327136%/97,500150% para Grão 4.0 × Grão Convencional. As diferenças frente às aproximações do protótipo foram investigadas e registradas em [BASELINE_W2.md](BASELINE_W2.md). Gemini, harness de IA, investigação real integrada e relatório ainda não foram implementados.

Verificação de 2026-10-13: **163 testes Pytest com o pacote real**, **25 testes Vitest** e build Vite aprovados. A revisão de interface da W2.13 confirmou importação de fixtures, comparação e gráficos responsivos sem erros de console. O backend mantém um aviso de depreciação já existente de Starlette/httpx.

Para repetir a validação real, sem copiar os CSVs para o repositório:

```sh
cd backend
FARMLAB_REAL_DATA_DIR='/Users/lucashygidio/Downloads/FarmLab' .venv/bin/python -m pytest tests/test_real_baseline.py
```

O teste encontra os sete nomes recursivamente, confere seus hashes e compara as seis análises com cálculos independentes diretamente dos arquivos. Sem `FARMLAB_REAL_DATA_DIR`, os nove testes reais são ignorados explicitamente; arquivos ausentes, duplicados ou alterados fazem a validação falhar quando a variável é definida. Os gráficos da investigação continuam usando as fixtures locais identificadas na interface.

Não coloque `.env`, chaves de API ou CSVs privados no repositório. Use apenas fixtures artificiais pequenas nos testes.
