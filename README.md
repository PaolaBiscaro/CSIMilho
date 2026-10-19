# FarmLab Investigator

MVP acadêmico para importar e validar sete arquivos CSV agrícolas, com foco descritivo em análise de solo, antes de executar análises rastreáveis.

**W4 concluída e congelada:** tag local `apresentacao-w4-2026-10-18`, na branch `feat/lorena`. Consulte o [registro de congelamento](CONGELAMENTO_APRESENTACAO.md), o [inventário de versões](VERSAO_APRESENTACAO.json) e o [roteiro da demonstração](ROTEIRO_DEMONSTRACAO.md). Validação final: **880 testes backend e 164 frontend passaram**, build aprovado; nove testes privados ignorados e três avisos existentes. Não adicionar funcionalidades após o congelamento sem necessidade crítica. Commit e tag ainda não publicados no remoto.

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

## Apresentação em uma única URL — W4.09

A partir da raiz do projeto, compile a interface e inicie apenas o FastAPI:

```powershell
cd frontend
pnpm build
cd ../backend
$env:APP_ENV = "development"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Abra **http://127.0.0.1:8000/**. JavaScript, CSS, upload, comparação, investigação e download usam esse mesmo servidor. A tela inicial do build foi conferida no navegador. Não é necessário executar `pnpm dev` ou `pnpm preview` para apresentar. Mantenha um processo de backend, pois datasets e relatórios ficam em memória.

`APP_ENV=development` é necessário no fluxo local atual porque a comparação consulta `/api/diagnostics/tools`, restrito a esse ambiente. A configuração não impede servir o build. A chave continua somente no backend; nenhum segredo deve usar o prefixo `VITE_`.

FastAPI encontra `frontend/dist` a partir da localização do código, independentemente do diretório de execução. Sem build, a API continua acessível e a página retorna 503 com a orientação para compilar. Após `pnpm build`, basta recarregar. Repita o build após alterar o frontend; o HTML exige revalidação para carregar os assets atuais.

O fallback de navegação entrega `index.html` para rotas da interface, preservando erros 404/405 da API e documentação. Assets inexistentes continuam 404. Somente a pasta do build é publicada, com bloqueio de caminhos ocultos e tentativas de sair dela. O frontend continua mantendo seu estado apenas em memória: recarregar a página volta à tela inicial, sem recuperar a investigação anterior.

Para desenvolver, mantenha os dois servidores descritos acima: Vite em 5173 com proxy `/api` e FastAPI em 8000. `VITE_API_BASE_URL`, se utilizado, vale apenas no modo de desenvolvimento; o build sempre usa a própria origem.

Verificação de 2026-10-17: **872 testes backend passaram, 9 privados ignorados, 3 avisos existentes (45,78 s); 128 Vitest passaram; build Vite e `git diff --check` aprovados**. Os novos testes cobrem navegação, assets/MIME/cache, ausência de build, caminhos indevidos, isolamento da API e origem de requisições. Com o build presente, o teste integrado percorre upload, comparação, investigação com fallback e download via HTTP na mesma origem, sem acessar o Gemini. Sem build, somente esse teste integrado é ignorado; execute `pnpm build` antes da suíte para verificá-lo.

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

### Teclado e telas menores — W4.10

Use **Tab** para alcançar os controles e **Enter/Espaço** para ativá-los. O link **Pular para o conteúdo** aparece ao receber foco. Ao trocar de página, o título recebe foco; ao validar um pacote, o foco vai ao resultado ou à mensagem de erro. Durante a investigação, o painel de progresso recebe foco fora do formulário ocupado.

Nas abas do resultado, use **setas esquerda/direita**, **Home** e **End**. As tabelas largas têm regiões identificadas, acessíveis por Tab, e podem ser roladas com as setas. Os critérios de comparação mostram suas explicações diretamente. Upload e pergunta possuem instruções associadas, mensagens de status e alertas de erro. Textos auxiliares foram ampliados, campos ganharam bordas mais contrastantes e as abas se distribuem em linhas nas telas menores. A interface respeita movimento reduzido.

Verificação em **2026-10-18**: **132 testes Vitest passaram**, build aprovado e **22 testes HTTP do build passaram**, com os três avisos existentes. Fluxo de fixtures sintéticas conferido no navegador por teclado até o download e nova comparação; seis abas inspecionadas em **390, 820 e 1440 px**, sem estouro horizontal do documento. Tabelas usam rolagem interna. Os contrastes calculados dos textos principais e estados ficaram acima de 5,4:1; bordas de campos em 3,3:1. A leitura para apresentação foi avaliada no navegador desktop, sem projetor físico ou leitor de tela dedicado. Não houve chamada real ao Gemini. Próximo item: **W4.11 — painel de pré-apresentação**.

### Conferir a conexão antes de apresentar — W4.11

Na tela **Dados**, o painel **Antes de apresentar** consulta o backend automaticamente, mesmo sem arquivos importados. **Atualizar status** verifica novamente a configuração, o modelo e a versão. Essa consulta não chama o Gemini: **Configurado · conexão não testada** significa apenas que a chave foi detectada no backend.

Use **Testar Gemini** para fazer uma chamada curta ao modelo, sem enviar o pacote ou iniciar uma investigação. O painel mostra confirmação, latência medida pelo backend (inclusive `0 ms`) ou uma mensagem compreensível de falha; permite repetir o teste. Sem chave, configure `GEMINI_API_KEY` somente no backend, reinicie o servidor se necessário e atualize o status. Não coloque credenciais em variáveis `VITE_*`. O painel preserva o dataset e o estado da investigação.

Verificação em **2026-10-18**: **159 testes Vitest**, **53 testes backend de health/Gemini/build** e build aprovados, com três avisos backend existentes. Sucesso e falhas do Gemini simulados; painel sem chave conferido no navegador em 390, 820 e 1440 px e com atualização por teclado. Nenhuma chamada real ao Gemini nesta etapa. Próximo item: **W4.12 — testar falhas reais**.

### Continuidade após falhas — W4.12

A investigação conclui com **Relatório local · fallback** e um aviso explicando o motivo quando o Gemini falha. O relatório pode ser baixado e uma nova comparação usa o mesmo pacote. O fallback utiliza as evidências disponíveis: uma falha no início pode produzir um relatório mais limitado; uma falha na síntese preserva as análises já calculadas.

| Cenário validado | Comportamento confirmado |
| --- | --- |
| Sem chave | Plano local sem criar cliente do provedor; aviso de chave ausente. |
| Timeout no planejamento ou na síntese | Fallback com aviso de prazo excedido. |
| Limite de uso (429) no planejamento ou na síntese | Uma única repetição e fallback se o erro persistir. |
| JSON ou schema inválido | Uma tentativa de reparo e fallback se a saída continuar inválida. |
| Resposta vazia | Fallback com aviso de resposta inutilizável. |

Os oito cenários HTTP usam o SDK oficial com transporte de rede simulado e arquivos sintéticos, sem consumir a API real. Verificam também o teste de conexão, download, sessão reutilizável e ausência de credenciais/detalhes internos nos resultados. Cinco casos frontend verificam os avisos e uma nova investigação após fallback. Para repetir a matriz, execute em `backend`: `.\.venv\Scripts\python.exe -m pytest tests/test_presentation_failures.py --tb=short`.

Validação da W4.12 em **2026-10-18**: **880 testes backend passaram, 9 privados ignorados e 3 avisos existentes (45,29 s)**; **164 testes Vitest**, build Vite e `git diff --check` aprovados. Nenhuma correção no código de produção foi necessária. Próximo item: **W4.13 — teste ponta a ponta**.

### Teste ponta a ponta — W4.13

Em **2026-10-18**, o build foi recompilado e testado pelo navegador com um processo novo do FastAPI, sem Vite. O pacote foi o conjunto sintético de `backend/tests/fixtures/manual/`: sete arquivos, quatro talhões, duas amostras de solo, qualidade 85/100, zero erros impeditivos e três avisos previstos. Não foram usados arquivos privados.

O teste real de conexão com `gemini-2.5-flash` passou (1.472 ms). A primeira investigação **Grão 4.0 × Grão Convencional** concluiu com origem Gemini, oito chamadas analíticas e sem reparo ou fallback. Foram conferidas as seis abas, os valores de solo, o NDVI (0,5 nos dois talhões, gap zero), as evidências, fontes e limitações. O HTML foi baixado pelo botão da interface: 39.316 bytes e 19 tabelas.

Em **Nova comparação**, os talhões foram invertidos e outra investigação foi executada sem novo upload. A validação rejeitou o relatório do modelo após uma tentativa de reparo; o fallback concluiu com aviso explícito e preservou as sete chamadas analíticas realizadas. O segundo download também passou: 36.443 bytes e 17 tabelas. A sessão continuou disponível para outra comparação. Esse resultado confirma a continuidade do aplicativo, sem garantir que toda resposta futura do modelo passe pela validação.

**Nenhum erro ou aviso de console e nenhum stack trace visível** durante o fluxo. Os dois arquivos baixados foram conferidos por leitura e parser HTML: conteúdo esperado, sem scripts ou recursos externos. A inspeção visual offline ficou fora desta verificação porque o navegador integrado bloqueia URLs `file:`. Capturas, cópias dos relatórios, hashes e console ficam localmente em `backend/.local/w4-13/`, fora do Git. Servidor de teste encerrado. Build e `git diff --check` aprovados; nenhuma correção de produção necessária. Próximo item: **W4.14 — roteiro da demonstração**.

### Roteiro de apresentação — W4.14

O [roteiro da demonstração](ROTEIRO_DEMONSTRACAO.md) reúne preparação, pergunta pronta, sequência de cliques, falas para Gemini/fallback e plano de reserva. O pacote **sintético** está preparado localmente em `demo-data/apresentacao-sintetica/` (sete CSVs, 2.851 bytes); os dois HTMLs de reserva estão em `demo-data/relatorios-reserva/`. Esses arquivos locais são ignorados pelo Git. O pacote acadêmico privado não está disponível nesta cópia.

Ensaios operacionais de 18/10/2026: **60,4 s com Gemini**, **42,6 s com fallback sem chave** e **59,7 s com fallback por timeout**, incluindo as seis abas, download e Nova comparação. Sem erros/avisos de console capturados. A meta de dois minutos foi observada na automação; a fala humana ainda deve ser ensaiada com cronômetro. O roteiro usa limite de 75 s no processo principal e explica o modo local sem alterar `.env`. Próximo item: **W4.15 — congelar a versão da apresentação**.

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

1. Abra **Comparação** sem upload para explorar os pares fictícios.
2. Verifique que Grão × Silagem mantém o botão bloqueado.
3. Clique em **Ver gráficos demonstrativos** com um par permitido.
4. Explore **Solo**: distribuição, Conjunto 1 × Conjunto 2 e composição de textura; altere família, métrica e conjunto.
5. Abra **Gráfico NDVI** para a trajetória pareada. Todos os gráficos possuem tabela acessível, legenda/tooltip, contagem, unidade e fonte.

Sem upload, a tela **Investigação** apresenta uma prévia identificada, com dados fictícios de `frontend/src/mocks/analytics-preview.json`, derivados das fixtures manuais e conferidos pelos testes do backend. Os gráficos usam Chart.js e apenas apresentam os valores prontos; não calculam estatísticas no navegador e não representam o pacote importado. As instâncias anteriores são destruídas ao mudar filtro, aba ou página.

Para investigar um pacote, importe os sete CSVs, clique em **Continuar**, escolha um par permitido e use **Executar investigação**. A aba **Visão geral** apresenta título, resumo, força da evidência e origem Gemini ou fallback. A **Visão de solo** permite consultar qualidade, estatísticas e comparação entre conjuntos, com detalhes em tabelas expansíveis. Em seguida, os cards de achados e recomendações mostram explicações, justificativas e referências às evidências. Abra **Evidências** para consultar valores, unidades, contagens e fontes; **Solo** e **Gráfico NDVI** apresentam os gráficos dos resultados disponíveis. **Métodos** detalha a execução e **Limitações** apresenta as restrições e regras associadas.

Solo mantém escopo geral do dataset. Unidades desconhecidas aparecem explicitamente, e não há mapa, tendência temporal, profundidade ou classificação agronômica inventada. A textura usa percentuais normalizados no backend somente para amostras cuja soma original esteja entre 95 e 105; a soma original também aparece na tabela.

## Estado atual

W2.01–W2.14 e W3.01–W3.15 estão concluídas. O teste real controlado do Gemini foi aprovado em 2026-10-17. A validação HTTP completa da W3.14 passou na execução local informada pelo usuário em 2026-10-16. O pacote real foi validado em 2026-10-13: oito amostras de solo, 29 datas NDVI pareadas, gap −0,024985204049, população 61.306,27/63.629,03 plantas/ha e calagem 57,327136%/97,500150% para Grão 4.0 × Grão Convencional. As diferenças frente às aproximações do protótipo foram investigadas e registradas em [BASELINE_W2.md](BASELINE_W2.md). O endpoint de investigação integra planejamento, síntese, validação, reparo e fallback automático. W4.01–W4.15 estão concluídas e congeladas na tag local apresentacao-w4-2026-10-18: integração completa, testes, roteiro e inventário de versões. Sem push; não adicionar funcionalidades sem necessidade crítica.

Verificação de 2026-10-13: **163 testes Pytest com o pacote real**, **25 testes Vitest** e build Vite aprovados. A revisão de interface da W2.13 confirmou importação de fixtures, comparação e gráficos responsivos sem erros de console. O backend mantém um aviso de depreciação já existente de Starlette/httpx.

Para repetir a validação real, sem copiar os CSVs para o repositório:

```sh
cd backend
FARMLAB_REAL_DATA_DIR='/Users/lucashygidio/Downloads/FarmLab' .venv/bin/python -m pytest tests/test_real_baseline.py
```

O teste encontra os sete nomes recursivamente, confere seus hashes e compara as seis análises com cálculos independentes diretamente dos arquivos. Sem `FARMLAB_REAL_DATA_DIR`, os nove testes reais são ignorados explicitamente; arquivos ausentes, duplicados ou alterados fazem a validação falhar quando a variável é definida. Os gráficos da investigação continuam usando as fixtures locais identificadas na interface.

Não coloque `.env`, chaves de API ou CSVs privados no repositório. Use apenas fixtures artificiais pequenas nos testes.

## Cliente Gemini — W3.01

`uv sync --locked` instala o SDK oficial `google-genai` (2.31.0 no lockfile). O cliente síncrono está em `backend/app/harness/gemini_client.py`, seguindo a [documentação oficial do SDK](https://googleapis.github.io/python-genai/). Importar o módulo, construir `GeminiClient` ou abrir seu contexto `with` não cria o cliente do SDK nem faz chamadas externas; isso ocorre somente em `generate_content`. Use o contexto para encerrar as conexões ao terminar a operação.

As configurações existentes são `GEMINI_API_KEY` (somente no backend), `GEMINI_MODEL` e `GEMINI_TIMEOUT_SECONDS` (45 segundos por requisição HTTP por padrão). Sem chave, uma geração retorna o erro controlado `missing_api_key`; a aplicação e o health check continuam funcionando. Falhas de autenticação, permissão, modelo, cota, timeout, conexão e serviço recebem códigos e mensagens em português, sem incluir a resposta bruta do provedor.

O SDK não executa ferramentas automaticamente e não repete requisições internamente. O orchestrator controla um prazo e uma repetição de 429 compartilhados entre ferramentas, síntese e reparo; o gerador de fallback está descrito na W3.13 abaixo. O endpoint de teste é descrito na seção W3.02; a verificação com chave real permanece pendente.

Verificação da W3.01 em 2026-10-15 no Windows: **179 testes Pytest aprovados**, **9 ignorados** por ausência do pacote privado. Os 25 testes novos exercitam o SDK com transporte HTTP em memória, sem rede, e cobrem criação sob demanda, configuração, erros, timeout, controle de chamadas e fechamento. `uv pip check` confirmou compatibilidade das dependências. Há três avisos de depreciação de terceiros (Starlette/httpx, AnyIO e tipagem interna do SDK no Python 3.14), sem falhas nos testes.

## Teste de conexão Gemini — W3.02

Com o backend iniciado, execute:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/gemini/test
```

Se o backend já estava rodando sem `--reload`, reinicie-o para carregar a nova rota. O endpoint aparece também em `http://127.0.0.1:8000/docs`. Não envie chave, modelo ou dados no corpo: ele usa somente a configuração do backend e o prompt fixo `Responda apenas OK.`. Com chave configurada, cada POST faz uma chamada externa com um candidato e limite de 32 tokens de saída. `GET /api/health` continua sem consumir a API.

O JSON tem o mesmo formato em sucesso e falha. Exemplo ilustrativo de sucesso (a latência real varia):

```json
{
  "success": true,
  "model": "gemini-2.5-flash",
  "latency_ms": 125,
  "message": "Conexão com o Gemini verificada.",
  "error_code": null
}
```

| HTTP | `error_code` | Significado |
| --- | --- | --- |
| 200 | `null` | O modelo respondeu ao teste de conexão. |
| 503 | `missing_api_key` | Definir `GEMINI_API_KEY` somente no ambiente ou `.env` do backend. |
| 401 | `authentication_error` | Chave recusada pelo provedor. |
| 403 | `permission_denied` | Acesso negado pelo provedor. |
| 429 | `rate_limit` | Limite de requisições ou cota atingido. |
| 504 | `timeout` | Tempo limite da requisição atingido. |
| 503 | `network_error`, `unavailable`, `configuration_error` | Falha de conexão, serviço ou configuração. |
| 502 | `model_not_found`, `invalid_request`, `api_error`, `invalid_response` | Modelo/requisição recusados ou resposta inválida. |

Em falha, `success` é `false` e `message` explica o problema sem expor chave, texto gerado ou corpo de erro do provedor. `latency_ms` mede a operação no backend com relógio monotônico, incluindo criação e fechamento do cliente. Não há repetição automática neste teste mínimo. Uma resposta vazia ou bloqueada falha; atingir o limite de tokens confirma conectividade mesmo se o orçamento foi consumido pelo raciocínio do modelo. Este teste não avalia a qualidade do relatório.

Verificação da W3.02 em 2026-10-15: **208 testes Pytest aprovados e 9 ignorados**, incluindo 29 testes novos da rota. Sucesso, autenticação, rate limit e timeout foram verificados com respostas simuladas, inclusive pelo SDK oficial com transporte HTTP em memória. Um servidor temporário confirmou por HTTP `200` no health e `503`/`missing_api_key` no teste sem chave. Nenhuma chamada ao Gemini real foi feita; essa validação permanece pendente.

## Contratos do harness — W3.03

`backend/app/harness/schemas.py` define os contratos Pydantic com campos extras proibidos, inclusive nos objetos aninhados:

| Contrato | Conteúdo |
| --- | --- |
| `InvestigationRequest` | UUID do dataset, IDs textuais dos talhões, período obrigatório e pergunta de 10–500 caracteres após remover espaços externos. Reutiliza `full_season` ou o intervalo ordenado `start`/`end` da W2. |
| `ToolCallTrace` | UUID do trace, sequência positiva, ferramenta conhecida, argumentos tipados conforme a ferramenta, IDs das evidências, fontes, versão, início com fuso horário, duração finita não negativa e status. Falhas usam `status: error`, erro local com `code`/`message` e lista de evidências vazia. |
| `InvestigationReport` | `overview`, `findings`, `limitations` e `recommendations` obrigatórios. Força `weak`, `moderate` ou `strong`; achados e recomendações citam IDs no formato `EV-…`; pelo menos uma limitação com `rule_id`. |
| `InvestigationResponse` | Envelope do SPEC: `investigation_id`, `status: completed`, `generated_by`, `report`, `evidence`, `chart_data`, `trace` e `warnings`, todos obrigatórios. Origem `gemini` ou `deterministic_fallback`, atribuída pelo backend. |

O objeto `trace` reúne `trace_id`, `dataset_id`, `model`, `created_at` com fuso horário e `calls`. Os avisos reutilizam `ValidationIssue` do upload. O relatório narrativo não recebe campos de origem ou rastreamento gerados pelo modelo.

`evidence` preserva os sete tipos concretos da W2. `chart_data` contém `ndvi` (evidência NDVI ou `null`), `soil_summaries` (lista de resumos, incluindo Conjunto 1 e Conjunto 2 quando disponíveis) e `soil_groups` (lista de comparações pareadas). As listas comportam chamadas com filtros diferentes; `ndvi: null` e listas vazias representam gráficos indisponíveis. Séries, quartis, pares, textura, fontes e valores desconhecidos `null` são preservados na serialização, sem recalcular métricas. O contrato base `Evidence` foi isolado em `evidence_schema.py` para evitar dependência circular e continua importável por `schemas.py`.

Os schemas validam estrutura. A existência dos IDs no dataset é conferida pelo validador da W3.06. Referências a evidências, números no texto e limitações obrigatórias são conferidos pela W3.10; linguagem causal, pela W3.11. O endpoint `/api/investigations` está descrito na W3.14 abaixo.

Para verificar os contratos no Windows, em `backend/`: `.venv\Scripts\python.exe -m pytest tests/test_harness_schemas.py tests/test_evidence.py`. Em 2026-10-15, **164 casos passaram**, incluindo 112 novos casos dos schemas. A suíte completa do backend passou com **320 testes aprovados, 9 ignorados** por ausência do pacote privado e os três avisos de depreciação já registrados.

## System prompt — W3.04

`backend/app/harness/prompts.py` disponibiliza `SYSTEM_PROMPT`, uma instrução estática em português usada pelo orchestrator. Define o papel observacional, uso exclusivo das ferramentas como fonte de números, referências por `evidence_id`, proibição de causalidade, limites das análises de solo e síntese no contrato `InvestigationReport`.

A pergunta, os nomes e os demais textos externos são tratados como conteúdo não confiável. A instrução deve ser enviada separadamente do contexto da sessão: não interpolar nela perguntas, IDs, evidências ou segredos. O módulo não lê configurações nem chama o SDK. A rota de teste Gemini continua com seu prompt mínimo de conexão.

Verificação em 2026-10-15: revisão do texto contra o SPEC, importação e inspeção AST confirmando literal estático sem chamadas/interpolação; auditoria de credenciais, IDs concretos e caminhos, sem ocorrências. Os dígitos presentes pertencem apenas aos nomes Conjunto 1, Conjunto 2 e `_2`. Suíte existente do backend: **320 passaram, 9 ignorados e 3 avisos de depreciação**. Não houve chamada real ao Gemini. O prompt orienta o modelo; a aplicação dessas regras pelo harness e sua validação em execução continuam pendentes.

## Declarações de Function Calling — W3.05

`build_gemini_tool()`, em `backend/app/harness/registry.py`, produz um `google.genai.types.Tool` com declarações para as sete ferramentas do registry, incluindo as duas análises de solo. Cada declaração contém somente nome, descrição e `parameters_json_schema` gerado pelo modelo Pydantic de argumentos públicos. O SDK oferece esse campo para JSON Schema, conforme seu contrato `FunctionDeclaration`; o código usa o SDK 2.31.0 instalado, mantendo a abordagem declarativa de [Function Calling](https://ai.google.dev/gemini-api/docs/function-calling).

Exemplo de preparação da configuração, sem chamada externa:

```python
from google.genai import types
from app.harness.registry import build_gemini_tool

config = types.GenerateContentConfig(tools=[build_gemini_tool()])
```

Os schemas preservam `additionalProperties: false`, IDs textuais, UUID, período `full_season` ou `start`/`end`, enumerações, defaults e filtros opcionais de solo. As descrições explicam a seleção dos talhões e o escopo geral do solo. Não são expostos callables Python, DataFrames, caminhos, store ou geradores internos. Cada construção retorna objetos novos, sem criar cliente, ler a chave ou executar análises. Ao receber essa configuração, `GeminiClient` continua desativando a execução automática de ferramentas; o validador de chamadas está descrito na W3.06 abaixo e o orchestrator permanece pendente.

Verificação em 2026-10-15: **17 testes novos** de declarações, contratos, isolamento de mutações e envio pelo SDK oficial com transporte HTTP em memória. Cada uma das sete chamadas simuladas voltou para o chamador sem execução automática. Testes focados: **154 passaram**; suíte completa: **337 passaram, 9 ignorados** por ausência do pacote privado e os três avisos existentes. Nenhum acesso ao Gemini real; aceitação pelo serviço e comportamento do modelo continuam para o teste controlado da W3.15.

## Validador de chamadas — W3.06

`ToolCallValidator`, em `backend/app/harness/validators.py`, deve ser criado uma vez por investigação, com um `InvestigationRequest` validado e o `SessionStore` da sessão. `validate_call(name, arguments)` verifica a ferramenta no registry, exige um objeto de argumentos aderente ao respectivo modelo Pydantic e devolve esse modelo com valores normalizados. O recorder integrado ao orchestrator usa `params.model_dump(mode="json")` para executar e registrar a chamada, em vez do dicionário original do modelo.

O validador confirma que o dataset continua disponível, que os talhões pertencem a ele e que o dataset, o par ordenado e o período continuam iguais à seleção inicial. A seleção é copiada na construção. Solo permanece no escopo geral do dataset e não aceita argumentos de talhão ou período. Comparabilidade agronômica e disponibilidade de cada análise continuam nas ferramentas e no futuro loop.

Cada chamada aceita é reservada imediatamente: uma tentativa posterior idêntica é bloqueada mesmo se a execução falhar. Chamadas rejeitadas não ocupam esse histórico. A identificação considera nome da ferramenta e argumentos normalizados, incluindo defaults, UUIDs e espaços; operações usam a mesma normalização das análises. Filtros de solo com as mesmas métricas contam como repetição mesmo em outra ordem ou com nomes duplicados. O retorno preserva a ordem original das métricas, removendo duplicatas. Grupos, filtros ou operações diferentes continuam permitidos. Crie uma nova instância para outra investigação; use a instância sequencialmente.

`ToolCallValidationError` fornece códigos locais (`unknown_tool`, `invalid_arguments`, `dataset_mismatch`, `dataset_not_found`, `field_not_found`, `invalid_pair`, `pair_changed`, `period_changed`, `duplicate_call`) e mensagens sem reproduzir argumentos ou detalhes brutos do Pydantic. O validador não executa ferramentas nem cria trace: o orchestrator o utiliza por meio do recorder e aplica o orçamento de oito chamadas e a comparabilidade obrigatória, inclusive na rota W3.14.

Verificação em 2026-10-15: `.venv\Scripts\python.exe -m pytest tests/test_call_validators.py --tb=short` em `backend/`: **54 casos passaram**, incluindo bloqueios, normalização, isolamento e execução local das sete ferramentas após validação. Suíte completa: **391 passaram, 9 ignorados** por ausência do pacote privado e três avisos de depreciação existentes. Sem chamadas externas ou novas dependências.

## Trace da investigação — W3.07

`InvestigationRecorder`, em `backend/app/harness/trace.py`, recebe a requisição, o nome do modelo configurado e o store da sessão. Crie uma instância por investigação e use-a sequencialmente. Ela gera `investigation_id` e `trace_id` como UUIDs distintos e mantém um gerador de IDs de evidência compartilhado entre suas ferramentas.

`run_tool(name, arguments)` valida e reserva a chamada pela W3.06, executa a ferramenta local com os argumentos normalizados e retorna sua evidência. Cada execução registra uma entrada `ToolCallTrace`: sequência, ferramenta, argumentos, versão, início em UTC, duração em milissegundos, IDs de evidência e nomes das fontes. A duração usa relógio monotônico, independente de ajustes no relógio de parede. `snapshot()` retorna uma cópia defensiva de `InvestigationTrace`, pronta para `model_dump_json()`; o `investigation_id` fica disponível para o envelope final.

Falhas de execução registram `status: error`, listas vazias de evidências/fontes e um erro local, depois lançam `ToolExecutionError`. Os códigos são `analysis_unavailable`, `dataset_not_found`, `invalid_tool_result` e `tool_execution_failed`. Não são copiadas mensagens brutas ou encadeadas exceções originais. Sem resultado válido, o trace não afirma quais fontes foram efetivamente usadas. Rejeições de validação, incluindo repetição, continuam como `ToolCallValidationError`: não executam nem criam uma entrada de ferramenta executada. Uma execução que falhou continua reservada contra repetição.

O JSON do trace contém somente metadados de auditoria e argumentos públicos normalizados: não copia pergunta, configuração do provedor, chave, prompt, CSV bruto, notas ou séries do resultado. Fontes precisam pertencer aos sete nomes de arquivos esperados. Metadados de evidência inválidos, versão divergente ou ID já registrado produzem falha controlada. O retorno completo permanece separado e é revalidado pelo schema concreto da ferramenta antes de o orchestrator reunir as evidências; nenhuma rota nova foi adicionada.

Verificação em 2026-10-15: `.venv\Scripts\python.exe -m pytest tests/test_investigation_trace.py --tb=short` em `backend/`: **26 testes passaram**. Cobertura das sete ferramentas, falha real por NDVI indisponível, UUIDs, sequência, isolamento de cópias/geradores, serialização, privacidade e duração com relógio de parede retrocedendo. Suíte completa naquela entrega: **417 passaram, 9 ignorados** por ausência do pacote privado e três avisos de depreciação existentes. Sem chamadas externas ou novas dependências. A integração no loop foi concluída na W3.08 abaixo.

## Loop de ferramentas — W3.08

`backend/app/harness/orchestrator.py` expõe `run_investigation_tools(request, client=None, settings=None, store=dataset_store)`. Recebe um `InvestigationRequest` com dataset importado na sessão e retorna `ToolLoopResult`, um resultado interno com `investigation_id`, `stop_reason`, evidências, trace, avisos e erro opcional. Ainda não gera `InvestigationReport` nem publica uma rota HTTP.

O primeiro contexto contém somente pergunta, IDs/rótulos normalizados do par, período, inventário de arquivos, avisos e limite de chamadas. A instrução do sistema fica separada da pergunta; CSVs e DataFrames não são enviados. O modelo recebe as sete declarações do registry, com execução automática desativada. O harness exige `validate_comparison` antes de qualquer análise e interrompe o fluxo se o par for incompatível. Cada chamada passa pelo validador W3.06 e recorder W3.07; o retorno também é revalidado pelo schema concreto registrado para a ferramenta antes de ser entregue ao Gemini.

Chamadas em lote são executadas sequencialmente. O histórico preserva as partes da resposta do SDK, incluindo assinaturas de raciocínio, e devolve o ID da chamada em cada `FunctionResponse`. Respostas bloqueadas, truncadas, parciais ou ambíguas são rejeitadas. Chamadas desconhecidas, repetidas, fora da seleção e falhas de cálculo encerram o loop com erro controlado e preservam evidências/trace já produzidos.

`GEMINI_MAX_TOOL_CALLS` pode reduzir o orçamento, mas nunca ultrapassa oito execuções, incluindo a comparabilidade. Ao atingir o limite, o loop retorna `tool_limit` sem pedir outra rodada de planejamento; a síntese recebe todas as evidências, inclusive a última. Os demais motivos são `model_finished`, `invalid_comparison`, `error` e `timeout`. Texto livre de finalização do modelo não é aproveitado como relatório.

O prazo usa `GEMINI_TIMEOUT_SECONDS`, relógio monotônico e o tempo restante para reduzir o timeout HTTP de cada geração. Há uma única repetição de 429 por investigação, com espera de até um segundo dentro desse orçamento. A verificação do prazo ocorre entre etapas síncronas: cálculos locais não são interrompidos durante a execução, e o timeout HTTP não é um cancelamento absoluto do processo. O cliente criado pelo orchestrator é fechado ao terminar; clientes injetados pertencem ao chamador. A função integrada W3.09 compartilha esse orçamento entre planejamento e síntese.

Verificação em 2026-10-16: **34 testes do orchestrator passaram**, incluindo duas ferramentas e finalização com cliente fake, SDK real com transporte HTTP em memória, limites, falhas, privacidade, assinaturas/IDs e prazo total simulado. Nove novos testes verificam o timeout por chamada do cliente. Suíte backend naquela entrega: **460 passaram, 9 ignorados e 3 avisos de depreciação existentes**. Nenhuma chamada externa ou dependência nova. A síntese foi integrada na W3.09 abaixo.

## Síntese estruturada — W3.09

`synthesize_report(planning, client=..., settings=...)`, em `backend/app/harness/orchestrator.py`, recebe um `ToolLoopResult` e retorna `InvestigationReport`. Envia uma conversa nova com evidências, avisos acumulados e limitações obrigatórias determinadas pelo backend, mantendo `SYSTEM_PROMPT` e `SYNTHESIS_INSTRUCTION` separados dos dados. Preserva números, fontes, notas, limitações e `rule_id` dos resultados; não reenvia pergunta, diálogo de planejamento, trace ou dados brutos. Não oferece ferramentas nesta fase.

A geração usa `response_mime_type="application/json"` e `response_json_schema=InvestigationReport.model_json_schema()`, conforme o suporte a [saídas estruturadas do Gemini](https://ai.google.dev/gemini-api/docs/structured-output). O harness valida localmente o texto JSON com Pydantic, sem confiar em `response.parsed`. Objetos com campos extras, tipos incorretos, estrutura incompleta, enum inválido ou lista vazia de limitações são rejeitados. Também rejeita respostas vazias, bloqueadas, truncadas, ambíguas e chamadas de função. Falhas retornam `SynthesisError` com código/mensagem local, sem guardar texto bruto ou detalhes de entrada do erro Pydantic. Não há tentativa de reparo nesta etapa.

`run_investigation_draft(request, client=None, settings=None, store=dataset_store)` integra planejamento, síntese e o reparo da W3.12 com um cliente, prazo total e repetição única de 429 compartilhados. Só sintetiza após `model_finished` ou `tool_limit`, sem erro e com comparação permitida. Retorna `InvestigationDraft` com `planning`, `report` opcional e `error` opcional. Em falha, preserva as evidências e o trace do planejamento. `trace.calls` contém somente execuções de ferramentas; `trace.repair` registra a tentativa de reparo, quando necessária. O cliente próprio é fechado ao terminar; o cliente injetado permanece sob responsabilidade do chamador. O uso isolado de `synthesize_report` inicia um orçamento próprio e não repete a síntese por erro de validação.

O resultado permanece um **rascunho interno**. As W3.10 e W3.11 acrescentam as checagens de evidências e linguagem descritas abaixo; não foi criado um `InvestigationResponse` concluído nem uma rota nova.

Verificação da W3.09 em 2026-10-16: **43 testes novos passaram**, incluindo resposta fake válida, falhas de estrutura/JSON, isolamento do contexto, preservação dos fatos, orçamento/retry compartilhados, fechamento e SDK real com HTTP em memória. Suíte naquela entrega: **503 passaram, 9 ignorados por ausência do pacote privado e 3 avisos existentes**. Nenhuma chamada externa ou dependência nova.

## Validação de evidências e números — W3.10

`validate_report_evidence(report, evidence, warnings)` e `required_limitations(evidence, warnings)` estão em `backend/app/harness/report_validation.py`, com acesso também por `validators.py`. O validador retorna uma cópia validada do relatório ou lança `ReportValidationError` com uma lista de `code`, `location` e `message`. Não altera evidências nem recalcula métricas. O catálogo numérico projeta campos tipados das sete ferramentas; IDs, versões, textos livres e booleanos não viram valores numéricos de suporte.

As checagens abrangem títulos, visão geral, achados, recomendações e limitações adicionais. Cada frase usa suas citações explícitas ou os `evidence_ids` do respectivo achado/recomendação; a visão geral precisa citar a evidência na própria frase quando trouxer números. IDs desconhecidos e evidências com IDs duplicados são rejeitados. Um número presente em uma evidência não citada não pode justificar a afirmação.

O prompt orienta frases simples com métrica, papel e unidade explícitos. Exemplos de formatos: `NDVI médio do alvo: 0,4`, `gap: −0,1`, `25 plantas/ha`, `75 kg/ha`, `42,86%`, `−57,14 pontos percentuais` e `5 datas pareadas`. Valores dimensionais exigem unidade compatível; unidade de solo desconhecida não pode ser preenchida pelo modelo. Percentual e pontos percentuais são distintos. Datas ISO ou `DD/MM/AAAA` e identificadores de amostras restringem a busca aos valores correspondentes. Conjunto 1/2 e IDs conhecidos de talhão/amostra são rótulos, não métricas.

Decimais com vírgula, ponto e notação científica são reconhecidos. O padrão preferido é português: `61.306,27`; `61,306.27` também é aceito. Um ponto seguido de três algarismos, com parte inteira não nula, é tratado como agrupamento de milhares; use vírgula para evitar ambiguidade. A comparação usa arredondamento decimal à precisão escrita (`ROUND_HALF_UP`), preserva o sinal e não permite arredondar um valor não nulo para zero. Contagens precisam coincidir exatamente. Quantidades por extenso nos padrões reconhecidos são rejeitadas com orientação para usar algarismos. O vocabulário explícito de direção, como gap positivo/negativo e alvo maior/menor, também é conferido.

`required_limitations` inclui sempre natureza observacional e ausência de produtividade confiável. Conforme os resultados, acrescenta condição inicial não verificada, indisponível ou diferente; natureza heurística da análise inicial; poucas datas pareadas; avisos de qualidade; escopo do solo, significado de `_2`, unidades e referência agronômica ausentes. Esses objetos são enviados à síntese. O relatório deve manter cada `rule_id` uma única vez e copiar a explicação fornecida, tolerando apenas diferenças de espaços. Uma frase genérica com o ID correto não satisfaz a regra; o título pode variar.

Após a validação estrutural, o orchestrator executa essas checagens. Uma falha produz `invalid_report_evidence` e `validation_issues`, mantendo evidências e trace do planejamento. Os erros não reproduzem texto bruto do modelo. Na função integrada, essa falha inicia o reparo descrito na W3.12; se a nova resposta também falhar, o rascunho fica com `report=null` e o erro final. O gerador da W3.13 pode receber essas evidências para criar o fallback local.

Limite deliberado: são regras conservadoras para formatos, unidades e vocabulário explícitos, não uma prova de suporte semântico de qualquer frase em linguagem natural. Frases ambíguas podem ser rejeitadas; sinônimos ou relações qualitativas fora desses padrões não recebem validação completa. A checagem específica de causalidade está descrita na W3.11 abaixo.

Verificação da W3.10 em 2026-10-16: **80 testes novos do validador e cinco de integração passaram**. Suíte naquela entrega: **588 passaram, 9 ignorados e 3 avisos existentes**. Testes cobrem evidência falsa, números inventados, sinais/unidades, papéis, contagens, arredondamento, datas, solo, limitações e preservação do trace em falha. Sem API externa ou dependências novas.

## Validação de linguagem causal — W3.11

`validate_report_language(report)`, em `backend/app/harness/language_validation.py` e reexportado por `validators.py`, verifica títulos e textos de visão geral, achados, limitações e recomendações. Retorna uma cópia validada ou lança `ReportLanguageError` com `ReportValidationIssue`: `code=causal_language`, localização do campo e orientação local indicando a família da expressão. Os erros não copiam a frase do modelo nem usam a pergunta como instrução.

As regras cobrem `causou`, `provou`, `foi responsável por`, `garantiu` e `levou a`, flexões selecionadas e expressões como `provocou`, `efeito causal` e `resultado direto de`. Normalizam caixa, acentos, espaços e caracteres invisíveis; citações de evidências são metadados. Há exceções específicas para usos como `levou a equipe ao campo`, `a equipe foi responsável por coletar`, garantias de formato/rastreabilidade do processamento e a menção isolada de um termo entre aspas. Aspas em torno de uma afirmação causal inteira não a tornam válida.

Ressalvas explícitas são locais: `não é possível afirmar que o manejo causou a diferença` e `não há evidência de que o manejo causou a diferença` são aceitas. A ressalva deixa de valer na próxima frase, campo, adversativa ou nova afirmação independente reconhecida. Assim, `não é possível afirmar que causou, mas o manejo garantiu o resultado` é rejeitado. Também são rejeitadas construções como `não é possível negar que causou`, hipóteses causais com `pode ter causado` e a afirmação definitiva `o manejo não causou a diferença`. Prefira a descrição da associação ou da impossibilidade de concluir, sem afirmar efeito ou ausência de efeito.

O orchestrator executa a validação de linguagem depois das checagens de evidências. Em falha, mantém fatos e trace e produz `invalid_report_language` com os `validation_issues`. A função integrada usa esse erro para iniciar a única tentativa de reparo da W3.12. O prompt orienta o mesmo uso de ressalvas locais.

Limite: o validador usa padrões lexicais conservadores e escopo limitado de oração, não um parser completo de português. Pode rejeitar formulações ambíguas e não cobre todos os sinônimos, metáforas, negações complexas ou idiomas. A avaliação com o modelo real continua na W3.15.

Verificação da W3.11 em 2026-10-16: **91 testes novos de linguagem e quatro de integração passaram**. Suíte naquela entrega: **683 passaram, 9 ignorados por ausência do pacote privado e 3 avisos existentes**. Sem chamadas externas ou dependências novas.

## Uma tentativa de reparo — W3.12

`run_investigation_draft` tenta gerar um único relatório substituto quando a síntese falha com `invalid_report`, `invalid_report_evidence` ou `invalid_report_language`. O contexto é uma conversa nova com somente `errors`, `schema` e `facts`; os fatos preservam evidências, avisos e limitações obrigatórias. Não envia o relatório rejeitado, a pergunta, o histórico ou o trace. Erros de schema incluem localizações e orientações locais, sem valores de entrada ou nomes de campos extras fornecidos pelo modelo.

O reparo não disponibiliza nem executa ferramentas. A resposta passa novamente por Pydantic, validação de evidências/números/limitações e linguagem causal. Sucesso entrega o relatório validado; uma segunda falha encerra o rascunho com `report=null`, erro final e fatos preservados. Falhas do provedor e respostas bloqueadas, truncadas ou com chamadas de ferramenta não iniciam reparo. O prazo total e a única repetição de 429 são compartilhados pelas três fases; essa repetição de transporte não permite aceitar um terceiro relatório.

`trace.repair` é opcional: registra tentativa 1, início UTC, duração monotônica, status, erro e questões que motivaram o reparo, além do erro e questões finais em caso de falha. Não guarda prompts nem texto bruto do relatório. Se o prazo já tiver esgotado ao iniciar o reparo, registra a falha sem uma nova requisição. `trace.calls` permanece reservado às ferramentas. O resultado ainda é interno; a W3.13 fornece o gerador local e a W3.14 fará a integração com o endpoint.

Verificação da W3.12 em 2026-10-16: **34 testes novos de reparo passaram**, com cliente fake e SDK real sobre HTTP em memória. Cobrem recuperação, segunda resposta inválida, privacidade, ausência de ferramentas, falhas do provedor, prazo e repetição de 429 compartilhados, fechamento do cliente e trace. Suíte naquela entrega: **717 passaram, 9 ignorados por ausência do pacote privado e 3 avisos de depreciação existentes**. Sem chamadas externas ou dependências novas.

## Fallback determinístico — W3.13

`build_fallback_report(evidence, warnings=(), reason="unavailable")`, em `backend/app/harness/fallback.py`, gera título, resumo, achados, limitações e recomendações por templates locais. Retorna `FallbackResult` com `report`, `generated_by="deterministic_fallback"` fixo e avisos preservados mais um aviso de fallback com motivo local seguro. Funciona sem chave, cliente ou rede; não chama ferramentas, não recalcula métricas e não altera as evidências recebidas. Depois de uma falha no reparo, pode consumir `draft.planning.evidence`, `draft.planning.warnings` e `reason=draft.error.code`, preservando o trace original.

A ordem de apresentação é comparabilidade, condição inicial diferente quando sinalizada, resumos de solo por conjunto, contraste entre conjuntos, NDVI, condição inicial restante, aplicações (CALAGEM primeiro) e população. Empates usam `evidence_id`; métricas de solo usam nome. Esta é uma regra local de apresentação, sem ranking causal ou estatístico. Valores são formatados em português, com até seis casas decimais (duas para operações/população), preservando sinal e valores pequenos que seriam arredondados para zero. As recomendações citam somente evidências presentes e se limitam a conferência e documentação.

O gerador exige comparabilidade permitida e rejeita IDs duplicados, mistura de pares/períodos e fatos estruturalmente inválidos. Evidências parciais são aceitas com limitação explícita; nenhum resultado ausente é convertido em zero. A força é conservadoramente `weak`, sem promoção automática baseada em pontuação. Limitações de observação, produtividade, condição inicial, qualidade e solo vêm de `required_limitations`. O relatório passa pelos mesmos validadores de schema, fatos e linguagem da síntese. O aviso operacional de fallback não é tratado como defeito de qualidade dos dados. A redação da limitação sobre os conjuntos de solo foi ajustada para ser compatível com a validação causal, sem mudar seu significado.

O gerador é utilizado pelo fluxo completo da W3.14. `run_investigation_draft` continua disponível para obter apenas o rascunho interno; `run_investigation` integra fallback e envelope final.

Verificação da W3.13 em 2026-10-16: **45 testes novos de fallback passaram**. Suíte naquela entrega: **762 passaram, 9 ignorados por ausência do pacote privado e 3 avisos de depreciação existentes**. Testes usam fatos calculados pelas ferramentas locais e respostas simuladas para falhas de síntese/reparo. Sem API externa ou dependência nova.

## Endpoint de investigação — W3.14

`POST /api/investigations` recebe `InvestigationRequest` e responde sincronamente com `InvestigationResponse`. A rota chama `run_investigation`, valida dataset e talhões e executa `validate_comparison` localmente antes de criar o cliente. Essa chamada aparece no trace e consome o mesmo orçamento das demais ferramentas. Um par incompatível é rejeitado antes de qualquer outra análise ou chamada ao provedor, com indicação de cultura, finalidade ou manejo incompatível.

Com chave, o planejamento recebe a evidência de comparabilidade em `precomputed_evidence`, sem simular uma chamada do modelo. O recorder e o orçamento são compartilhados com o loop, a síntese e o reparo; repetir a comparação é rejeitado. Falhas do provedor, respostas inválidas e segunda falha de validação acionam o fallback sobre os fatos já obtidos. Mesmo uma falha na primeira geração pode produzir um relatório parcial a partir da comparabilidade, com gráficos ausentes e limitações explícitas. Erros de cálculo ou de validação das chamadas interrompem a investigação com erro controlado.

Sem chave, nenhum cliente é criado. Um plano local executa as análises disponíveis: resumos de solo por conjunto, contraste dos conjuntos, NDVI, condição inicial, aplicação comum com preferência por CALAGEM e população. Há no máximo oito execuções, incluindo comparabilidade, respeitando redução por `GEMINI_MAX_TOOL_CALLS`. O prazo começa antes da comparação; nenhuma nova ferramenta ou geração é iniciada depois de expirar. A formatação e validação local do fallback podem finalizar após o prazo, e cálculos síncronos em andamento não são interrompidos.

O envelope retorna origem atribuída pelo backend, relatório validado, evidências, gráficos derivados diretamente delas, trace e avisos do pacote/análises. No fallback, inclui aviso explícito de geração local. Não publica pergunta, prompts, credenciais ou resposta bruta rejeitada. Os gráficos mantêm séries, quartis, pares e textura; quando a análise não foi executada, usa `null` ou listas vazias.

| Status HTTP | Resultado |
| --- | --- |
| `200` | Relatório válido do Gemini ou fallback, com `status: completed`. |
| `404` | Dataset ausente na sessão. |
| `422` | Schema inválido, talhão inexistente, par repetido ou incompatível. |
| `503` | Falha de cálculo, chamada não permitida ou impossibilidade de produzir relatório válido. Erro local em `detail.code`/`detail.message`. |

Verificação concluída em 2026-10-16: **827 testes passaram, 9 foram ignorados e 3 avisos de depreciação existentes, em 50,61 s**, conforme saída da suíte completa executada pelo usuário no terminal e enviada nesta conversa. Inclui **41 testes novos** do fluxo/função da rota/OpenAPI/SDK simulado e **24 novos testes HTTP**. Antes disso, 745 testes haviam passado no ambiente restrito, excluindo os módulos HTTP; a execução local confirmou a parte que estava bloqueada pelo socket interno do TestClient e pelo limite de uso da revisão automática. Comando executado:

```powershell
cd C:\Users\souza\CSIMilho\backend
.\.venv\Scripts\python.exe -m pytest --tb=short
```

A W3.14 está concluída. Os nove testes ignorados dependem do pacote privado; os avisos são de dependências e não representam falhas. A W3.15 também foi concluída com chave real em 2026-10-17, conforme registro abaixo. W4 não foi iniciada.

## Teste controlado do Gemini — W3.15

O comando `app.harness.smoke` usa por padrão os **sete CSVs pequenos de `backend/tests/fixtures/manual`**, o alvo `103144`, a referência `103145` e a safra completa. Esse pacote permite conferir a integração sem dados privados; não representa validação agronômica ou de volume de produção. Nenhuma dependência adicional é necessária.

Configure `GEMINI_API_KEY` apenas no `.env` local da raiz, já preparado a partir de `.env.example` e ignorado pelo Git. Preserve as demais configurações ou ajuste `GEMINI_MODEL` ao modelo disponível na sua conta. Execute a partir de `backend`, sem precisar iniciar Uvicorn ou o frontend:

```powershell
cd C:\Users\souza\CSIMilho\backend
.\.venv\Scripts\python.exe -m app.harness.smoke --check-only
.\.venv\Scripts\python.exe -m app.harness.smoke
```

O primeiro comando valida pacote, par e configuração sem chamar o Gemini. `gemini_configured` informa somente a presença da chave, sem testar sua validade. O segundo executa uma investigação pelo harness e pode consumir a cota da API. Mantém os limites existentes de ferramentas, prazo, uma repetição por HTTP 429 e um reparo de relatório.

O resumo JSON final indica `passed`, origem, modelo, ferramentas/status, avisos, reparo e caminho do relatório. Para passar, exige origem `gemini`, chamadas bem-sucedidas de comparabilidade, NDVI e resumo de solo, no máximo oito ferramentas, correspondência entre evidências e trace e aprovação dos validadores de estrutura, evidências/números e linguagem. Um fallback válido continua sendo **reprovação do teste real**. Códigos de saída: `0` para aprovação (ou checagem local válida), `1` para investigação concluída sem cumprir o cenário e `2` para configuração, entrada ou execução inválida.

O envelope validado é salvo em `backend/.local/w3-15/<data>-<investigation_id>.json`, ignorado pelo Git. Abra o arquivo indicado por `report_path` e confira `report`, `evidence`, `trace.calls`, `trace.repair` e `warnings`: os achados devem corresponder às evidências, o solo deve permanecer no escopo do dataset e as limitações precisam estar explícitas. O artefato contém o relatório normalizado, sem chave, prompt ou resposta bruta do provedor. Compartilhe o resumo para revisão, nunca a chave.

Outro pacote exige `--data-dir CAMINHO` explícito, com `--target ID --reference ID` quando necessário. A variável `FARMLAB_REAL_DATA_DIR` não altera o pacote deste comando.

Verificação local em 2026-10-16: **14 testes novos**, incluindo integração com provedor simulado, cálculos reais das fixtures, gravação do relatório, fallback, análise ausente, evidência sem trace, número inventado, chave ausente e pacote inválido. **100 testes passaram** no conjunto focado de smoke/investigação/fallback. Regressão sem os módulos HTTP bloqueados no sandbox: **759 passaram, 9 ignorados, 3 avisos existentes em 39,39 s**. Os testes usaram uma pasta temporária exclusiva em `backend/.local`, pois a pasta temporária padrão do sandbox negou criação. `--check-only` confirmou os sete arquivos e a ausência de chave. Essa pendência foi resolvida pelo teste real de 2026-10-17, registrado a seguir.

**Validação real concluída em 2026-10-17:** `gemini-2.5-flash` retornou uma investigação aprovada (`passed: true`, `generated_by: gemini`), com oito chamadas bem-sucedidas e sem reparo ou fallback. Evidências e trace conferidos; NDVI, população, calagem, condição inicial e solo inspecionados. Relatório local: `backend/.local/w3-15/20261017T135442Z-c616c852-424a-45cb-91e6-769a46f56717.json`. O diagnóstico mínimo do endpoint também confirmou conexão, em 872 ms.

As tentativas iniciais identificaram redações numéricas inválidas e timeout. O prompt agora orienta a seleção de achados em `reference_findings`, renderizados pelos templates W3.13 sobre as evidências atuais e previamente validados. O Gemini organiza os achados e redige visão geral e recomendações; toda a resposta continua passando pelos mesmos validadores. Não houve alteração de cálculos ou flexibilização de validação. Novas gerações ainda podem exigir reparo ou fallback.

O `.env` local foi ajustado para `GEMINI_TIMEOUT_SECONDS=120`, preservando a chave. O padrão do código e de `.env.example` permanece 45 s; para reproduzir o teste, use 120 s. A chave e os relatórios continuam ignorados pelo Git. O teste de health foi isolado do `.env` para funcionar também em instalações com chave configurada.

Regressão completa, incluindo HTTP: **841 passaram, 9 ignorados, 3 avisos existentes em 41,40 s**. Depois do último ajuste textual do prompt: **100 testes focados de síntese, reparo e smoke passaram em 12,62 s**. Os nove testes ignorados dependem dos CSVs privados. W3.15 concluída; W4 não iniciada.

## Estado da investigação no frontend — W4.01

`frontend/src/state.js` mantém o dataset, o resultado em `state.investigation` e o erro. `runInvestigation(execute)` recebe a operação assíncrona conectada à API na W4.02: exige READY e um dataset, muda imediatamente para INVESTIGATING e compartilha a mesma Promise entre chamadas repetidas. Uma resposta, inclusive fallback, conclui em COMPLETED; uma exceção síncrona ou rejeição conclui em ERROR. A troca de pacote durante a operação é bloqueada.

`startNewComparison()` faz COMPLETED → READY, limpa o resultado e mantém o mesmo dataset, sem upload. O reinício após erro segue ERROR → EMPTY e limpa o pacote.

Verificação de 2026-10-17: **35 testes Vitest passaram**, incluindo dez novos casos de cliques repetidos, concorrência, sucesso/fallback, falhas e reutilização do dataset; `pnpm build` aprovado. Antes da alteração, a suíte do handoff W3 foi reproduzida: **841 testes backend passaram, 9 privados ignorados e 3 avisos existentes**. Nenhuma dependência nova ou chamada ao Gemini nesta etapa.

## Execução pela interface — W4.02

Após importar o pacote, mantenha o backend em desenvolvimento para consultar a comparabilidade. Escolha os talhões e o período, escreva uma pergunta de 10 a 500 caracteres e clique em **Executar investigação**. O frontend envia JSON para `POST /api/investigations`, bloqueia os controles e a navegação e mostra progresso indeterminado. A lista textual descreve as etapas do processo; o endpoint síncrono não fornece o estágio atual.

O sucesso abre o resultado com a origem Gemini ou fallback local. **Nova comparação** reutiliza o dataset. Erros HTTP, de rede ou de resposta inválida aparecem na própria tela; **Reiniciar pacote** retorna à importação sem recarregar a página. Dados demonstrativos só aparecem no fluxo sem upload. A confirmação inicial da W4.02 foi ampliada na W4.03 com resumo e visão de solo, descritos abaixo.

Verificação de 2026-10-17: **57 testes Vitest passaram** (22 novos nesta tarefa), `pnpm build` e `git diff --check` aprovados. A navegação, os cliques repetidos, o fallback e o reinício após erro foram exercitados em happy-dom com API fake. Sem nova chamada ao Gemini, dependência ou alteração no backend.

## Visão geral e visão de solo — W4.03

A tela usa `report.overview` para apresentar título, resumo e força da evidência (fraca, moderada ou forte), preservando a origem Gemini/fallback. Título, resumo e força inválidos são rejeitados pelo adaptador da API. Textos externos são inseridos com `textContent`, inclusive avisos, fontes e identificadores de amostra.

Logo após o resumo, a **Visão de solo** apresenta as evidências de escopo geral do dataset. Cada chamada mantém seus próprios cards de amostras, completude do recorte e textura válida. O seletor de métrica mostra mínimo, mediana, máximo, unidade e contagem válida; **Ver estatísticas detalhadas** abre a tabela com média, quartis e valores ausentes. Em **Conjunto 1 × Conjunto 2**, o seletor mostra pares válidos e delta mediano, com **Ver valores por amostra** para consultar os pares e deltas fornecidos pelo backend.

Não há agregação entre chamadas com filtros diferentes nem cálculo analítico no navegador. Valores nulos aparecem como indisponíveis, e ferramentas/conjuntos ausentes não recebem dados demonstrativos. Os avisos deixam explícita a ausência de vínculo entre solo e talhão, coordenada, data ou profundidade, bem como a falta de referência para classificação agronômica. Os detalhes tabulares da visão geral são complementados pelos gráficos integrados na W4.06.

Verificação de 2026-10-17: **71 testes Vitest passaram** (14 novos), build Vite e `git diff --check` aprovados. Testes em happy-dom cobrem HTML malicioso, origens e forças, filtros separados, resultados parciais, nulos/zeros, seleção de métrica e preservação dos valores recebidos. Sem nova dependência, chamada ao Gemini ou alteração no backend. Próximo item: **W4.04 — achados e recomendações**.

## Achados e recomendações — W4.04

Após a visão de solo, os cards apresentam os achados na ordem de `report.findings`, com título e explicação. As recomendações preservam a ordem de `report.recommendations`, exibindo ação e justificativa. Cada card contém **Evidências relacionadas**: expanda um ID para consultar o método e os arquivos fonte da evidência correspondente. Evidências de solo mantêm o aviso de escopo geral do dataset. Listas vazias recebem uma mensagem explícita.

O adaptador da API verifica que cada card tem ao menos um `evidence_id` existente e que todas as referências são válidas. IDs de evidência duplicados, referências desconhecidas, campos textuais inválidos ou ausência dos metadados necessários causam erro controlado antes da exibição. Nenhum card é descartado silenciosamente. Todo conteúdo externo continua usando `textContent`.

Verificação de 2026-10-17: **85 testes Vitest passaram** (14 novos), build Vite e `git diff --check` aprovados. Cobertos ordem, vínculos de todos os cards, origens Gemini/fallback, conteúdo malicioso, listas vazias e navegação com API fake. Sem chamada ao Gemini, dependência nova ou alteração no backend. Próximo item: **W4.05 — aba de evidências**.

## Aba de evidências — W4.05

As abas **Visão geral** e **Evidências**, introduzidas na W4.05, preservam a seleção de métricas da visão geral. Clique na aba ou use as setas, Home e End para navegar. A aba Evidências apresenta cada evidência na ordem recebida, com métrica, alvo, referência, diferença, unidade, quantidade de observações e arquivos fonte. Quando disponíveis, também mostra datas pareadas, amostras e linhas válidas/descartadas. A diferença de conformidade de aplicação é indicada em pontos percentuais.

Solo mantém tabelas próprias de estatísticas por conjunto e detalhes pareados por amostra, com contagem válida e delta mediano, sem associar valores aos talhões. Nulos e valores ausentes aparecem como **Indisponível**, zeros reais permanecem zero e unidades desconhecidas são explícitas. Os valores são apenas formatados; não há recálculo, dados demonstrativos ou nova chamada à API ao trocar de aba.

Verificação de 2026-10-17: **93 testes Vitest passaram** (oito novos), build Vite e `git diff --check` aprovados. Cobertos valores nulos/zero, diferenças recebidas, unidades, contagens, fontes, solo, conteúdo malicioso e navegação por teclado e com API fake. Sem nova dependência, chamada ao Gemini ou alteração no backend. Próximo item: **W4.06 — gráficos reais**.

## Gráficos da investigação — W4.06

Abra **Solo** ou use **Explorar gráficos de solo** na visão geral. Os seletores de evidência, família e métrica permitem examinar cada chamada de resumo separadamente; a comparação entre conjuntos tem seus próprios seletores. Distribuição mostra mínimo, quartis, mediana e máximo recebidos; comparação mostra pares e deltas; textura apresenta somente as amostras e percentuais normalizados pelo backend. Resultados parciais não são preenchidos com outras chamadas ou dados demonstrativos.

Em **Gráfico NDVI**, a série preserva pontos, ordem e gaps de `chart_data.ndvi`, com datas em dia/mês/ano, sem deslocamento de fuso. Quando a análise não foi retornada, aparece uma mensagem de indisponibilidade. Cada visualização inclui unidade, quantidade válida, fonte, tooltip e tabela acessível. Mapa, tendência temporal e perfil de profundidade do solo permanecem indisponíveis por ausência dos campos necessários.

O adaptador verifica que as entradas de `chart_data` correspondem às evidências de mesmo ID, incluindo o conteúdo completo, sem depender da ordem das chaves dos objetos. Divergências geram erro controlado antes da exibição. Chart.js é montado após anexar o painel visível; trocar filtros, abas ou sair do resultado descarta as instâncias anteriores. Voltar à aba recria os gráficos sem consultar novamente a API.

Verificação de 2026-10-17: **105 testes Vitest passaram** (12 novos), build Vite e `git diff --check` aprovados. Configurações de gráficos, tabelas, tooltips, resultados parciais, filtros e descarte de instâncias foram inspecionados em happy-dom com Chart.js substituído nos testes; navegação com API fake também verificada. Sem nova dependência, chamada ao Gemini ou alteração no backend. Próximo item: **W4.07 — limitações e métodos**.

## Limitações e métodos — W4.07

A aba **Limitações** preserva a ordem dos itens de `report.limitations`, mostrando título, explicação e `rule_id`. A aba **Métodos** apresenta origem do relatório, modelo configurado e início da investigação em UTC. Cada chamada mostra sequência, ferramenta, versão, estado, horário, duração em milissegundos, argumentos permitidos, fontes e métodos das evidências produzidas. Se houve reparo, aparecem somente estado, horário e duração. A duração por chamada não é apresentada como tempo total da investigação.

Argumentos são selecionados por ferramenta: talhões/período e operação quando aplicável, ou conjunto/métricas para solo. O componente não serializa objetos completos, não inclui campos desconhecidos e não mostra prompts, credenciais, dados brutos ou mensagens internas de falha/reparo. Erros de ferramenta usam mensagens locais; todo texto externo é inserido com `textContent`. Fallback é identificado como geração local, independentemente do modelo configurado. O adaptador rejeita limitações ausentes/inválidas e metadados malformados, incluindo datas sem fuso e durações inválidas.

Verificação de 2026-10-17: **116 testes Vitest passaram** (11 novos), build Vite e `git diff --check` aprovados. Testes cobrem campos privados ausentes do DOM, HTML malicioso, horário UTC, argumentos por ferramenta, zero/ausência, fallback, reparo e navegação das seis abas com API fake. Sem nova dependência, chamada ao Gemini ou alteração no backend. Próximo item: **W4.08 — relatório HTML**.

## Relatório HTML offline — W4.08

Após concluir uma investigação, clique em **Baixar relatório HTML** e abra o arquivo `farmlab-<investigation_id>.html` salvo pelo navegador. O backend gera o documento com visão geral, achados, recomendações, evidências, limitações, métodos, origem (Gemini ou fallback), modelo configurado e horários UTC. As evidências incluem tabelas de solo e série NDVI com referências internas; os valores vêm das análises já concluídas, sem novo cálculo ou chamada ao Gemini.

O arquivo contém seu próprio CSS e não precisa do servidor ou de internet para leitura. Todos os textos externos são escapados e o documento não contém JavaScript ou recursos externos. A política CSP também fica embutida no HTML. Os métodos mostram apenas campos permitidos; prompts, credenciais e mensagens internas de erro não são exportados.

`GET /api/investigations/{investigation_id}/report` retorna `text/html; charset=utf-8`, com nome de arquivo, `Content-Disposition: attachment` e `Cache-Control: no-store`. O HTML é armazenado apenas em memória, limitado aos **32 últimos relatórios por processo**. Após reiniciar o backend ou ultrapassar esse limite, relatórios removidos retornam 404; execute uma nova investigação para gerar outro. O arquivo já baixado continua disponível offline. Use um processo de backend, como no armazenamento de datasets.

O botão bloqueia cliques repetidos, mostra mensagens de progresso/erro, permite tentar novamente e cancela a requisição ao sair da tela. Falhas de download preservam a investigação e o dataset.

Verificação de 2026-10-17: **850 testes backend passaram, 9 privados ignorados e 3 avisos existentes (46,10 s); 126 testes Vitest passaram; build Vite e `git diff --check` aprovados**. Nove casos novos no backend e dez no frontend cobrem POST→GET, HTML malicioso, privacidade, armazenamento, download e falhas. O funcionamento offline foi verificado por gravação/leitura e parser HTML, conferindo ausência de recursos externos; o botão foi testado em happy-dom. Não houve inspeção visual manual em navegador, nova dependência ou chamada real ao Gemini. Próximo item: **W4.09 — servir o build pelo FastAPI**.
