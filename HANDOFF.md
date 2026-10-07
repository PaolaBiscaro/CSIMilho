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

- [ ] Grão × Grão é permitido.
- [ ] Silagem × Silagem é permitido.
- [ ] Grão × Silagem é bloqueado.
- [ ] NDVI usa somente datas pareadas.
- [ ] Condição inicial usa corte anterior ao plantio.
- [ ] População é ponderada pela área.
- [ ] Conformidade é ponderada pela área e pode ultrapassar 100%.
- [ ] O resumo do solo calcula estatísticas descritivas sobre valores válidos.
- [ ] A comparação de solo é pareada por `AMOSTRA` e usa Conjunto 2 menos Conjunto 1.
- [ ] Nenhuma evidência de solo atribui amostra a talhão ou presume profundidade.
- [ ] Os contratos visuais do solo carregam valores, unidade, contagem, fonte e limitações sem misturar métricas incompatíveis.
- [ ] Cada ferramenta retorna uma evidência conforme o schema.
- [ ] O registry rejeita ferramentas desconhecidas.
- [ ] O baseline do pacote real foi conferido.

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

- [ ] A aplicação inicia sem chave.
- [ ] O teste do Gemini funciona com chave válida.
- [ ] O Gemini só pode chamar ferramentas do registry.
- [ ] IDs fora do dataset são bloqueados.
- [ ] O limite de chamadas é respeitado.
- [ ] Número inventado é rejeitado.
- [ ] Evidência inexistente é rejeitada.
- [ ] Linguagem causal é rejeitada.
- [ ] Uma falha após reparo aciona o fallback.
- [ ] A resposta da investigação segue o schema do `SPEC.md`.

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
primeiro_passo_da_semana_seguinte:
```

### Registro — Semana 3

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
primeiro_passo_da_semana_seguinte:
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
