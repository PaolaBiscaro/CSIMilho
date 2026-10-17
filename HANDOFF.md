# HANDOFF — FarmLab Investigator

## 1. Finalidade

Este arquivo organiza a passagem do projeto entre as pessoas responsáveis por cada semana. Ele deve permitir que a próxima pessoa continue o desenvolvimento sem depender de explicações por mensagem ou de conhecimento que ficou apenas com a pessoa anterior.

Cada responsável deve:

1. receber o repositório em estado verificável;
2. trabalhar somente na semana atribuída;
3. manter os contratos existentes;
4. registrar decisões e problemas;
5. entregar código testado e documentação atualizada;
6. preencher o handoff antes de passar o projeto adiante.

## 2. Divisão de responsabilidade

| Responsável | Escopo | Tarefas | Resultado principal |
| --- | --- | --- | --- |
| Pessoa 1 | Semana 1 | `W1.01` a `W1.16` | Projeto iniciado, arquivos importados e dados validados |
| Pessoa 1 / Codex | Reajuste pós-Semana 1 | `R1.01` a `R1.06` | Solo integrado e identidade visual atualizada |
| Pessoa 2 | Semana 2 | `W2.01` a `W2.14` | Ferramentas analíticas determinísticas funcionando |
| Pessoa 3 | Semana 3 | `W3.01` a `W3.15` | Gemini e harness controlado integrados |
| Pessoa 4 | Semana 4 | `W4.01` a `W4.15` | Interface integrada e versão pronta para apresentação |

A semana seguinte só deve começar depois que o gate de entrega da semana anterior estiver aprovado.

## 3. Documentos obrigatórios

Antes de alterar código, toda pessoa deve ler:

1. `SPEC.md` — fonte principal dos requisitos técnicos;
2. `PROJETO.md` — visão, objetivo e limites do produto;
3. `PIPELINES.md` — fluxos esperados;
4. `PLANEJAMENTO_CODEX.md` — tarefas e verificações;
5. `HANDOFF.md` — estado real recebido da equipe.

Ordem de autoridade:

```text
SPEC.md
→ PROJETO.md
→ PIPELINES.md
→ PLANEJAMENTO_CODEX.md
→ HANDOFF.md
```

O handoff informa o que foi realmente implementado. Ele não autoriza alterar a especificação. Se o código e o `SPEC.md` divergirem, registrar o problema e alinhar com o grupo antes de continuar.

## 4. Regras de colaboração

### 4.1 Git

- `main` deve permanecer utilizável;
- cada semana deve ser desenvolvida em uma branch própria;
- nomes sugeridos:
  - `week-1-foundation-data`;
  - `week-2-analytics`;
  - `week-3-gemini-harness`;
  - `week-4-integration-demo`;
- não trabalhar diretamente na branch de outra semana;
- fazer commits pequenos e descritivos;
- a branch da semana seguinte deve nascer da `main` depois do merge anterior;
- conflitos não devem ser resolvidos removendo testes ou requisitos silenciosamente.

### 4.2 Pull request

Cada semana deve terminar com um pull request contendo:

- intervalo de tarefas concluídas;
- resumo das alterações;
- como executar;
- testes executados;
- evidências manuais relevantes;
- decisões técnicas;
- pendências e limitações;
- confirmação de que nenhum segredo ou CSV privado foi versionado.

### 4.3 Segredos e dados

- nunca commitar `.env`;
- nunca colocar `GEMINI_API_KEY` em HTML, JavaScript do navegador, teste ou documentação;
- manter `.env.example` sem valor real;
- não versionar CSVs reais sem autorização;
- testes devem usar fixtures pequenas e artificiais sempre que possível;
- o pacote completo da apresentação deve ficar fora do repositório ou em local explicitamente autorizado.

### 4.4 Mudanças de contrato

Uma pessoa não pode alterar sozinha:

- nomes dos endpoints;
- schemas de request ou response;
- nomes das ferramentas analíticas;
- fórmulas;
- estrutura do relatório;
- responsabilidade do Gemini;
- regras de causalidade e rastreabilidade.

Se uma alteração for necessária:

1. registrar a proposta em **Decisões pendentes**;
2. indicar arquivos e semanas afetadas;
3. obter acordo do grupo;
4. atualizar primeiro o `SPEC.md`;
5. atualizar diagramas, planejamento, testes e código afetados.

## 5. Fluxo de passagem

### Quem entrega

1. conclui apenas as tarefas da própria semana;
2. executa testes automatizados;
3. executa o cenário manual descrito no gate;
4. atualiza checkboxes e Diário de execução;
5. preenche o registro da semana neste arquivo;
6. abre o pull request;
7. informa à próxima pessoa o commit aprovado ou mergeado.

### Quem recebe

1. confirma que está na revisão correta da `main`;
2. lê o registro da semana anterior;
3. instala dependências pelas instruções do README;
4. executa os testes informados;
5. repete o cenário mínimo do gate;
6. registra qualquer divergência antes de iniciar código novo;
7. cria a branch da própria semana.

## 6. Gate geral de handoff

Uma semana não está pronta para entrega se alguma resposta abaixo for “não”.

- [x] Todas as tarefas P0 da semana foram concluídas.
- [x] Tarefas não concluídas estão registradas com motivo ou não existem.
- [x] O código inicia seguindo apenas o README.
- [x] Os testes informados passam em ambiente limpo.
- [x] O cenário manual da semana funciona.
- [x] Contratos públicos não foram alterados silenciosamente.
- [x] Documentação e checklist refletem o código atual.
- [x] Não há chave, `.env` ou dado privado no Git.
- [x] Erros conhecidos estão registrados.
- [x] A próxima pessoa sabe exatamente por onde começar.

## 7. Handoff da Semana 1 para a Semana 2

### A Semana 1 deve entregar

- estrutura do repositório;
- backend FastAPI inicial;
- frontend Vite Vanilla inicial;
- configuração e `.env.example`;
- schemas de dados normalizados;
- leitura e validação dos seis CSVs;
- catálogo de ordens por `serviceOrderNumber` e candidatos um-para-muitos;
- ligação espacial das operações aos talhões candidatos;
- ligação das séries NDVI aos talhões;
- store temporário por `dataset_id`;
- `POST /api/datasets`;
- tela de importação funcional;
- testes de dados e API;
- README com comandos válidos.

### A Semana 1 não deve entregar

- fórmulas analíticas finais;
- integração real com Gemini;
- harness;
- relatório final;
- deploy.

### Gate específico

- [x] `GET /api/health` retorna 200.
- [x] O frontend abre sem erro de console.
- [x] Os seis arquivos podem ser importados pelo navegador.
- [x] Os quatro talhões são reconhecidos.
- [x] Os pares Grão e Silagem são formados corretamente.
- [x] Arquivo ausente e coluna ausente produzem erro claro.
- [x] `dataset_id` permite recuperar o estado temporário.
- [x] Os testes da Semana 1 passam.

### O que a Semana 2 precisa encontrar

Objetos normalizados estáveis para:

```text
fields
ndvi_observations
planting_operations
fertilization_operations
service_order_mapping
service_order_number_mapping
service_order_operations
dataset_metadata
```

Nenhuma análise da Semana 2 deve voltar a ler os CSVs diretamente. Ela deve consumir os objetos normalizados entregues pela Semana 1.

## 7.1 Handoff do reajuste pós-Semana 1 para a Semana 2

O registro da Semana 1 permanece válido como histórico da versão de seis arquivos. Entretanto, a Semana 2 só pode começar depois deste reajuste.

### O reajuste deve entregar

- contrato de upload com sete arquivos obrigatórios;
- normalização de `soil_analysis.csv` no store como `soil_samples`;
- resposta da API com quantidade de amostras, grupos disponíveis e `scope: dataset`;
- tela de importação reconhecendo o sétimo arquivo;
- tokens CSS com `#895129` como cor principal;
- fixtures e testes atualizados sem quebrar as seis fontes anteriores;
- README e documentação coerentes.

### Limites que não podem ser removidos

- não associar `AMOSTRA` a `idField` sem uma chave real;
- não chamar `_2` de profundidade, camada, época ou repetição;
- não aplicar faixas de suficiência sem unidades e referência agronômica documentadas;
- não tornar `agricultural_inputs.csv` obrigatório sem definir uma ligação confiável.

### Gate específico do reajuste

- [x] Sete arquivos podem ser importados pelo navegador.
- [x] O pacote sem `soil_analysis.csv` retorna erro compreensível.
- [x] O pacote atual reconhece oito amostras válidas.
- [x] `soil_samples` fica disponível no store com escopo geral.
- [x] Conjunto 1 e Conjunto 2 são preservados sem inferência de profundidade.
- [x] A interface usa `#895129` como cor primária e mantém contraste/foco.
- [x] Pytest, Vitest e build Vite passam.
- [x] O Registro — Reajuste pós-Semana 1 foi preenchido.

### O que a Semana 2 precisa encontrar adicionalmente

```text
soil_samples
soil_metadata.sample_count
soil_metadata.scope = dataset
soil_metadata.measurement_groups
```

## 7.2 Handoff do reajuste visual para a Semana 2

Antes de `W2.01`, o frontend passa a oferecer prévias navegáveis das três áreas dentro de um shell de dashboard inspirado nas referências fornecidas. A cor primária continua sendo `#895129`.

### O reajuste visual deve entregar

- cabeçalho horizontal com marca, navegação em pílulas e estado ativo acessível;
- tela de Dados funcional reaproveitada na nova grade de cards;
- prévia de Comparação com controles clicáveis e mocks locais;
- prévia de Investigação com abas internas clicáveis e mocks locais;
- selo visível **Prévia · dados demonstrativos** nas telas ainda não conectadas;
- responsividade sem rolagem horizontal em 1440 px, 820 px e 390 px.

### Limites que a Semana 2 deve preservar

- mocks não são evidências e não podem alimentar o backend;
- a prévia não conclui nenhuma tarefa `W2.*`, `W3.*` ou `W4.*`;
- nenhum número demonstrativo pode ser apresentado como calculado, real ou produzido pelo Gemini;
- os componentes visuais devem aceitar substituição futura dos mocks pelos contratos reais;
- a importação e a validação já entregues continuam funcionais.

### Gate do reajuste visual

- [x] Os seis documentos-base foram atualizados antes do frontend.
- [x] Dados, Comparação e Investigação podem ser abertas pela navegação.
- [x] Continuar leva à prévia de Comparação.
- [x] O CTA da Comparação leva à prévia de Investigação sem chamar a API.
- [x] As abas internas da Investigação trocam o conteúdo visível.
- [x] As telas mockadas estão claramente identificadas.
- [x] A paleta mantém `#895129` como primária.
- [x] Vitest, build e revisão responsiva passam.

## 7.3 Diretriz de visualização para as próximas semanas

A prévia entregue em `R1.08` valida navegação e composição, mas seus gráficos ilustrativos não representam o nível final esperado. As Semanas 2 e 4 devem transformar a aba **Solo** em uma área analítica prioritária, inspirada na densidade e na narrativa do dashboard de referência, sem trocar a identidade marrom.

A Semana 2 deve fornecer evidências e contratos próprios para distribuição por métrica, comparação pareada Conjunto 1 × Conjunto 2 e composição válida de textura. A Semana 4 deve transformar esses contratos em cards, gráficos interativos, tooltips e tabelas acessíveis. Nenhum gráfico pode criar mapa, tempo, profundidade, unidade, vínculo com talhão ou faixa agronômica que os dados não fornecem.

## 8. Handoff da Semana 2 para a Semana 3

### A Semana 2 deve entregar

- schema comum de evidência;
- `validate_comparison`;
- `compare_ndvi`;
- `check_initial_condition`;
- `compare_population`;
- `application_compliance`;
- `summarize_soil_analysis`;
- `compare_soil_measurement_groups`;
- contratos de visualização do solo para distribuição, comparação pareada e composição de textura;
- registry fechado das ferramentas;
- testes unitários das fórmulas;
- teste de regressão com o pacote da apresentação;
- tela de comparação e componentes de gráficos para NDVI e solo.

### A Semana 2 não deve entregar

- prompt final do Gemini;
- loop do harness;
- tentativa de reparo;
- fallback narrativo completo;
- relatório final integrado.

### Gate específico

- [x] Grão × Grão é permitido.
- [x] Silagem × Silagem é permitido.
- [x] Grão × Silagem é bloqueado.
- [x] NDVI usa somente datas pareadas.
- [x] Condição inicial usa corte anterior ao plantio.
- [x] População é ponderada pela área.
- [x] Conformidade é ponderada pela área e pode ultrapassar 100%.
- [x] O resumo do solo calcula estatísticas descritivas sobre valores válidos.
- [x] A comparação de solo é pareada por `AMOSTRA` e usa Conjunto 2 menos Conjunto 1.
- [x] Nenhuma evidência de solo atribui amostra a talhão ou presume profundidade.
- [x] Os contratos visuais do solo carregam valores, unidade, contagem, fonte e limitações sem misturar métricas incompatíveis.
- [x] Cada ferramenta retorna uma evidência conforme o schema.
- [x] O registry rejeita ferramentas desconhecidas.
- [x] O baseline do pacote real foi conferido; auditoria e reprodução em [BASELINE_W2.md](BASELINE_W2.md).

### O que a Semana 3 precisa encontrar

Cada ferramenta deve poder ser chamada desta forma lógica:

```text
tool(dataset_id, target_field_id, reference_field_id, period, ...)
→ evidence
```

As ferramentas de solo usam a assinatura lógica abaixo porque o arquivo não possui vínculo com talhão:

```text
soil_tool(dataset_id, measurement_group ou metrics)
→ evidence com scope = dataset
```

A Semana 3 não deve reproduzir fórmulas dentro do prompt. Ela deve registrar e chamar as funções já testadas.

## 9. Handoff da Semana 3 para a Semana 4

### A Semana 3 deve entregar

- SDK oficial do Gemini configurado no backend;
- endpoint de teste da API;
- schemas do harness;
- system prompt;
- Function Calling baseado no registry;
- validação de chamadas e argumentos;
- loop limitado do orchestrator;
- trace das ferramentas;
- síntese estruturada;
- validação de evidências, números e linguagem causal;
- uma tentativa de reparo;
- fallback determinístico;
- `POST /api/investigations`;
- teste com cliente fake;
- teste real controlado com Gemini.

### A Semana 3 não deve entregar

- chave real no repositório;
- execução de código produzido pelo modelo;
- acesso do Gemini aos CSVs brutos;
- interface final polida;
- nova ferramenta fora da especificação.

### Gate específico

- [x] A aplicação inicia sem chave.
- [x] O teste do Gemini funciona com chave válida.
- [x] O Gemini só pode chamar ferramentas do registry.
- [x] IDs fora do dataset são bloqueados.
- [x] O limite de chamadas é respeitado.
- [x] Número inventado é rejeitado.
- [x] Evidência inexistente é rejeitada.
- [x] Linguagem causal é rejeitada.
- [x] Uma falha após reparo aciona o fallback.
- [x] A resposta da investigação segue o schema do `SPEC.md`.

### O que a Semana 4 precisa encontrar

Um endpoint estável que retorne:

```text
investigation_id
status
generated_by
report
evidence
chart_data
trace
warnings
```

A Semana 4 deve consumir esse contrato sem criar cálculos paralelos no frontend.

## 10. Handoff final da Semana 4 para o grupo

### A Semana 4 deve entregar

- frontend integrado ao endpoint de investigação;
- visão geral escrita do Gemini;
- achados, recomendações e evidências;
- gráfico real de NDVI;
- dashboard analítico de solo com distribuição, comparação pareada, composição de textura e alternativas tabulares;
- abas de limitações e métodos;
- relatório HTML;
- build servido pelo FastAPI;
- painel de pré-apresentação;
- tratamento de falhas e fallback visível;
- teste ponta a ponta;
- roteiro da apresentação;
- versão congelada e identificável.

### Gate específico

- [ ] O fluxo completo funciona em uma única URL local.
- [ ] Os CSVs são importados ao vivo.
- [ ] A investigação real pode ser executada na interface.
- [ ] A visão geral identifica Gemini ou fallback corretamente.
- [ ] O gráfico corresponde aos pontos da evidência.
- [ ] Os gráficos de solo correspondem às evidências, mostram amostras/unidades/fontes e não inventam mapa, tempo ou profundidade.
- [ ] Nenhum conteúdo externo é inserido com `innerHTML` inseguro.
- [ ] O relatório abre offline.
- [ ] Falha do Gemini não derruba a aplicação.
- [ ] O fluxo foi ensaiado no computador da apresentação.
- [ ] A versão apresentada possui tag ou commit registrado.

## 11. Registro obrigatório de cada semana

Cada responsável deve substituir os campos da própria semana antes da entrega.

### Registro — Semana 1

```yaml
responsavel: Codex
branch: codex/week-1-foundation-data
commit_entregue: nao_criado
data: 2026-09-23
status: pronta
tarefas_concluidas: [W1.01, W1.02, W1.03, W1.04, W1.05, W1.06, W1.07, W1.08, W1.09, W1.10, W1.11, W1.12, W1.13, W1.14, W1.15, W1.16]
tarefas_pendentes: []
comandos_para_executar:
  - "cd backend && uv sync --locked"
  - "cd backend && uv run uvicorn app.main:app --reload"
  - "cd frontend && pnpm install --frozen-lockfile"
  - "cd frontend && pnpm dev"
testes_executados:
  - "cd backend && uv run pytest"
  - "cd frontend && pnpm test"
  - "cd frontend && pnpm build"
  - "validação direta do pacote real em demo-data/local"
  - "importação manual no navegador com demo-data/local"
resultado_dos_testes: "49 testes Pytest e 4 testes Vitest passaram; build Vite passou; pacote real retorna 201/ready_with_warnings, reconhece 4 talhões, forma 2 pares e habilita Continuar"
decisoes_tomadas:
  - "Pares da Semana 1 exigem mesma finalidade, alvo digital, referência convencional e dados mínimos de NDVI, plantio e fertilização; score analítico fica para W2"
  - "Empate espacial de até 1 m é ambíguo; 500–1.000 m gera aviso; acima de 1.000 m bloqueia"
  - "serviceOrderNumber é canonicalizado e resolvido pelo catálogo; ordens compartilhadas produzem conjuntos de candidatos válidos"
  - "Operações usam ponto representativo e fallback por interseção única de pelo menos 50%; empate espacial continua impeditivo"
  - "O alias Convecional é corrigido para classificação e rótulo, preservando o nome original e emitindo field_name_normalized"
problemas_conhecidos:
  - "TestClient emite dois avisos de depreciação de dependências, sem falha funcional"
  - "O pacote real fica com qualidade 60 por 14 avisos agregados; 9.599 linhas operacionais não atribuídas e 30 geometrias inválidas são descartadas conforme o SPEC, sem ambiguidade impeditiva"
arquivos_importantes_alterados:
  - "backend/pyproject.toml e backend/uv.lock"
  - "backend/app/api/datasets.py"
  - "backend/app/data/contracts.py"
  - "backend/app/data/loader.py"
  - "backend/app/data/normalizer.py"
  - "backend/app/data/linker.py"
  - "backend/app/data/session_store.py"
  - "backend/tests/conftest.py e testes de dados/API"
  - "backend/tests/fixtures/manual/"
  - "frontend/src/ui/upload.js"
  - "README.md"
primeiro_passo_da_semana_seguinte: "Executar R1.01 antes de W2.01; ampliar o contrato para sete arquivos sem apagar ou refazer o histórico concluído da Semana 1."
```

### Registro — Reajuste pós-Semana 1

```yaml
responsavel: Codex
branch: feat/heloisa
commit_entregue: "working tree sobre 5bc3e70; nenhum commit criado automaticamente"
data: 2026-10-07
status: concluido
tarefas_concluidas: [R1.01, R1.02, R1.03, R1.04, R1.05, R1.06]
tarefas_pendentes: []
comandos_para_executar:
  - "cd backend && uv sync --locked"
  - "cd backend && uv run uvicorn app.main:app --reload"
  - "cd frontend && pnpm install --frozen-lockfile"
  - "cd frontend && pnpm dev"
testes_executados:
  - "cd backend && uv run pytest"
  - "cd frontend && pnpm test"
  - "cd frontend && pnpm build"
  - "POST /api/datasets com os sete arquivos reais de demo-data/local"
  - "importação dos sete arquivos reais pelo navegador e revisão em 1440, 820 e 390 px"
resultado_dos_testes: "56 testes Pytest e 4 testes Vitest passaram; build Vite passou; pacote real retorna 201/ready_with_warnings, qualidade 60, 15 avisos, 4 talhões, 2 pares e 8 amostras de solo; Continuar habilitado"
decisoes_tomadas:
  - "soil_analysis.csv é obrigatório e tem escopo geral do dataset"
  - "colunas _2 são Conjunto 2 até que seu significado seja documentado"
  - "a cor primária do frontend é #895129"
  - "valores ausentes ou inválidos do solo viram ausência, nunca zero"
  - "soil_samples usa sample_id, scope, group_1 e group_2; cópias do store isolam também os dicionários internos"
problemas_conhecidos:
  - "soil_analysis.csv não possui vínculo com idField, coordenada, data ou profundidade"
  - "TestClient emite dois avisos de depreciação de dependências, sem falha funcional"
arquivos_importantes_alterados:
  - "backend/app/data/contracts.py, loader.py, normalizer.py e session_store.py"
  - "backend/app/api/datasets.py"
  - "backend/tests/ e backend/tests/fixtures/manual/soil_analysis.csv"
  - "frontend/src/ui/upload.js e frontend/src/main.js"
  - "frontend/src/styles/"
  - "README.md, PLANEJAMENTO_CODEX.md e HANDOFF.md"
primeiro_passo_da_semana_seguinte: "Iniciar W2.01 consumindo objetos normalizados, inclusive soil_samples; não reler CSVs nas ferramentas."
```

### Registro — Reajuste visual pré-Semana 2

```yaml
responsavel: Codex
branch: feat/heloisa
commit_entregue: "working tree sobre 5bc3e70; nenhum commit criado automaticamente"
data: 2026-10-07
status: concluido
tarefas_concluidas: [R1.07, R1.08]
tarefas_pendentes: []
testes_executados:
  - "cd backend && pytest"
  - "cd frontend && vitest run"
  - "cd frontend && vite build"
  - "navegação e interações pelo Chrome em 1440, 820 e 390 px"
resultado_dos_testes: "56 testes Pytest e 7 testes Vitest passaram; build Vite passou; Dados, Comparação, Investigação, troca de talhões e abas internas foram validados; não houve overflow horizontal"
decisoes_tomadas:
  - "manter #895129 como cor primária"
  - "usar shell claro, cards brancos arredondados e navegação horizontal em pílulas"
  - "isolar mocks em frontend/src/mocks e identificar toda prévia como demonstrativa"
problemas_conhecidos:
  - "Comparação e Investigação ainda não consomem contratos analíticos, por decisão de escopo"
arquivos_importantes_alterados:
  - "frontend/src/main.js, frontend/src/ui/navigation.js"
  - "frontend/src/ui/comparison-preview.js e frontend/src/ui/investigation-preview.js"
  - "frontend/src/mocks/preview-data.js e frontend/src/styles/"
  - "HANDOFF.md, PIPELINES.md, PLANEJAMENTO_CODEX.md, PROJETO.md, README.md e SPEC.md"
primeiro_passo_da_semana_seguinte: "Iniciar W2.01 sem reaproveitar os valores mockados como evidência e substituir os mocks somente por contratos reais validados."
```

### Registro — Semana 2

```yaml
responsavel: Codex
branch: passo_2
commit_entregue: "alterações locais; nenhum commit criado automaticamente"
data: 2026-10-13
status: concluida
tarefas_concluidas: [W2.01, W2.02, W2.03, W2.04, W2.05, W2.06, W2.07, W2.08, W2.09, W2.10, W2.11, W2.12, W2.13, W2.14]
tarefas_pendentes: []
comandos_para_executar:
  - "cd backend && uv run uvicorn app.main:app --reload"
  - "cd frontend && pnpm dev"
testes_executados:
  - "cd backend && .venv/bin/python -m pytest"
  - "cd backend && FARMLAB_REAL_DATA_DIR='/Users/lucashygidio/Downloads/FarmLab' .venv/bin/python -m pytest"
  - "cd frontend && pnpm test && pnpm build"
  - "git diff --check"
  - "navegador: importação dos sete CSVs artificiais, comparação e bloqueio de Grão × Silagem"
  - "navegador: gráficos de solo e NDVI, tabelas, troca de abas e responsividade"
resultado_dos_testes: "163 Pytest com pacote real e 25 Vitest passaram; build aprovado. Nove regressões reais também passaram isoladamente; sem FARMLAB_REAL_DATA_DIR são ignoradas explicitamente. Revisão visual da W2.13 preservada, sem overflow horizontal ou erros de console"
decisoes_tomadas:
  - "Diagnóstico disponível somente em APP_ENV=development; sem Gemini ou execução de código externo"
  - "Comparação após upload consulta critérios reais locais; gráficos continuam usando fixtures claramente identificadas"
  - "NDVI exige uma data pareada; menos de cinco gera aviso e reduz o score"
  - "Quartis por interpolação linear; textura normalizada para 100% somente quando a soma original está entre 95 e 105"
  - "IDs de evidência locais à investigação; chamadores podem compartilhar o gerador entre ferramentas"
  - "Baseline real: 29 datas NDVI, gap -0,024985204049, população 61306,266516/63629,025950 e calagem 57,327136%/97,500150%; oito amostras de solo"
  - "Regressão compara API com recálculo independente dos CSVs; hashes fixam o pacote, contagens são exatas e floats usam tolerância absoluta 1e-8 sem tolerância relativa"
problemas_conhecidos:
  - "Importação real mantém 15 avisos e qualidade 60; descartes e diferenças frente ao protótipo estão em BASELINE_W2.md"
  - "Código do protótipo histórico indisponível: origem exata das aproximações antigas não confirmada; baseline atual auditado diretamente nos arquivos"
  - "Aviso de depreciação Starlette/httpx já existente"
arquivos_importantes_alterados:
  - "backend/app/analytics/, app/harness/schemas.py e registry.py"
  - "backend/app/api/datasets.py, diagnostics.py e app/main.py"
  - "backend/tests/test_analytics.py, test_diagnostics.py e test_evidence.py"
  - "backend/tests/test_real_baseline.py, real_baseline_reference.py e fixtures/real_baseline.json"
  - "BASELINE_W2.md"
  - "frontend/src/ui/comparison.js, analytical-panels.js e investigation-preview.js"
  - "frontend/src/charts/analytics-charts.js e mocks/analytics-preview.json"
  - "frontend/src/main.js, api.js, styles/components.css, package.json e pnpm-lock.yaml"
  - "frontend/tests/ e documentação de planejamento/execução"
primeiro_passo_da_semana_seguinte: "Aguardar próxima solicitação do usuário antes de iniciar W3.01; Semana 2 concluída."
```

### Registro — Semana 3

```yaml
responsavel: Codex
branch: feat/lorena
commit_entregue: "alterações locais sobre f9b30df; nenhum commit criado automaticamente"
data: 2026-10-17
status: concluida
tarefas_concluidas: [W3.01, W3.02, W3.03, W3.04, W3.05, W3.06, W3.07, W3.08, W3.09, W3.10, W3.11, W3.12, W3.13, W3.14, W3.15]
tarefas_pendentes: []
tarefas_em_validacao: []
validacao_real_w3_15:
  data: 2026-10-17
  status: "Concluída, com investigação real e relatório/trace inspecionados."
  modelo: gemini-2.5-flash
  timeout_local_segundos: 120
  investigation_id: c616c852-424a-45cb-91e6-769a46f56717
  resultado: "passed=true, generated_by=gemini; oito ferramentas com sucesso; sem reparo ou fallback; evidências correspondentes ao trace."
  artefato: "backend/.local/w3-15/20261017T135442Z-c616c852-424a-45cb-91e6-769a46f56717.json (local e ignorado pelo Git)"
  inspecao: "NDVI e população iguais nas fixtures, conformidade de calagem coerente, solo no escopo do dataset, diferenças entre conjuntos sem interpretação temporal/profundidade, condição inicial indisponível e limitações explícitas."
  conexao: "Função do endpoint Gemini também testada com a chave real: success=true, error_code=null, 872 ms."
  regressao: "841 passaram, 9 testes privados ignorados, 3 avisos existentes em 41,40 s, incluindo módulos HTTP. Após o último ajuste textual: 100 testes focados passaram em 12,62 s."
  ajustes: "Prompt mais explícito sobre unidades, citações e limitações únicas; reference_findings reutiliza os templates verificados W3.13 sobre os fatos atuais. Gemini seleciona/ordena achados e redige a narrativa; resposta inteira é revalidada. Cálculos e validadores preservados. Teste de health isolado do .env local."
validacao_preparatoria_w3_15:
  status: "Histórico de 2026-10-16; a pendência de chave/teste real foi resolvida em validacao_real_w3_15."
  pacote: "Sete fixtures pequenas de backend/tests/fixtures/manual; par 103144 x 103145, full_season."
  comandos:
    - "Em backend: .venv/Scripts/python.exe -m app.harness.smoke --check-only"
    - "Após configurar GEMINI_API_KEY no .env local, em backend: .venv/Scripts/python.exe -m app.harness.smoke"
  testes: "14 testes novos; 100 focados passaram. Regressão sem módulos HTTP: 759 passaram, 9 reais ignorados, 3 avisos existentes em 39,39 s. Check-only aprovou os sete CSVs e confirmou ausência de chave."
  comando_regressao: "Em backend: .venv/Scripts/python.exe -m pytest --ignore=tests/test_api.py --ignore=tests/test_diagnostics.py --ignore=tests/test_gemini_api.py --ignore=tests/test_health.py --ignore=tests/test_investigations_api.py --basetemp=.local/pytest-w3-15-NOVO-ID --tb=short"
  ambiente: "Criar backend/.local antes dos testes e usar NOVO-ID único para temporários: a pasta temporária padrão do sandbox negou criação. Não repetir a suíte HTTP neste sandbox; validação completa anterior de 827 testes foi fornecida pelo usuário."
  artefatos: "Relatório/evidências/trace em backend/.local/w3-15, ignorado pelo Git. Testes automatizados usam provedor simulado e diretórios temporários, nunca a chave local."
  pendencia: "Resolvida em 2026-10-17: execução real aprovada e inspecionada. W4 não iniciada."
comandos_para_executar:
  - "cd backend; uv sync --locked"
  - "cd backend; uv run uvicorn app.main:app --reload"
  - "cd frontend; pnpm dev"
testes_executados:
  - "cd backend; .venv/Scripts/python.exe -m pytest tests/test_gemini_api.py tests/test_gemini_client.py tests/test_health.py --tb=short"
  - "cd backend; .venv/Scripts/python.exe -m pytest tests/test_harness_schemas.py tests/test_evidence.py --tb=short"
  - "cd backend; .venv/Scripts/python.exe -m pytest tests/test_gemini_tools.py tests/test_gemini_client.py tests/test_harness_schemas.py --tb=short"
  - "cd backend; .venv/Scripts/python.exe -m pytest tests/test_call_validators.py --tb=short"
  - "cd backend; .venv/Scripts/python.exe -m pytest tests/test_investigation_trace.py --tb=short"
  - "cd backend; .venv/Scripts/python.exe -m pytest tests/test_orchestrator.py --tb=short"
  - "cd backend; .venv/Scripts/python.exe -m pytest tests/test_synthesis.py tests/test_orchestrator.py --tb=short"
  - "cd backend; .venv/Scripts/python.exe -m pytest tests/test_report_validation.py tests/test_synthesis.py --tb=short"
  - "cd backend; .venv/Scripts/python.exe -m pytest tests/test_language_validation.py tests/test_synthesis.py --tb=short"
  - "cd backend; .venv/Scripts/python.exe -m pytest tests/test_report_repair.py tests/test_synthesis.py tests/test_harness_schemas.py tests/test_investigation_trace.py --tb=short"
  - "cd backend; .venv/Scripts/python.exe -m pytest tests/test_fallback.py tests/test_report_validation.py tests/test_language_validation.py --tb=short"
  - "cd backend; .venv/Scripts/python.exe -m pytest tests/test_fallback.py --tb=short"
  - "cd backend; .venv/Scripts/python.exe -m pytest tests/test_investigations.py tests/test_orchestrator.py tests/test_synthesis.py tests/test_report_repair.py --tb=short"
  - "cd backend; .venv/Scripts/python.exe -m pytest tests/test_investigations_api.py --collect-only"
  - "cd backend; .venv/Scripts/python.exe -m pytest --ignore=tests/test_api.py --ignore=tests/test_diagnostics.py --ignore=tests/test_gemini_api.py --ignore=tests/test_health.py --ignore=tests/test_investigations_api.py --tb=short"
  - "W3.04: importação de app.harness.prompts e inspeção AST do literal SYSTEM_PROMPT; auditoria de credenciais, IDs concretos e caminhos; revisão contra SPEC seções 3, 11, 12 e 15."
  - "cd backend; .venv/Scripts/python.exe -m pytest --tb=short -o faulthandler_timeout=30"
  - "cd backend; .venv/Scripts/python.exe -m pytest"
  - "cd backend; uv sync --locked"
  - "cd backend; uv pip check --python .venv/Scripts/python.exe"
  - "git diff --check"
  - "Servidor Uvicorn temporário em 127.0.0.1: GET /api/health, POST /api/gemini/test sem chave e GET /openapi.json; encerrado ao final."
resultado_dos_testes: "W3.15 concluída em 2026-10-17: investigação real passou sem reparo/fallback, diagnóstico de conexão aprovado. Suíte completa: 841 passaram, 9 ignorados e 3 avisos em 41,40 s; após o último ajuste textual, 100 testes focados passaram. Histórico: W3.14 concluída em 2026-10-16: usuário executou .venv/Scripts/python.exe -m pytest --tb=short em backend e enviou a saída completa: 827 passaram, 9 reais ignorados e 3 avisos existentes em 50,61 s. Inclui 41 testes novos do fluxo, função da rota, importação, OpenAPI e SDK em memória, além dos 24 novos testes HTTP. Antes disso, 745 passaram no ambiente restrito, excluindo módulos HTTP. A execução local informada pelo usuário resolveu a pendência causada pelo bloqueio de socket do TestClient no sandbox e pelo limite de uso da revisão automática. Nenhuma chamada ao Gemini real."
decisoes_tomadas:
  - "Mantida a branch existente feat/lorena no mesmo commit da entrega W2 (f9b30df); main local permanece anterior à W2."
  - "SDK google-genai 2.31.0 fixado no lockfile; httpx passou de dev para dependência de execução."
  - "Cliente síncrono por operação/investigação, criado somente na primeira geração e fechado pelo contexto with."
  - "GEMINI_API_KEY é passada explicitamente para a Developer API; GOOGLE_API_KEY e seleção de Enterprise/Vertex no ambiente não substituem essa escolha."
  - "Timeout HTTP usa GEMINI_TIMEOUT_SECONDS; orchestrator reduz cada chamada ao tempo restante e compartilha o prazo total e uma repetição única de 429 entre planejamento, síntese e reparo."
  - "Execução automática de ferramentas e retries do SDK desativados para preservar o controle do harness."
  - "Erros expõem somente código, status HTTP quando disponível e mensagem local; corpo do provedor e cadeia de exceção não são exibidos."
  - "POST /api/gemini/test não requer corpo: usa prompt fixo, modelo/chave do backend, um candidato e máximo de 32 tokens; não encaminha conteúdo fornecido pelo navegador."
  - "A rota retorna success, model, latency_ms, message e error_code em sucesso e falha; latência medida por relógio monotônico e esquema documentado no OpenAPI."
  - "Chave ausente retorna 503; autenticação 401, permissão 403, cota 429, timeout 504, indisponibilidade 503 e outras falhas do provedor 502."
  - "Teste mínimo sem retry; resposta vazia ou bloqueada falha. MAX_TOKENS confirma conectividade, sem avaliar qualidade da geração."
  - "W3.03 define somente contratos estruturais: objetos fechados, pergunta de 10–500 caracteres, força weak/moderate/strong e origem gemini/deterministic_fallback."
  - "InvestigationResponse mantém as oito chaves do SPEC; trace reúne trace_id, dataset_id, model, created_at e calls. Metadados de origem são atribuídos pelo backend, fora da narrativa gerada."
  - "Trace usa os tipos de argumentos da W2 conforme a ferramenta; sucesso exige evidências/fontes, falha exige code/message locais e não produz evidências."
  - "Evidence foi extraída para evidence_schema.py e reexportada por schemas.py para preservar imports e evitar ciclo com analytics/contracts.py. Os sete tipos concretos são preservados na resposta final."
  - "chart_data usa ndvi opcional e listas soil_summaries/soil_groups, reutilizando séries, quartis, pares e textura da W2. Ausência é null/lista vazia; não há recálculo nem inferência de profundidade."
  - "SYSTEM_PROMPT estático em prompts.py orienta análise observacional, evidências existentes, números apenas das ferramentas, ausência de causalidade, restrições de solo e schema narrativo."
  - "Pergunta e textos externos são dados não confiáveis. O orchestrator envia SYSTEM_PROMPT separado do contexto, sem interpolar conteúdo da sessão na instrução. Não foi alterado o prompt mínimo de POST /api/gemini/test."
  - "build_gemini_tool() deriva as sete FunctionDeclaration exclusivamente de TOOLS e dos schemas Pydantic dos argumentos; a contagem antiga de cinco no planejamento foi corrigida para incluir as duas ferramentas de solo do SPEC."
  - "parameters_json_schema preserva objetos fechados, referências locais, uniões, defaults, enums e filtros nulos. Acrescentadas descrições aos argumentos sem mudar campos ou validações. Objetos novos a cada construção evitam mutações entre requisições."
  - "O adaptador importa os tipos do SDK somente quando chamado, sem criar cliente nem acessar chave. Não passa callables Python, datasets internos, DataFrames, caminhos, store ou geradores de IDs ao SDK."
  - "ToolCallValidator é instanciado uma vez por investigação e usado sequencialmente. Copia a seleção, valida argumentos pelo registry e confere dataset, talhões e período antes de reservar chamadas."
  - "Chamadas aceitas ficam reservadas antes da execução, inclusive se a análise falhar depois; chamadas rejeitadas não alteram o histórico. O chamador deve executar/registrar os argumentos normalizados retornados."
  - "Repetições consideram defaults, UUIDs, espaços, operação canônica e conjunto de métricas de solo. A ordenação de métricas é ignorada apenas na identidade da chamada; o retorno mantém a ordem sem duplicatas."
  - "Erros locais expõem somente código e mensagem estática. O validador reconsulta a sessão a cada chamada e não executa ferramentas nem cria trace."
  - "InvestigationRecorder gera UUIDs de investigação/trace, mede execuções com relógio monotônico e fornece snapshot defensivo de InvestigationTrace. Um EvidenceIdGenerator é compartilhado apenas pelas ferramentas dessa instância."
  - "run_tool integra validação W3.06 e execução local de uma ferramenta; retorna evidência em sucesso ou lança ToolExecutionError após registrar falha. Rejeições anteriores à execução não geram entrada nem armazenam argumentos brutos."
  - "O trace projeta somente metadados e argumentos normalizados; não copia pergunta, configuração do provedor, notas, séries, CSVs ou exceções originais. Fontes desconhecidas, versão inconsistente e ID repetido são rejeitados como metadados inválidos."
  - "Falhas não produzem evidências e usam fontes vazias por não haver resultado validado; mensagens são locais. O resultado analítico completo fica fora do trace para consumo do orchestrator."
  - "run_investigation_tools retorna ToolLoopResult interno com evidências, trace, avisos e motivo de parada; texto livre do modelo serve apenas como sinal de finalização. Não produz InvestigationReport nem InvestigationResponse."
  - "Primeiro contexto contém apenas pergunta, IDs/rótulos selecionados, período, arquivos, avisos e orçamento. Sete declarações sem callables; comparabilidade obrigatória e permitida antes de qualquer análise, inclusive solo."
  - "Lotes são executados sequencialmente, preservando partes, assinaturas e IDs no histórico do SDK. Respostas bloqueadas, truncadas, parciais e ambíguas são rejeitadas antes de executar ferramentas."
  - "Registry declara o schema concreto de retorno de cada ferramenta; recorder revalida todo o resultado antes de registrar sucesso e devolver fatos ao Gemini. Falhas de cálculo ou validação encerram o loop com evidências parciais."
  - "Orçamento efetivo é min(8, GEMINI_MAX_TOOL_CALLS), incluindo comparabilidade. Ao atingir o limite, retorna tool_limit sem geração adicional de planejamento; a síntese recebe todas as evidências. Cliente próprio é fechado; cliente injetado pertence ao chamador."
  - "synthesize_report inicia conversa nova com evidências/avisos, required_limitations locais e instruções estáticas, sem ferramentas, pergunta, trace ou texto livre do planejamento. MIME JSON e response_json_schema derivado de InvestigationReport."
  - "O texto JSON recebido é validado localmente com Pydantic, sem confiar no response.parsed do SDK. Respostas inválidas geram SynthesisError seguro; synthesize_report valida uma resposta e a função integrada controla o reparo único."
  - "run_investigation_draft integra as fases com cliente e orçamento compartilhados. Retorna InvestigationDraft interno com planning, report opcional e error opcional; falha da síntese preserva evidências/trace. Comparabilidade inválida ou falha no planejamento impede síntese."
  - "Após Pydantic, a W3.10 confere referências, fatos numéricos, sinal/unidade e limitações obrigatórias; a W3.11 confere linguagem causal. run_investigation_draft mantém retorno interno; run_investigation monta o envelope completed da API. Uso isolado de synthesize_report tem orçamento próprio."
  - "report_validation.py concentra regras de relatório, reexportadas por validators.py. Catálogo explícito dos campos numéricos das sete ferramentas; não usa IDs, versões, notas, avisos ou booleanos como valores de suporte."
  - "Números usam evidências citadas no trecho, com qualificadores de alvo/referência/diferença, métrica/estatística e data/amostra. Visão geral exige citações na frase numérica. Unidades dimensionais explícitas; % difere de pontos percentuais."
  - "Arredondamento por Decimal/ROUND_HALF_UP à precisão escrita, sem tolerância percentual global; sinal preservado, contagens exatas e valor não nulo não pode virar zero. Quantidades por extenso nos padrões reconhecidos são rejeitadas. Formatos preferidos estão no prompt e README."
  - "required_limitations é calculado antes da síntese; report deve preservar rule_id único e explicação fornecida, normalizando apenas espaços. Regras cobrem observação/produtividade, condição inicial, cobertura, qualidade e limites do solo."
  - "Falha de validação produz SynthesisError/invalid_report_evidence e validation_issues com code/location/message seguros. A função integrada tenta o reparo; falha final preserva planning e deixa report vazio."
  - "validate_report_language em language_validation.py, reexportado por validators.py, inspeciona todos os campos narrativos; reconhece os cinco termos do SPEC, flexões e expressões causais selecionadas."
  - "Ressalvas de impossibilidade de concluir valem apenas na oração reconhecida. Frases novas, adversativas e novas afirmações coordenadas encerram o escopo; negação genérica, dupla negação e citação de uma afirmação inteira não liberam causalidade."
  - "Exceções explícitas distinguem transporte literal, responsabilidades administrativas, garantias de processamento e menções de termos entre aspas. Normaliza caixa, acentos, espaços e caracteres invisíveis, sem transformar IDs de evidência em afirmações."
  - "Falha de linguagem produz invalid_report_language com validation_issues causal_language, localização e família lexical segura; pode iniciar o reparo único na função integrada."
  - "W3.12: erros invalid_report, invalid_report_evidence e invalid_report_language iniciam uma única nova síntese. Contexto contém errors/schema/facts, com evidências, avisos e limitações obrigatórias; sem relatório rejeitado, pergunta, histórico ou trace."
  - "Erros Pydantic são projetados em mensagens locais e caminhos de campos conhecidos; valores e nomes de campos extras não são copiados. ReportValidationIssue foi movido para schemas.py e continua importável por report_validation.py."
  - "Reparo não disponibiliza nem executa ferramentas e passa novamente por Pydantic, evidências/números/limitações e linguagem. Falhas do provedor ou protocolo não iniciam reparo; segunda falha encerra com erro final, sem terceiro relatório."
  - "trace.repair opcional registra tentativa 1, início UTC, duração monotônica, status, motivo/questões iniciais e erro/questões finais. Não guarda prompts ou texto bruto; trace.calls mantém apenas ferramentas. Falta de prazo ao iniciar a tentativa é registrada sem nova requisição."
  - "W3.13: build_fallback_report(evidence, warnings, reason=...) em fallback.py não importa cliente ou configuração e não executa ferramentas. Consome os mesmos fatos, sem modificar evidências/trace, e retorna FallbackResult interno com report, generated_by fixo deterministic_fallback e avisos."
  - "Comparabilidade permitida é obrigatória. IDs duplicados, mistura de pares/períodos e fatos inválidos são rejeitados; análises parciais produzem limitação explícita. Sem evidência de comparabilidade, o chamador deve coletá-la antes de pedir fallback."
  - "Ordem de apresentação local: comparabilidade, diferença inicial, resumos/contraste de solo, NDVI, condição inicial restante, aplicações (CALAGEM primeiro), população. Desempate por evidence_id; métricas de solo por nome. Ordem não expressa causalidade ou ranking estatístico."
  - "Força do fallback sempre weak, por escolha conservadora. Templates mantêm números, sinais e unidades, formatando até seis casas (duas para operações/população) sem converter valores pequenos em zero. Recomendações citam apenas evidências disponíveis e orientam conferência/documentação."
  - "Templates passam por Pydantic, validação de evidências e linguagem. Reescrita a limitação soil_group_meaning para retirar falso positivo causal de repetição comprovada, sem mudar significado. Aviso deterministic_fallback é operacional e não dispara limitação de qualidade por si só."
  - "Motivo de fallback usa mensagens locais, incluindo missing_api_key do cliente; códigos desconhecidos recebem aviso genérico. Erros não são atribuídos ao modelo como autoria. W3.14 integra ativação automática e envelope HTTP."
  - "run_investigation valida o escopo e executa validate_comparison antes de criar o cliente, registrando a chamada. Reutiliza recorder/evidência/prazo no loop, enviando precomputed_evidence como dados, sem fabricar histórico de chamadas do modelo. Repetição da comparação é rejeitada."
  - "Sem chave, plano local escolhe análises disponíveis: solo por conjunto, contraste, NDVI, condição inicial, operação comum (CALAGEM primeiro) e população. Limite min(8, GEMINI_MAX_TOOL_CALLS) inclui comparabilidade. Não cria cliente ou faz rede."
  - "Falhas de provedor/protocolo e segundo relatório inválido acionam fallback sobre as evidências já obtidas, preservando trace.repair. Falha imediata pode produzir relatório parcial só com comparabilidade. Erros de cálculo/chamada inválida interrompem, sem completar fatos pelo modelo ou fallback."
  - "Prazo começa antes da comparabilidade; após expirar só formatação/validação local do fallback pode finalizar. Nenhuma ferramenta ou geração adicional é iniciada. Cálculos síncronos em andamento não são interrompidos."
  - "Envelope inclui origem backend, evidências e projeção dos gráficos sem recálculo: NDVI opcional, resumos e contrastes de solo em listas. Avisos do pacote e das análises são acumulados, com aviso explícito quando há fallback."
  - "POST /api/investigations retorna 200 para relatório válido; 404 para dataset ausente; 422 para requisição/par inválido; 503 para falha sem relatório válido. Erros de execução usam detail.code/message locais e não retornam stack trace, prompts ou entradas privadas."
problemas_conhecidos:
  - "A investigação real e o diagnóstico de conexão foram aprovados em 2026-10-17. Resultados de novas gerações podem variar; uma resposta inválida continua sujeita a reparo e fallback."
  - "O ambiente restrito bloqueia o socket interno do asyncio/TestClient e a revisão automática da execução ampliada atingiu limite de uso nesta sessão. A validação HTTP da W3.14 foi concluída pelo usuário. Em 2026-10-17 a execução ampliada foi autorizada e a suíte completa com HTTP passou novamente; não há pendência de testes."
  - "As regras de relatório são conservadoras e limitadas a formatos/vocabulário explícitos. Não provam suporte semântico de prosa arbitrária; podem rejeitar construções ambíguas e não cobrem todas as relações qualitativas/sinônimos. O prompt orienta frases simples."
  - "A validação causal é lexical, com escopo local limitado; não é parser completo de português. Não cobre todos os sinônimos, metáforas, idiomas ou negações complexas. O cenário real da W3.15 foi inspecionado."
  - "As primeiras respostas reais foram rejeitadas pelos validadores; os ajustes de prompt e referências verificadas permitiram concluir o cenário. O prazo local é 120 s; o padrão de 45 s pode expirar durante o reparo."
  - "Prazo compartilhado é verificado entre etapas síncronas e limita timeout HTTP restante; não interrompe cálculos locais em andamento nem constitui cancelamento absoluto de processo."
  - "Nove testes reais dependem de FARMLAB_REAL_DATA_DIR, não disponível neste ambiente."
  - "Avisos de depreciação de Starlette/httpx, AnyIO e tipagem interna do SDK no Python 3.14."
  - "Correções UTF-8 em test_analytics.py e test_real_baseline.py feitas na preparação do Windows permanecem no working tree."
arquivos_importantes_alterados:
  - "backend/app/harness/gemini_client.py"
  - "backend/tests/test_gemini_client.py"
  - "backend/app/api/gemini.py e backend/app/main.py"
  - "backend/tests/test_gemini_api.py"
  - "backend/app/harness/schemas.py, evidence_schema.py e backend/app/analytics/contracts.py"
  - "backend/tests/test_harness_schemas.py"
  - "backend/app/harness/prompts.py"
  - "backend/tests/test_synthesis.py e backend/tests/test_health.py"
  - "backend/app/harness/registry.py e backend/tests/test_gemini_tools.py"
  - "backend/app/harness/validators.py e backend/tests/test_call_validators.py"
  - "backend/app/harness/trace.py e backend/tests/test_investigation_trace.py"
  - "backend/app/harness/orchestrator.py e backend/tests/test_orchestrator.py"
  - "backend/tests/test_synthesis.py"
  - "backend/app/harness/report_validation.py e backend/tests/test_report_validation.py"
  - "backend/app/harness/language_validation.py e backend/tests/test_language_validation.py"
  - "backend/tests/test_report_repair.py"
  - "backend/app/harness/fallback.py e backend/tests/test_fallback.py"
  - "backend/app/api/investigations.py, backend/tests/test_investigations.py e backend/tests/test_investigations_api.py"
  - "backend/app/harness/smoke.py, backend/tests/test_gemini_smoke.py e .gitignore"
  - "backend/pyproject.toml e backend/uv.lock"
  - "README.md, PLANEJAMENTO_CODEX.md e HANDOFF.md"
primeiro_passo_da_semana_seguinte: "W3.01–W3.15 concluídas. Para a pessoa responsável por W4: ler o contrato de POST /api/investigations e iniciar W4.01 quando solicitado. Nenhuma tarefa W4 foi implementada."
```

### Registro — Semana 4

```yaml
responsavel:
branch:
commit_entregue:
data:
status: nao_iniciada
tarefas_concluidas: []
tarefas_pendentes: []
comandos_para_executar: []
testes_executados: []
resultado_dos_testes:
decisoes_tomadas: []
problemas_conhecidos: []
arquivos_importantes_alterados: []
versao_da_apresentacao:
```

## 12. Decisões pendentes

Registrar aqui somente decisões que precisam do grupo.

| ID | Data | Proposta | Motivo | Semanas afetadas | Decisão |
| --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — |

## 13. Problemas transversais

Problemas que afetam mais de uma semana devem ser registrados aqui.

| ID | Detectado na semana | Descrição | Impacto | Responsável | Estado |
| --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — |

## 14. Prompt inicial para a Semana 1

```text
Você está assumindo a Semana 1 do projeto FarmLab Investigator.

Antes de alterar qualquer arquivo, leia integralmente SPEC.md, PROJETO.md, PIPELINES.md, PLANEJAMENTO_CODEX.md e HANDOFF.md. Em seguida, inspecione o repositório e confirme o estado atual, sem presumir que a implementação já existe.

Sua atribuição é executar somente as tarefas W1.01 até W1.16, na ordem definida em PLANEJAMENTO_CODEX.md. Trabalhe uma tarefa por vez, mas continue automaticamente dentro da Semana 1 após concluir e verificar cada tarefa. Não inicie nenhuma tarefa W2.*.

Regras obrigatórias:
- frontend Vanilla com HTML, CSS e JavaScript, usando Vite apenas para desenvolvimento e build;
- backend Python com FastAPI;
- nenhum Streamlit, framework de frontend ou banco de dados;
- não implementar ainda as fórmulas analíticas da Semana 2;
- não integrar ainda a API do Gemini ou o harness da Semana 3;
- não versionar .env, GEMINI_API_KEY ou CSVs privados;
- não alterar contratos do SPEC.md sem parar e explicar o conflito;
- usar fixtures pequenas nos testes sempre que possível;
- executar as verificações de cada tarefa antes de avançar.

Depois de cada tarefa, atualize o checkbox e o Diário de execução em PLANEJAMENTO_CODEX.md. Se houver um bloqueio real, pare, explique o problema e diga qual informação é necessária. Se não houver bloqueio, continue até W1.16.

Ao terminar a Semana 1:
1. execute todos os testes da semana;
2. repita o fluxo de importação manual;
3. preencha o Registro — Semana 1 em HANDOFF.md;
4. liste arquivos alterados, comandos de execução, testes, decisões e pendências;
5. pare antes de qualquer tarefa da Semana 2.
```

## 14.1 Prompt inicial para o reajuste pós-Semana 1

```text
Você está assumindo o reajuste pós-Semana 1 do FarmLab Investigator. A Semana 1 já foi concluída e seu histórico não deve ser apagado nem reaberto.

Leia integralmente SPEC.md, PROJETO.md, PIPELINES.md, PLANEJAMENTO_CODEX.md e HANDOFF.md. Inspecione o código e execute primeiro os testes registrados na entrega da Semana 1.

Implemente somente R1.01 até R1.06, na ordem, sem iniciar W2.*. O objetivo é tornar soil_analysis.csv o sétimo arquivo obrigatório, normalizá-lo como contexto geral do dataset e aplicar a identidade visual marrom com #895129 como cor principal.

Regras obrigatórias:
- não atribua amostras de solo a talhões, pois não existe chave ou coordenada para isso;
- trate colunas sem sufixo como Conjunto 1 e colunas _2 como Conjunto 2; não presuma profundidade;
- não classifique nutrientes ou atributos como baixos, adequados ou altos sem unidades e referência documentadas;
- não torne agricultural_inputs.csv obrigatório neste reajuste;
- preserve o comportamento e os testes das seis fontes já implementadas;
- mantenha frontend Vanilla, FastAPI, dados em memória e chave Gemini somente no backend;
- atualize checkboxes, Diário de execução, README e o Registro — Reajuste pós-Semana 1.

Ao terminar, execute Pytest, Vitest, build Vite e a importação manual dos sete arquivos. Confirme a leitura das oito amostras do arquivo atual, registre branch/commit e pare antes de W2.01.
```

## 15. Prompt para receber uma semana já iniciada

```text
Leia SPEC.md, PROJETO.md, PIPELINES.md, PLANEJAMENTO_CODEX.md e HANDOFF.md. Verifique o registro e o gate da semana anterior, confira a revisão atual do Git e execute os testes informados no handoff antes de alterar código. Se o handoff não puder ser reproduzido, pare e relate a divergência. Caso esteja válido, execute somente as tarefas da semana que me foi atribuída, em ordem, atualizando checklist, Diário de execução e o registro de handoff correspondente. Não avance para a semana seguinte.
```

## 16. Prompt para gerar a entrega da semana

```text
Finalize o handoff da semana atual. Não implemente novas funcionalidades. Execute os testes e o cenário manual do gate, atualize os checkboxes e o Diário de execução, preencha todos os campos do registro da semana em HANDOFF.md e produza um resumo com: branch, commit, tarefas concluídas, tarefas pendentes, comandos, testes, decisões, problemas conhecidos e primeiro passo da próxima semana. Se algum gate falhar, marque a semana como bloqueada em vez de pronta.
```
