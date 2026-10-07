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

## Prévias navegáveis

As abas **Comparação** e **Investigação** podem ser abertas para revisão visual antes da implementação analítica. Elas usam somente dados locais mockados e mostram o selo **Prévia · dados demonstrativos**. A prévia não chama endpoints de investigação, não executa cálculos e não representa resposta do Gemini.

- **Dados:** fluxo real de upload e validação;
- **Comparação:** formulário e indicadores demonstrativos clicáveis;
- **Investigação:** cards, gráfico ilustrativo e abas internas demonstrativas.

O gráfico atual é propositalmente uma prévia simples. Para as Semanas 2 e 4 está previsto um dashboard analítico mais completo, com prioridade para **Solo**: cards de qualidade, distribuição por métrica, comparação pareada entre Conjunto 1 e Conjunto 2, composição de textura, filtros, tooltips e tabelas acessíveis. Esses gráficos só serão ligados quando as evidências determinísticas reais estiverem disponíveis.

Como o arquivo de solo atual não possui coordenada, data ou profundidade, o projeto não prevê mapa, tendência temporal nem perfil de camadas para essas amostras. A interface também não inventará unidades ou faixas agronômicas de suficiência.

O reajuste pós-Semana 1 (`R1.01` a `R1.06`) está concluído: a importação exige sete arquivos, normaliza `soil_analysis.csv` no escopo geral do dataset e apresenta sua disponibilidade sem associar amostras a talhões. Ferramentas analíticas, Gemini, harness e relatório ainda não foram implementados.

## Estado atual

O reajuste visual `R1.07`–`R1.08` está concluído antes de `W2.01`: o frontend usa o novo shell de dashboard e oferece prévias clicáveis de Comparação e Investigação, sempre identificadas como demonstrativas. A implementação analítica continua pendente. A regressão final registrou 56 testes Pytest e 7 testes Vitest aprovados, build Vite concluído, navegação responsiva validada e o pacote real reconhecido com oito amostras de solo.

Não coloque `.env`, chaves de API ou CSVs privados no repositório. Use apenas fixtures artificiais pequenas nos testes.
