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
| Pessoa 2 | Semana 2 | `W2.01` a `W2.12` | Ferramentas analíticas determinísticas funcionando |
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

## 8. Handoff da Semana 2 para a Semana 3

### A Semana 2 deve entregar

- schema comum de evidência;
- `validate_comparison`;
- `compare_ndvi`;
- `check_initial_condition`;
- `compare_population`;
- `application_compliance`;
- registry fechado das ferramentas;
- testes unitários das fórmulas;
- teste de regressão com o pacote da apresentação;
- tela de comparação e componente do gráfico.

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
- [ ] Cada ferramenta retorna uma evidência conforme o schema.
- [ ] O registry rejeita ferramentas desconhecidas.
- [ ] O baseline do pacote real foi conferido.

### O que a Semana 3 precisa encontrar

Cada ferramenta deve poder ser chamada desta forma lógica:

```text
tool(dataset_id, target_field_id, reference_field_id, period, ...)
→ evidence
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
primeiro_passo_da_semana_seguinte: "Iniciar W2.01 consumindo somente os objetos normalizados do store; não reler os CSVs nem refazer a atribuição espacial."
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

## 15. Prompt para receber uma semana já iniciada

```text
Leia SPEC.md, PROJETO.md, PIPELINES.md, PLANEJAMENTO_CODEX.md e HANDOFF.md. Verifique o registro e o gate da semana anterior, confira a revisão atual do Git e execute os testes informados no handoff antes de alterar código. Se o handoff não puder ser reproduzido, pare e relate a divergência. Caso esteja válido, execute somente as tarefas da semana que me foi atribuída, em ordem, atualizando checklist, Diário de execução e o registro de handoff correspondente. Não avance para a semana seguinte.
```

## 16. Prompt para gerar a entrega da semana

```text
Finalize o handoff da semana atual. Não implemente novas funcionalidades. Execute os testes e o cenário manual do gate, atualize os checkboxes e o Diário de execução, preencha todos os campos do registro da semana em HANDOFF.md e produza um resumo com: branch, commit, tarefas concluídas, tarefas pendentes, comandos, testes, decisões, problemas conhecidos e primeiro passo da próxima semana. Se algum gate falhar, marque a semana como bloqueada em vez de pronta.
```
