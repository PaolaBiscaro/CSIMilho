# Planejamento de desenvolvimento para o Codex

## 1. Como usar este arquivo

Este é o backlog executável do FarmLab Investigator. O Codex deve trabalhar **uma tarefa por vez**, na ordem apresentada, salvo quando uma tarefa declarar dependência diferente.

### Instruções permanentes para o Codex

Antes de implementar:

1. leia `PROJETO.md`, `SPEC.md`, `PIPELINES.md` e este arquivo;
2. inspecione o estado atual do repositório;
3. identifique a primeira tarefa não concluída cujas dependências estejam prontas;
4. descreva em uma frase o que será alterado;
5. implemente somente essa tarefa.

Depois de implementar:

1. execute os testes e verificações indicados;
2. corrija problemas relacionados à tarefa;
3. marque a tarefa como concluída neste arquivo;
4. registre uma nota curta em **Diário de execução**;
5. informe arquivos alterados, testes executados e qualquer limitação;
6. pare e aguarde a próxima solicitação.

### Regras de escopo

- não adicionar Streamlit;
- não trocar o frontend por um framework;
- não adicionar banco de dados;
- não expor a chave do Gemini ao navegador;
- não enviar CSV bruto ao Gemini;
- não fazer o Gemini calcular métricas;
- não criar ferramentas além das definidas no `SPEC.md`;
- não usar valores hardcoded do protótipo como resultado real;
- não ampliar o escopo sem registrar a decisão;
- manter commits e alterações pequenos e relacionados à tarefa atual.

### Prioridades

- **P0:** indispensável para a apresentação;
- **P1:** necessário para qualidade e segurança do MVP;
- **P2:** melhoria, pode ser cortada se o prazo ficar crítico.

## 2. Resultado esperado ao final

O fluxo completo deve ser:

```text
abrir aplicação
→ importar sete CSVs
→ validar e reconhecer talhões
→ escolher comparação e pergunta
→ executar harness com Gemini e ferramentas Python
→ mostrar visão geral escrita, evidências, gráfico e limitações
→ baixar relatório HTML
```

## 3. Semana 1 — Fundação, contratos e importação

### W1.01 — Criar a estrutura do repositório `[P0]`

- [x] Criar as pastas de frontend e backend definidas no `SPEC.md`.
- [x] Copiar os quatro documentos de orientação para a raiz.
- [x] Criar `README.md` mínimo com pré-requisitos e comandos ainda pendentes.
- [x] Criar `.gitignore` para `.env`, ambientes virtuais, `node_modules`, builds, caches e dados locais.

**Verificar:** árvore do projeto corresponde à especificação e nenhum dado CSV foi adicionado por engano.

### W1.02 — Inicializar o backend `[P0]`

- [x] Criar `backend/pyproject.toml` com dependências mínimas.
- [x] Criar aplicação FastAPI vazia e rota `GET /api/health`.
- [x] Adicionar comando documentado para iniciar Uvicorn.

**Verificar:** servidor inicia e `/api/health` retorna HTTP 200.

### W1.03 — Implementar configuração e ambiente `[P0]`

- [x] Criar `config.py` com Pydantic Settings ou solução equivalente.
- [x] Criar `.env.example` sem segredo.
- [x] Expor no health check apenas configuração segura.

**Verificar:** aplicação inicia com e sem `GEMINI_API_KEY`; a chave nunca aparece na resposta ou nos logs.

### W1.04 — Inicializar o frontend Vanilla `[P0]`

- [x] Criar projeto Vite Vanilla JavaScript dentro de `frontend/`.
- [x] Remover conteúdo demonstrativo padrão.
- [x] Criar `main.js`, `api.js`, `state.js` e arquivos CSS base.

**Verificar:** `npm run dev` abre uma página vazia sem erro no console.

### W1.05 — Definir tokens e layout base `[P1]`

- [x] Migrar cores, tipografia, espaçamento, cards e navegação do protótipo visual.
- [x] Criar layout responsivo com barra lateral em desktop e cabeçalho em telas menores.
- [x] Remover qualquer referência ao Streamlit.

**Verificar:** layout funciona em aproximadamente 1440 px, 820 px e 390 px.

### W1.06 — Criar os schemas de dados normalizados `[P0]`

- [x] Implementar modelos Pydantic para arquivo, talhão, aviso, erro, par e resposta de validação.
- [x] Proibir campos extras nos contratos críticos.
- [x] Adicionar exemplos mínimos nos testes.

**Verificar:** schemas aceitam objetos válidos e rejeitam tipos e campos incorretos.

### W1.07 — Implementar leitura segura de CSV `[P0]`

- [x] Criar loader com detecção de vírgula ou ponto e vírgula.
- [x] Tentar `utf-8-sig` e fallback `latin-1` com aviso.
- [x] Impor lista de nomes permitidos e limite de tamanho.
- [x] Não converter valores inválidos em zero.

**Verificar:** testes com os dois delimitadores, encoding alternativo e arquivo ilegível.

### W1.08 — Validar `fields.csv` `[P0]`

- [x] Validar colunas mínimas.
- [x] Normalizar IDs para string.
- [x] Ler centroide JSON.
- [x] Validar `fieldGeom` como `POLYGON` ou `MULTIPOLYGON` WKT.
- [x] Derivar `label`, `purpose` e `management` pelas regras da especificação.
- [x] Corrigir o alias conhecido `Convecional` somente para classificação, preservando o nome original e emitindo aviso.

**Verificar:** os quatro talhões da demonstração são reconhecidos com classificação correta.

### W1.09 — Validar ordens e relações com talhões `[P0]`

- [x] Validar as colunas mínimas de `service_orders.csv` e `service_orders_fields.csv`.
- [x] Canonicalizar `serviceOrderNumber` e criar o mapa número → ID.
- [x] Criar o mapa um-para-muitos de ordem de serviço → talhões candidatos.
- [x] Aceitar ordens compartilhadas e bloquear número de ordem ligado a IDs diferentes.

**Verificar:** `1`, `1.0` e espaços externos resolvem a mesma ordem; vínculos compartilhados são válidos e conflito de número gera erro impeditivo.

### W1.10 — Validar mapas de plantio e fertilização `[P0]`

- [x] Implementar normalização do mapa de plantio.
- [x] Implementar normalização do mapa de fertilização.
- [x] Converter datas e números com relatório de linhas descartadas.
- [x] Resolver `Service Order` como número e limitar a busca aos talhões candidatos.
- [x] Ligar cada linha por `representative_point()` ou interseção única de pelo menos 50%.
- [x] Contabilizar linhas atribuídas, não atribuídas, com geometria inválida e ambíguas.

**Verificar:** nenhuma linha inválida entra silenciosamente nos cálculos.

### W1.11 — Validar e normalizar NDVI `[P0]`

- [x] Validar colunas mínimas.
- [x] Extrair data do `filename`.
- [x] descartar observações sem pixels válidos ou sem média.
- [x] validar intervalo `[-1, 1]`.

**Verificar:** datas e NDVI válidos são preservados; ausências continuam ausentes.

### W1.12 — Ligar `season_id` ao talhão `[P0]`

- [x] Implementar conversão EPSG:3857 para longitude e latitude.
- [x] Implementar distância de Haversine.
- [x] Ligar cada série ao centroide mais próximo dentro do limite.
- [x] Registrar distância e impedir ligações ambíguas.

**Verificar:** todas as séries da demonstração são ligadas ao talhão correto com teste de regressão.

### W1.13 — Criar store temporário da sessão `[P0]`

- [x] Criar armazenamento em memória por `dataset_id` UUID.
- [x] Guardar DataFrames normalizados e metadados, nunca caminhos fornecidos pelo usuário.
- [x] Permitir substituir o pacote na mesma execução.

**Verificar:** dataset recuperado pelo ID mantém os objetos corretos e ID inexistente retorna erro controlado.

### W1.14 — Implementar `POST /api/datasets` `[P0]`

- [x] Receber os seis arquivos como multipart.
- [x] Executar loaders, normalizadores e ligações.
- [x] Criar erros, avisos, qualidade, talhões e pares válidos.
- [x] Persistir somente o estado temporário.

**Verificar:** pacote completo retorna `201`; pacote incompleto retorna `422`; excesso de tamanho retorna `413`.

### W1.15 — Construir a tela de importação `[P0]`

- [x] Criar seletor múltiplo de arquivos.
- [x] Mostrar status por arquivo.
- [x] Enviar multipart usando `api.js`.
- [x] Mostrar erros e avisos retornados.
- [x] Habilitar **Continuar** somente em estado pronto.

**Verificar:** importar os arquivos reais pelo navegador funciona sem recarregar a página.

### W1.16 — Teste integrado da Semana 1 `[P0]`

- [x] Executar toda a suíte criada.
- [x] Testar o pacote da apresentação manualmente.
- [x] Confirmar os quatro talhões e os pares permitidos.
- [x] Atualizar o README com comandos reais.

**Saída:** importação e validação completas, ainda sem análises.

## 3.1 Reajuste obrigatório após a Semana 1 — solo e identidade visual

Este bloco foi criado depois da conclusão de `W1.16`. Ele preserva o histórico entregue e deve ser executado antes de qualquer tarefa `W2.*`. Não marcar as tarefas antigas da Semana 1 como pendentes novamente.

### R1.01 — Atualizar o contrato para sete arquivos `[P0]`

- [x] Adicionar `soil_analysis.csv` à lista permitida e obrigatória do loader.
- [x] Atualizar os contratos multipart e a resposta de validação.
- [x] Preservar compatibilidade das seis fontes já implementadas.
- [x] Atualizar mensagens que ainda mencionem seis arquivos.

**Verificar:** seis arquivos retornam erro claro de ausência de `soil_analysis.csv`; o pacote com sete segue para validação.

### R1.02 — Normalizar `soil_analysis.csv` `[P0]`

- [x] Ler BOM, delimitador `;` e vírgula decimal.
- [x] Validar `AMOSTRA` única, textura, pH e valores não negativos conforme o `SPEC.md`.
- [x] Separar colunas sem sufixo como Conjunto 1 e `_2` como Conjunto 2.
- [x] Emitir avisos de textura, nulos, colunas opcionais e segundo conjunto.
- [x] Guardar o resultado no store como `soil_samples`, com `scope: dataset`.

**Verificar:** fixture pequena cobre linha válida, amostra duplicada, número inválido, soma de textura fora da tolerância e ausência de Conjunto 2.

### R1.03 — Integrar solo à API e à importação `[P0]`

- [x] Incluir resumo de disponibilidade do solo na resposta de `POST /api/datasets`.
- [x] Mostrar o sétimo arquivo e seu estado na tela de importação.
- [x] Não criar `field_id`, coordenada, data ou profundidade para as amostras.
- [x] Manter arquivos e dados somente na sessão em memória.

**Verificar:** a interface reconhece os sete arquivos e a API informa a quantidade válida de amostras com escopo geral.

### R1.04 — Aplicar a nova identidade visual `[P0]`

- [x] Substituir os tokens principais de cor pelos valores da seção 4.1 do `SPEC.md`.
- [x] Usar `#895129` na barra lateral, botões principais, item ativo e série principal.
- [x] Usar `#6b3f22` em hover/foco e tons claros nos fundos de destaque.
- [x] Preservar cores semânticas de sucesso, aviso e erro.
- [x] Validar contraste e foco visível.

**Verificar:** revisar 1440 px, 820 px e 390 px; nenhum hexadecimal antigo deve permanecer fora de `tokens.css`, exceto cores semânticas documentadas.

### R1.05 — Revalidar o pacote e os testes `[P0]`

- [x] Atualizar fixtures artificiais para sete arquivos.
- [x] Executar Pytest, Vitest e build Vite.
- [x] Importar o pacote real pelo navegador.
- [x] Confirmar oito amostras válidas no arquivo atual.
- [x] Registrar nova qualidade, avisos e qualquer regressão.

**Verificar:** regressões das seis fontes antigas continuam passando e o novo fluxo funciona de ponta a ponta até **Continuar**.

### R1.06 — Atualizar documentação e handoff `[P1]`

- [x] Atualizar README com sete arquivos e o novo fluxo manual.
- [x] Preencher o Registro — Reajuste pós-Semana 1 em `HANDOFF.md`.
- [x] Registrar branch/commit e comandos reproduzíveis.
- [x] Parar antes de `W2.01`.

**Saída:** fundação existente ampliada para solo e tema marrom, pronta para a pessoa responsável pela Semana 2.

## 3.2 Reajuste visual e prévias navegáveis — antes da Semana 2

Este bloco foi solicitado após `R1.06` e também deve terminar antes de `W2.01`. Ele altera somente documentação e frontend; não cria schemas de evidência, ferramentas analíticas, endpoints de investigação nem integração Gemini.

### R1.07 — Registrar a direção visual e o limite dos mocks `[P0]`

- [x] Atualizar `HANDOFF.md`, `PIPELINES.md`, `PLANEJAMENTO_CODEX.md`, `PROJETO.md`, `README.md` e `SPEC.md` antes de alterar o frontend.
- [x] Manter `#895129` como cor primária obrigatória.
- [x] Registrar o dashboard de cards, cabeçalho horizontal e navegação em pílulas como direção visual.
- [x] Definir que Comparação e Investigação usam mocks locais, identificados e sem chamadas à API de investigação.

**Verificar:** os seis documentos distinguem claramente prévia visual de funcionalidade analítica concluída.

### R1.08 — Construir shell de dashboard e prévias clicáveis `[P0]`

- [x] Reorganizar a aplicação em moldura de dashboard clara, cabeçalho horizontal e cards responsivos.
- [x] Manter a tela de Dados funcional dentro da nova composição.
- [x] Criar prévia clicável de Comparação com selects, período, pergunta e cards mockados.
- [x] Criar prévia clicável de Investigação com abas internas e conteúdo mockado.
- [x] Fazer **Continuar** abrir Comparação e o CTA mockado abrir Investigação.
- [x] Exibir o selo **Prévia · dados demonstrativos** nas duas telas futuras.
- [x] Testar navegação, 1440 px, 820 px, 390 px, Vitest e build Vite.
- [x] Parar antes de `W2.01`.

**Saída:** frontend visualmente próximo às referências, navegável nas três áreas e ainda tecnicamente separado das implementações das Semanas 2 a 4.

## 4. Semana 2 — Ferramentas analíticas determinísticas

### W2.01 — Criar protocolo comum de evidência `[P0]`

- [x] Criar schema base de evidência.
- [x] Padronizar ID, unidade, fontes, método, observações e versão.
- [x] Criar gerador determinístico de IDs dentro da investigação.

**Verificar:** todas as futuras ferramentas conseguem herdar ou compor o contrato.

**Contrato implementado:** `Evidence` em `backend/app/harness/schemas.py` exige `evidence_id`, `unit` (aceita nulo), `source_files`, `method`, `observation_count` (aceita nulo) e `tool_version`; inclui `notes` e campos opcionais de métrica, alvo, referência e diferença. Resultados específicos podem herdar ou compor esse contrato, preservando métricas múltiplas e o escopo geral do solo. `EvidenceIdGenerator` em `backend/app/analytics/evidence.py` deve ser instanciado uma vez por investigação e compartilhado entre suas ferramentas: cada prefixo possui sequência própria a partir de `001`, reproduzível para a mesma ordem de solicitações. Os IDs são locais à investigação; referências entre relatórios precisam também de `investigation_id`.

### W2.02 — Implementar pares e comparabilidade `[P0]`

- [x] Gerar somente pares com mesma finalidade e manejos distintos.
- [x] Implementar os cinco critérios do score.
- [x] Bloquear incompatibilidade de cultura ou finalidade.

**Verificar:** Grão × Grão e Silagem × Silagem são válidos; Grão × Silagem é bloqueado.

### W2.03 — Implementar `compare_ndvi` `[P0]`

- [x] Filtrar alvo, referência e período.
- [x] Parear datas por inner join.
- [x] Calcular médias, gaps e série do gráfico.
- [x] Produzir evidência validada.

**Verificar:** sinal de `target - reference` está correto e datas ausentes não são interpoladas.

### W2.04 — Testar `compare_ndvi` com fixture pequena `[P0]`

- [x] Criar fixture manual com datas pareadas e não pareadas.
- [x] Testar quantidade de pares, média e gap.
- [x] Testar erro quando não há pares suficientes.

**Verificar:** testes independem dos números do protótipo.

### W2.05 — Implementar `check_initial_condition` `[P0]`

- [x] Encontrar a data de corte do plantio.
- [x] Filtrar NDVI pareado anterior ao corte.
- [x] Aplicar mínimo de três pares e limiar de 0,02.
- [x] Marcar regra como heurística operacional.

**Verificar:** casos diferente, semelhante e indisponível têm testes.

### W2.06 — Implementar `compare_population` `[P0]`

- [x] Calcular média ponderada por área.
- [x] Calcular diferença absoluta e percentual.
- [x] Contar linhas válidas e descartadas.
- [x] Produzir evidência.

**Verificar:** teste demonstra que média simples e ponderada produzem resultados diferentes.

### W2.07 — Implementar `application_compliance` `[P0]`

- [x] Agrupar por talhão e operação.
- [x] Ponderar doses pela área.
- [x] Calcular conformidade sem limitar a 100%.
- [x] Priorizar CALAGEM no cenário da demonstração.

**Verificar:** testar subaplicação, aplicação exata, sobreaplicação e dose configurada zero.

### W2.08 — Implementar `summarize_soil_analysis` `[P0]`

- [x] Calcular contagem, média, mediana, mínimo, máximo, Q1 e Q3 por métrica.
- [x] Separar textura, fertilidade/acidez, bases e micronutrientes.
- [x] Expor a unidade como nula quando não documentada.
- [x] Não aplicar classificação agronômica de suficiência.
- [x] Produzir contrato de distribuição por métrica com mínimo, Q1, mediana, Q3, máximo, contagem válida e fonte.
- [x] Produzir contrato de composição de textura somente para amostras cuja soma válida esteja dentro da tolerância.

**Verificar:** testes usam fixture manual e confirmam que nulos não viram zero.

### W2.09 — Implementar `compare_soil_measurement_groups` `[P0]`

- [x] Parear Conjunto 1 e Conjunto 2 por `AMOSTRA`.
- [x] Calcular `Conjunto 2 - Conjunto 1` por amostra e métrica.
- [x] Calcular mediana do delta e quantidade de pares válidos.
- [x] Incluir a limitação sobre o significado desconhecido de `_2`.
- [x] Produzir série pareada própria para barras agrupadas ou pontos conectados, sem misturar unidades.

**Verificar:** o retorno nunca usa os termos profundidade, camada ou horizonte como fato.

### W2.10 — Criar registry local das ferramentas `[P0]`

- [x] Registrar nome, descrição, schema de parâmetros e função Python.
- [x] Expor somente as sete ferramentas previstas.
- [x] Adicionar versão por ferramenta.

**Verificar:** lookup aceita nomes permitidos e rejeita qualquer outro.

### W2.11 — Criar endpoint temporário de diagnóstico `[P1]`

- [x] Criar endpoint disponível apenas em desenvolvimento para executar ferramentas sem Gemini.
- [x] Não aceitar caminho de arquivo nem DataFrame no corpo.
- [x] Desabilitar no modo de apresentação ou produção.

**Verificar:** cada ferramenta pode ser testada pelo dataset e IDs selecionados.

### W2.12 — Construir a tela de comparação `[P0]`

- [x] Preencher selects com pares retornados pelo backend.
- [x] Atualizar pergunta padrão ao trocar os talhões.
- [x] Mostrar comparabilidade e análises disponíveis.
- [x] Bloquear botão quando o par não for permitido.

**Verificar:** a tela nunca permite Grão × Silagem como comparação executável.

### W2.13 — Construir componentes dos gráficos analíticos `[P0]`

- [x] Criar gráfico Chart.js a partir do contrato de série.
- [x] Mostrar alvo e referência de NDVI com legenda e tooltip.
- [x] Criar componentes reutilizáveis para distribuição, comparação pareada e composição de textura do solo.
- [x] Incluir seletor de família/métrica, unidade, contagem, fonte, estado vazio e alternativa tabular acessível.
- [x] Impedir mapa ou linha temporal de solo enquanto não existirem coordenadas ou datas.
- [x] Destruir instância anterior ao renderizar outra análise.

**Verificar:** os gráficos funcionam com fixtures, reproduzem exatamente as evidências, não misturam unidades e não duplicam canvas após nova seleção.

### W2.14 — Validar o baseline do pacote real `[P0]`

**Retomada e concluída em 2026-10-13 por solicitação do usuário**, com os sete CSVs de `/Users/lucashygidio/Downloads/FarmLab/`. Auditoria, diferenças históricas e reprodução em [BASELINE_W2.md](BASELINE_W2.md).

- [x] Executar as seis análises nos dados da apresentação.
- [x] Confirmar oito amostras de solo válidas no escopo geral.
- [x] Comparar com os valores aproximados da especificação.
- [x] Investigar qualquer diferença antes de alterar tolerâncias.
- [x] Criar teste de regressão com resultados confirmados.

**Saída:** ferramentas produzem fatos corretos sem Gemini.

## 5. Semana 3 — Gemini e harness controlado

### W3.01 — Integrar o SDK oficial do Gemini `[P0]`

- [x] Instalar `google-genai` no backend.
- [x] Criar cliente a partir de `GEMINI_API_KEY`.
- [x] Usar `GEMINI_MODEL` configurável.
- [x] Implementar timeout e tradução de erros comuns.

**Verificar:** módulo pode ser importado sem chave e só cria cliente quando necessário.

**Entrega de 2026-10-15:** `backend/app/harness/gemini_client.py` usa o SDK oficial sob demanda, com modelo configurável, timeout HTTP em milissegundos, encerramento por contexto e erros seguros em português. Chamadas automáticas de ferramentas e retries internos do SDK ficam desativados; o orchestrator futuro controlará o prazo total, a repetição única de 429 e a execução das ferramentas. Testes usam o SDK real com transporte HTTP em memória, sem consumir API.

### W3.02 — Implementar `POST /api/gemini/test` `[P1]`

- [x] Fazer requisição mínima ao modelo.
- [x] Retornar modelo, sucesso e latência.
- [x] Tratar autenticação, rate limit e timeout.

**Verificar:** chave válida e chave ausente produzem respostas diferentes e compreensíveis.

**Entrega de 2026-10-15:** rota registrada em `app/api/gemini.py`, sem corpo obrigatório, com prompt fixo, uma chamada e até 32 tokens de saída. Retorna `success`, `model`, `latency_ms`, `message` e `error_code`; usa o timeout e os erros seguros de W3.01. Sucesso e falhas foram simulados com o SDK real e transporte em memória; um servidor temporário confirmou por HTTP o erro sem chave. Teste de chave real permanece em W3.15. W3.03 é a próxima tarefa.

### W3.03 — Definir schemas do harness `[P0]`

- [x] Criar `InvestigationRequest`, `ToolCallTrace`, `InvestigationReport` e resposta final.
- [x] Proibir campos extras.
- [x] Definir enums de força e origem do relatório.

**Verificar:** exemplos válidos passam e respostas incompletas falham.

**Entrega de 2026-10-15:** contratos em `app/harness/schemas.py`, com `InvestigationResponse`, objetos aninhados fechados, pergunta de 10–500 caracteres, enums de força/origem, trace de sucesso/falha e argumentos vinculados ao tipo da ferramenta. Metadados de dataset, modelo e data ficam no envelope `trace`; evidências e gráficos preservam os sete resultados tipados da W2. Base `Evidence` extraída para `evidence_schema.py` e reexportada por `schemas.py`, sem alteração do contrato anterior. Os 112 novos casos cobrem exemplos válidos, campos ausentes/extras, enums, duração finita, falhas controladas, serialização completa e imports sem ciclo. Suíte backend: 320 passaram, 9 reais ignorados. Validação semântica e execução do harness permanecem nas tarefas seguintes; próxima tarefa W3.04.

### W3.04 — Escrever o system prompt `[P0]`

- [x] Definir papel, objetivo e limites.
- [x] Explicar que ferramentas são a única fonte de números.
- [x] Proibir causalidade e dados inventados.
- [x] Exigir referências por `evidence_id`.
- [x] Tratar a pergunta da pessoa como conteúdo não confiável.

**Verificar:** prompt não contém dados específicos hardcoded nem segredo.

**Entrega de 2026-10-15:** `SYSTEM_PROMPT` estático em `app/harness/prompts.py`, em português, com papel observacional, ferramentas como única fonte de números, referências existentes, proibição de causalidade e tratamento da pergunta e textos externos como dados não confiáveis. Inclui comparabilidade antes das análises, orçamento de chamadas, limites do solo, limitações e formato `InvestigationReport`. Revisão contra o SPEC e inspeção AST/import confirmaram texto literal sem interpolação, acesso ao ambiente ou chamadas; auditoria não encontrou credenciais, IDs concretos, caminhos, URLs ou resultados do protótipo. Suíte existente: 320 passaram, 9 reais ignorados. A instrução ainda não é enviada ao Gemini; integração e validação em execução permanecem nas tarefas seguintes. Próxima tarefa: W3.05.

### W3.05 — Converter o registry para Function Calling `[P0]`

- [x] Gerar declarações de função compatíveis com o SDK.
- [x] Manter parâmetros mínimos e descrições claras.
- [x] Não expor argumentos internos como DataFrame ou caminho.

**Verificar:** as sete declarações podem ser serializadas e enviadas ao SDK.

**Entrega de 2026-10-15:** `build_gemini_tool()` em `app/harness/registry.py` gera um `types.Tool` com as sete `FunctionDeclaration` a partir de `TOOLS`, usando nome, descrição e `parameters_json_schema` dos modelos Pydantic. Corrigida a contagem antiga de cinco para incluir as duas ferramentas de solo já previstas no SPEC e entregues na W2. Descrições dos parâmetros adicionadas aos contratos, sem alterar campos ou regras. Preservados objetos fechados, período alternativo, referências locais, enumerações, defaults e filtros nulos. Nenhum callable Python, dataset interno, DataFrame, caminho, store ou gerador de IDs é exposto. Os 17 novos testes verificaram declarações e o payload HTTP real do SDK em transporte simulado, além do retorno das chamadas sem execução automática. Suíte completa: 337 passaram, 9 reais ignorados. Próxima tarefa: W3.06; nenhuma chamada ao serviço Gemini real.

### W3.06 — Implementar validador de chamadas `[P0]`

- [x] Conferir allowlist.
- [x] Validar parâmetros com Pydantic.
- [x] Conferir IDs no dataset.
- [x] Impedir troca de alvo e referência.
- [x] Detectar repetição idêntica.

**Verificar:** testes cobrem cada bloqueio.

**Entrega de 2026-10-15:** `ToolCallValidator` em `app/harness/validators.py`, com estado por investigação e cópia da seleção original. Valida nome no registry, objeto de argumentos pelo modelo Pydantic, dataset da sessão, existência dos talhões e preservação de alvo, referência e período. Chamadas aceitas ficam reservadas antes da execução; chamadas rejeitadas não alteram o histórico. Repetições consideram defaults, UUID, espaços, nome canônico de operação e conjunto de métricas de solo. Retorna argumentos tipados normalizados; erros locais usam códigos/mensagens sem ecoar conteúdo não confiável. Os 54 novos casos cobrem os bloqueios, expiração da sessão, isolamento, mutações e execução local das sete ferramentas após validação. Suíte completa: 391 passaram, 9 reais ignorados. Integração no loop, orçamento e comparabilidade continuam na W3.08; próxima tarefa W3.07.

### W3.07 — Implementar trace da investigação `[P0]`

- [x] Registrar sequência, ferramenta, argumentos normalizados, evidências, fontes e duração.
- [x] Não registrar chave, CSV bruto ou prompt completo.
- [x] Criar `trace_id` e `investigation_id`.

**Verificar:** trace de ferramenta bem-sucedida e falha controlada segue o schema.

**Entrega de 2026-10-15:** `InvestigationRecorder` em `app/harness/trace.py` cria UUIDs de investigação/trace e um gerador local de evidências. `run_tool` usa o validador W3.06, executa uma ferramenta local e registra sequência, argumentos normalizados, versão, início UTC, duração monotônica, IDs e fontes. Falhas geram entrada `error` e `ToolExecutionError` com mensagem local, sem exceção bruta; rejeições anteriores à execução não criam entrada. `snapshot()` retorna cópia defensiva aderente a `InvestigationTrace`. O trace não inclui pergunta, configuração do provedor ou resultado completo. Fontes precisam ser nomes dos arquivos esperados; versão inconsistente e ID repetido são rejeitados. Os 26 novos testes incluem as sete ferramentas, falha real, isolamento, privacidade e relógio de parede retrocedendo. Suíte completa: 417 passaram, 9 reais ignorados. Próxima tarefa W3.08; loop Gemini e orçamento ainda não implementados.

### W3.08 — Implementar o loop do orchestrator `[P0]`

- [x] Enviar contexto e ferramentas ao Gemini.
- [x] Receber, validar e executar chamadas.
- [x] Devolver resultados ao modelo.
- [x] Aplicar limite de oito chamadas.
- [x] Exigir `validate_comparison` antes das análises.

**Verificar:** usar um cliente fake para simular duas ferramentas e finalização sem consumir API.

**Entrega de 2026-10-16:** `run_investigation_tools` integra contexto sem CSVs, sete declarações, validador, execução determinística e trace. Exige comparabilidade permitida, executa lotes sequencialmente, revalida retornos pelo schema concreto e preserva IDs/assinaturas no histórico do SDK. Limita a oito chamadas (ou configuração menor), controla prazo entre etapas e timeout HTTP restante, repete 429 uma única vez e encerra em falhas com evidências parciais e erro local. Retorna `ToolLoopResult` interno; texto livre não vira relatório. Cliente próprio é fechado; cliente injetado pertence ao chamador. Verificação: 34 testes novos de loop e nove de timeout; suíte completa com 460 aprovados, 9 reais ignorados e três avisos existentes, sem consumir API. Prazo síncrono não interrompe cálculo local em andamento. Síntese, orçamento compartilhado entre fases, fallback e rota continuam nas próximas tarefas; próximo item W3.09.

### W3.09 — Implementar síntese estruturada `[P0]`

- [x] Enviar somente evidências e regras acumuladas.
- [x] Solicitar JSON aderente ao schema final.
- [x] Validar a resposta com Pydantic.

**Verificar:** resposta fake válida vira `InvestigationReport`.

**Entrega de 2026-10-16:** `synthesize_report` envia uma conversa nova contendo somente evidências e avisos acumulados, com instruções estáticas de síntese, MIME JSON e `response_json_schema` derivado de `InvestigationReport`. Não disponibiliza ferramentas nem reutiliza pergunta, trace ou texto livre do planejamento. Revalida fatos de entrada e exige planejamento concluído/limitado com comparabilidade permitida. Valida o texto JSON recebido com Pydantic, sem confiar em `response.parsed`; erros estruturais, bloqueios, truncamento e chamadas de ferramentas são rejeitados com mensagens locais. `run_investigation_draft` integra as fases com um cliente, prazo e repetição única de 429 compartilhados, preservando evidências/trace quando a síntese falha. Retorna rascunho interno, ainda sem validação semântica, reparo, fallback ou endpoint. Verificação: 43 testes novos passaram; suíte backend com 503 aprovados, 9 reais ignorados e três avisos existentes, sem consumir API. Próxima tarefa: W3.10.

### W3.10 — Validar evidências e números `[P0]`

- [x] Verificar todos os `evidence_ids`.
- [x] Detectar números ausentes dos fatos estruturados.
- [x] Verificar sinal e unidade.
- [x] Exigir limitações obrigatórias.

**Verificar:** testes rejeitam evidência falsa e número inventado.

**Entrega de 2026-10-16:** `report_validation.py`, reexportado por `validators.py`, confere referências estruturadas e no texto, duplicação de IDs, números nas evidências citadas, unidades, sinal, papéis alvo/referência/diferença, estatísticas de solo, contagens e datas/amostras. O catálogo usa campos tipados das sete ferramentas, sem aproveitar números em versões, IDs, notas ou avisos como fatos. Arredondamento decimal respeita a precisão escrita, sem converter valor não nulo em zero; contagens exigem igualdade. Regras locais produzem `required_limitations` antes da síntese; o relatório deve preservar `rule_id` e explicação fornecida. O orchestrator aplica as checagens após Pydantic e retorna `invalid_report_evidence` com `validation_issues` locais, preservando fatos/trace e sem executar reparo. Os 80 testes novos do validador e cinco de integração passaram; suíte completa com 588 aprovados, 9 reais ignorados e três avisos existentes. Validação conservadora de formatos/vocabulário explícitos, não prova semântica de prosa arbitrária. Linguagem causal permanece na W3.11, próximo item.

### W3.11 — Validar linguagem causal `[P0]`

- [x] Detectar termos proibidos em contexto causal.
- [x] Permitir menções explícitas como “não é possível afirmar que causou”.
- [x] Retornar erros de validação claros para reparo.

**Verificar:** conjunto de frases permitidas e proibidas possui testes.

**Entrega de 2026-10-16:** `validate_report_language` em `language_validation.py`, reexportado por `validators.py`, verifica todos os campos narrativos. Regras locais cobrem os cinco termos do SPEC, flexões e algumas expressões equivalentes. Ressalvas explícitas de impossibilidade de concluir são permitidas somente no escopo da oração; pontuação, adversativas e novas afirmações encerram esse escopo. Negação genérica, dupla negação e aspas em torno de uma afirmação não liberam causalidade. Há exceções específicas para transporte literal, responsabilidades administrativas, garantias do processamento e menções metalinguísticas. O orchestrator valida linguagem após evidências, retornando `invalid_report_language` e `validation_issues` com campo/família da expressão, sem texto bruto e preservando fatos/trace. Os 91 testes de linguagem e quatro de integração novos passaram; suíte completa: 683 aprovados, 9 reais ignorados e três avisos existentes. Regras lexicais conservadoras, sem garantia de compreensão de prosa arbitrária. Próximo item W3.12; reparo não iniciado.

### W3.12 — Implementar uma tentativa de reparo `[P1]`

- [x] Enviar ao Gemini somente erros, schema e fatos.
- [x] Não repetir ferramentas no reparo.
- [x] Aceitar apenas uma nova resposta.

**Verificar:** primeiro relatório inválido e segundo válido concluem com trace de reparo.

**Entrega de 2026-10-16:** `run_investigation_draft` executa uma única tentativa após erro de JSON/schema, evidências ou linguagem. A conversa nova contém somente erros locais seguros, schema e fatos já acumulados, incluindo avisos e limitações; não reutiliza o relatório rejeitado ou o histórico. Ferramentas indisponíveis no reparo; a nova resposta passa por todas as validações. Cliente, prazo total e uma repetição de 429 permanecem compartilhados. `trace.repair` registra início, duração, motivo e resultado, preservando `trace.calls` e evidências; segunda falha retorna erro final sem terceira resposta. Falhas do provedor ou protocolo não iniciam reparo. Os 34 testes novos passaram; suíte completa: 717 aprovados, 9 reais ignorados e três avisos existentes, sem API externa ou dependências novas. Fallback e endpoint continuam pendentes. Próximo item: W3.13.

### W3.13 — Implementar fallback determinístico `[P0]`

- [x] Criar visão geral por templates.
- [x] Ordenar achados pelas regras do MVP.
- [x] Adicionar limitações obrigatórias.
- [x] Marcar `generated_by` corretamente.

**Verificar:** fallback funciona sem chave e não menciona Gemini como autor.

**Entrega de 2026-10-16:** `fallback.py` implementa `build_fallback_report` sobre as evidências existentes, sem chave, cliente, rede ou repetição de ferramentas. Retorna relatório validado, origem fixa `deterministic_fallback` e aviso com motivo seguro. Templates cobrem as sete ferramentas, limitações obrigatórias e recomendações vinculadas às evidências. Ordem local documentada: comparabilidade, diferença inicial, solo, NDVI, condição inicial restante, aplicações com CALAGEM primeiro e população; força conservadora `weak`. Comparabilidade ausente/inválida e fatos inconsistentes são rejeitados; cobertura parcial é explicitada. Ajustada a redação da limitação de conjuntos de solo, antes incompatível com o validador causal; aviso operacional não implica qualidade ruim dos dados. Os 45 novos testes passaram; suíte completa: 762 aprovados, 9 reais ignorados e três avisos existentes. Ativação automática, coleta local sem chave e endpoint permanecem na W3.14, próximo item.

### W3.14 — Implementar `POST /api/investigations` `[P0]`

- [x] Validar requisição e recuperar dataset.
- [x] Executar orchestrator.
- [x] Acionar fallback nos casos previstos.
- [x] Retornar relatório, evidências, gráfico, trace e avisos.

**Verificar:** cliente fake do Gemini permite teste completo da API sem rede.

**Entrega de 2026-10-16 — concluída:** `POST /api/investigations` chama `run_investigation` e retorna o envelope completo. Comparabilidade local antecede o provedor e compartilha recorder, limite de ferramentas e prazo com o loop; a evidência já executada é fornecida em `precomputed_evidence`. Sem chave, plano local de até oito chamadas; após falha do provedor ou reparo, fallback reutiliza os fatos sem repetir ferramentas. Erros de cálculo e chamadas inválidas interrompem o fluxo; erros HTTP são controlados. Verificação inicial restrita: 745 aprovados, 9 ignorados. O usuário executou `.\.venv\Scripts\python.exe -m pytest --tb=short` em `backend` e forneceu a saída completa: **827 aprovados, 9 reais ignorados e três avisos existentes em 50,61 s**, incluindo os 41 novos testes de fluxo/rota direta/OpenAPI/SDK simulado e os 24 novos testes HTTP. Essa execução resolveu a pendência de validação causada pelo bloqueio de socket no sandbox e pelo limite da revisão automática. Próximo item: W3.15; não iniciado.

### W3.15 — Teste real controlado do Gemini `[P0]`

- [x] Preparar cenário reproduzível e testes simulados do comando local.
- [x] Configurar chave somente no ambiente local.
- [x] Rodar uma investigação real.
- [x] Inspecionar ferramentas solicitadas e resposta.
- [x] Ajustar descrições ou prompt sem alterar cálculos.

**Saída:** uma investigação completa passa pelo harness e pelo Gemini.

**Concluída em 2026-10-17:** teste real com `gemini-2.5-flash`, chave somente no `.env` ignorado e sete fixtures pequenas. Investigação `c616c852-424a-45cb-91e6-769a46f56717`: `passed=true`, `generated_by=gemini`, oito chamadas bem-sucedidas, evidências correspondentes ao trace, sem reparo ou fallback. Relatório inspecionado: NDVI, população, calagem, solo nos dois conjuntos e contraste, condição inicial indisponível explicitada, força fraca e limitações preservadas. Artefato local: `backend/.local/w3-15/20261017T135442Z-c616c852-424a-45cb-91e6-769a46f56717.json`.

As tentativas iniciais expuseram redação numérica/unidades inválidas e timeout de reparo. O prompt foi ajustado, e o contexto passou a incluir `reference_findings`, textos verificados dos mesmos fatos usando os templates W3.13. O Gemini é orientado a selecionar/ordenar esses achados sem alterar valores e a redigir a visão geral/recomendações. Nenhum cálculo ou validador foi flexibilizado. Prazo local ampliado para 120 s; padrão do projeto permanece 45 s. Teste de health isolado do `.env` real. Suíte completa: **841 passaram, 9 reais ignorados, 3 avisos existentes em 41,40 s**; após o último ajuste textual, **100 testes focados passaram em 12,62 s**. W3.01–W3.15 concluídas; W4 não iniciada.

## 6. Semana 4 — Interface final, relatório e apresentação

### W4.01 — Implementar estado de investigação no frontend `[P0]`

- [ ] Adicionar estados READY, INVESTIGATING, COMPLETED e ERROR.
- [ ] Impedir duas requisições simultâneas.
- [ ] Preservar dataset ao iniciar nova comparação.

**Verificar:** cliques repetidos não disparam requisições duplicadas.

### W4.02 — Integrar a execução ao botão principal `[P0]`

- [ ] Montar payload com dataset, talhões, período e pergunta.
- [ ] Chamar `/api/investigations`.
- [ ] Mostrar progresso indeterminado e etapas textuais.
- [ ] Tratar erros sem recarregar a página.

**Verificar:** investigação fake conclui e navega para o resultado.

### W4.03 — Criar a Visão geral do Gemini `[P0]`

- [ ] Exibir título, resumo e força da evidência no topo.
- [ ] Identificar quando o resultado veio do fallback.
- [ ] Renderizar com `textContent`, nunca `innerHTML` externo.
- [ ] Criar a área **Visão de solo** logo após o resumo, com métricas descritivas, Conjunto 1 × Conjunto 2 e aviso de escopo geral.
- [ ] Tratar a visão de solo como seção prioritária do dashboard, com cards de qualidade e acesso às visualizações detalhadas.
- [ ] Não apresentar amostras como pertencentes aos talhões selecionados.

**Verificar:** caracteres especiais e texto malicioso aparecem como texto, não como HTML.

### W4.04 — Criar cards de achados e recomendações `[P0]`

- [ ] Renderizar achados em ordem.
- [ ] Mostrar evidências relacionadas.
- [ ] Renderizar recomendações e justificativas.

**Verificar:** todo card aponta para ao menos um `evidence_id` existente.

### W4.05 — Criar aba de evidências `[P0]`

- [ ] Mostrar métrica, alvo, referência, diferença e unidade.
- [ ] Mostrar quantidade de observações quando aplicável.
- [ ] Mostrar arquivos fonte.

**Verificar:** valores nulos aparecem como indisponíveis, nunca como zero.

### W4.06 — Integrar os gráficos reais `[P0]`

- [ ] Alimentar Chart.js com `chart_data` da resposta.
- [ ] Formatar datas e valores.
- [ ] Exibir estado vazio quando a ferramenta NDVI não foi executada.
- [ ] Integrar distribuição, comparação pareada e composição de textura do solo aos contratos reais.
- [ ] Exibir tooltip, unidade, amostras válidas, fonte e tabela acessível em cada visualização.
- [ ] Manter mapa, tendência temporal e perfil de profundidade indisponíveis para solo enquanto faltarem os campos necessários.

**Verificar:** cada gráfico usa exatamente os pontos e resumos presentes nas evidências correspondentes, sem cálculo analítico paralelo no frontend.

### W4.07 — Criar abas de limitações e métodos `[P0]`

- [ ] Mostrar limitações e regras associadas.
- [ ] Mostrar ferramentas, fontes e duração.
- [ ] Exibir modelo, horário e origem do relatório.
- [ ] Ocultar detalhes internos sensíveis.

**Verificar:** trace é legível sem mostrar prompts, chave ou dados brutos.

### W4.08 — Implementar relatório HTML `[P1]`

- [ ] Criar gerador server-side com conteúdo autocontido.
- [ ] Escapar todos os textos.
- [ ] Incluir visão geral, evidências, limitações, métodos e origem.
- [ ] Criar endpoint de download.

**Verificar:** arquivo baixa, abre offline e não executa conteúdo vindo do Gemini.

### W4.09 — Servir o build do frontend pelo FastAPI `[P0]`

- [ ] Configurar build do Vite.
- [ ] Servir assets e fallback do `index.html` no FastAPI.
- [ ] Manter proxy separado apenas para desenvolvimento.

**Verificar:** apresentação funciona em uma única URL local após o build.

### W4.10 — Revisar responsividade e acessibilidade `[P1]`

- [ ] Verificar navegação por teclado.
- [ ] Adicionar labels, foco visível e regiões de status.
- [ ] Conferir contraste e leitura em tela projetada.
- [ ] Ajustar telas de 390 px, 820 px e desktop.

**Verificar:** fluxo principal pode ser realizado sem mouse e sem texto cortado.

### W4.11 — Implementar painel de pré-apresentação `[P1]`

- [ ] Mostrar backend conectado.
- [ ] Mostrar Gemini configurado.
- [ ] Adicionar botão **Testar Gemini**.
- [ ] Exibir latência e mensagem de erro compreensível.

**Verificar:** teste pode ser executado antes da banca sem iniciar investigação.

### W4.12 — Testar falhas reais `[P0]`

- [ ] Rodar sem chave.
- [ ] Simular timeout.
- [ ] Simular rate limit.
- [ ] Simular saída inválida.
- [ ] Confirmar fallback e avisos.

**Verificar:** nenhuma dessas falhas derruba a aplicação.

### W4.13 — Executar teste ponta a ponta `[P0]`

- [ ] iniciar a aplicação do zero;
- [ ] importar os sete arquivos;
- [ ] executar Grão 4.0 × Grão Convencional;
- [ ] conferir visão geral, visão de solo, evidências, gráfico e limitações;
- [ ] baixar relatório;
- [ ] executar nova comparação sem reenviar arquivos.

**Verificar:** todo o fluxo conclui sem console error ou stack trace visível.

### W4.14 — Preparar o roteiro da demonstração `[P0]`

- [ ] Escrever sequência de cliques e fala principal.
- [ ] Definir pacote exato e pasta de fácil acesso.
- [ ] Medir tempo do fluxo.
- [ ] Ensaiar resultado Gemini e fallback.

**Meta:** concluir a parte interativa em até dois minutos após selecionar os arquivos.

### W4.15 — Congelar a versão da apresentação `[P0]`

- [ ] Executar todos os testes.
- [ ] Registrar versões de Python, Node e dependências.
- [ ] Confirmar `.env` e dados fora do Git.
- [ ] Criar tag ou commit identificável.
- [ ] Não adicionar funcionalidades depois do congelamento sem necessidade crítica.

**Saída:** versão pronta para a banca.

## 7. Corte de escopo se o prazo apertar

Não cortar:

- importação real;
- validação dos sete arquivos;
- seis análises;
- Gemini via harness;
- visão geral escrita;
- evidências e limitações;
- fallback;
- proteção da chave.

Cortar primeiro, nesta ordem:

1. animações e transições visuais;
2. endpoint de diagnóstico;
3. download com gráfico incorporado;
4. refinamentos avançados de responsividade;
5. operações além de CALAGEM;
6. publicação online.

## 8. Checklist de pré-apresentação

- [ ] notebook conectado à energia;
- [ ] internet testada;
- [ ] `GEMINI_API_KEY` configurada;
- [ ] endpoint de saúde verde;
- [ ] teste do Gemini concluído;
- [ ] arquivos da demonstração em uma pasta única;
- [ ] servidor iniciado antes da apresentação;
- [ ] navegador aberto na tela inicial;
- [ ] zoom adequado ao projetor;
- [ ] fallback testado no mesmo computador;
- [ ] relatório de exemplo disponível apenas como contingência;
- [ ] nenhuma aba mostra a chave ou console com dados sensíveis.

## 9. Prompt curto para iniciar cada sessão do Codex

```text
Leia PROJETO.md, SPEC.md, PIPELINES.md e PLANEJAMENTO_CODEX.md. Inspecione o repositório e encontre a primeira tarefa não concluída cujas dependências estejam prontas. Implemente somente essa tarefa, execute as verificações indicadas, atualize o checklist e o Diário de execução, e pare. Não amplie o escopo.
```

## 10. Diário de execução

Adicionar uma linha por tarefa concluída.

| Data | Tarefa | Resumo | Testes | Pendências |
| --- | --- | --- | --- | --- |
| 2026-09-19 | W1.01 | Estrutura inicial, README, proteção de segredos/dados e branch da semana criados. | Árvore inspecionada; busca por CSVs versionáveis. | Comandos ainda serão completados nas próximas tarefas. |
| 2026-09-19 | W1.02 | Backend FastAPI mínimo, health check e comando Uvicorn adicionados. | `uv run pytest tests/test_health.py` (1 passou); servidor local e `GET /api/health` (200). | Avisos de depreciação das integrações atuais de TestClient, sem impacto funcional. |
| 2026-09-19 | W1.03 | Configuração tipada e health check seguro com estado do Gemini, modelo e versão. | `uv run pytest tests/test_health.py` (2 passaram, com e sem chave). | Integração com Gemini permanece fora do escopo até W3. |
| 2026-09-19 | W1.04 | Frontend Vanilla modular inicializado com Vite, proxy da API e CSS base. | `pnpm build`; `pnpm dev --host 127.0.0.1`; página Vite respondeu 200. | Runtime local usa pnpm; scripts Vite permanecem padronizados. |
| 2026-09-19 | W1.05 | Tokens visuais e layout responsivo com navegação lateral/cabeçalho adaptativo. | `pnpm build`; inspeção no navegador em 1440, 820 e 390 px, sem overflow ou logs de erro; busca por Streamlit vazia. | Não havia protótipo visual versionado; identidade foi derivada do contexto agrícola e dos requisitos. |
| 2026-09-19 | W1.06 | Contratos Pydantic estritos para arquivos, talhões, issues, pares e resposta de validação. | `uv run pytest tests/test_contracts.py tests/test_health.py` (6 passaram). | `dataset_id` é nulo nas respostas de pacote inválido; datasets prontos sempre recebem UUID. |
| 2026-09-19 | W1.07 | Loader seguro com nomes fechados, limite total, delimitadores e fallback de encoding. | `uv run pytest tests/test_loader.py tests/test_contracts.py tests/test_health.py` (15 passaram). | A inferência de tipos fica deliberadamente para os normalizadores específicos. |
| 2026-09-19 | W1.08 | `fields.csv` validado e normalizado com centroide, geometria, rótulo, finalidade, manejo e alias conhecido. | Cobertura revisada em 2026-09-23, incluindo quatro talhões artificiais, WKT e `field_name_normalized`. | Nomes fora das regras recebem `unknown`, conforme especificado. |
| 2026-09-19 | W1.09 | Catálogo de ordens e relações um-para-muitos validados; número canônico resolve o ID e ordens compartilhadas são aceitas. | Cobertura revisada em 2026-09-23 para canonicalização, compartilhamento válido e conflito impeditivo. | Nome da operação é preservado para auditoria; geometria decide o talhão. |
| 2026-09-19 | W1.10 | Mapas operacionais normalizados, datados e ligados espacialmente entre os candidatos da ordem. | Cobertura revisada em 2026-09-23 para ponto representativo, fallback de 50%, descarte externo e empate impeditivo. | Linhas inválidas são descartadas com aviso agregado; fórmulas permanecem para W2. |
| 2026-09-19 | W1.11 | NDVI validado por data, CRS, bounds, pixels e faixa, sem interpolação. | Suíte parcial da Semana 1 (30 passaram). | CRS diferente de EPSG:3857 é erro impeditivo; agregação ponderada ocorre após a ligação espacial. |
| 2026-09-19 | W1.12 | Séries NDVI ligadas espacialmente com conversão, Haversine, limites e rastreabilidade. | Suíte parcial da Semana 1 (34 passaram), com regressão de quatro séries e agregação ponderada. | Empate até 1 m é tratado como ambíguo; distância de 500–1.000 m gera aviso. |
| 2026-09-19 | W1.13 | Store em memória por UUID para objetos normalizados, com substituição e cópias defensivas. | Suíte parcial da Semana 1 (38 passaram). | Estado é perdido ao reiniciar o processo, conforme o requisito sem persistência. |
| 2026-09-19 | W1.14 | Endpoint multipart integra os seis arquivos, validação, qualidade, pares disponíveis, vínculo operacional e store temporário. | Suíte final revisada em 2026-09-23: 49 testes, incluindo 201 completo, 422 inválido e 413 excedente. | Score de comparabilidade e análises permanecem para W2; `quality_score` foi documentado. |
| 2026-09-19 | W1.15 | Tela de importação conectada ao multipart de seis arquivos, com status, qualidade, issues e talhões. | Vitest (4 passaram), build Vite e fluxo real no navegador revisado em 2026-09-23; botão Continuar habilitado. | O botão emite evento para a futura tela de comparação, sem iniciar W2. |
| 2026-09-19 | W1.16 (bloqueada) | Suítes finais e importação manual executadas sob a revisão anterior do SPEC; pacote real expôs ordens compartilhadas e o alias `Convecional`. | Pytest: 42 passaram; Vitest: 4 passaram; Vite build passou; pacote real retornou 422 sob o contrato anterior. | Registro histórico superado pela revisão do SPEC e pela execução de 2026-09-23. |
| 2026-09-23 | W1.08–W1.15 (revisão de contrato) | Implementação alinhada ao SPEC revisado: sexto CSV, `fieldGeom`, alias de nome, catálogo de ordens, candidatos compartilhados e vínculo espacial das operações. | Pytest: 49 passaram; Vitest: 4 passaram; Vite build passou; casos obrigatórios de vínculo espacial cobertos por fixtures artificiais. | Fórmulas analíticas permanecem fora do escopo até W2. |
| 2026-09-23 | W1.16 | Pacote real validado pela API e pelo navegador; quatro talhões e dois pares (Grão e Silagem) confirmados, sem ambiguidade espacial. | Importação real: 201/`ready_with_warnings`, qualidade 60, 23.738 linhas atribuídas, 9.599 não atribuídas, 30 geometrias inválidas e 0 ambíguas; botão Continuar habilitado. | Nenhuma pendência impeditiva da Semana 1. |
| 2026-10-07 | Revisão de escopo | Documentação atualizada para exigir `soil_analysis.csv`, criar `R1.01`–`R1.06`, acrescentar duas ferramentas de solo e adotar `#895129` como cor principal. | Revisão documental; implementação ainda não executada. | Solo permanece no escopo geral do dataset; `_2` significa somente Conjunto 2 até haver metadado. |
| 2026-10-07 | R1.01 | Contrato de upload ampliado para sete arquivos, com `soil_analysis.csv` obrigatório e resumo de solo na resposta. | Testes de pacote completo e ausência do sétimo arquivo; regressão da API. | As seis fontes anteriores foram preservadas. |
| 2026-10-07 | R1.02 | Normalizador de solo com BOM, ponto e vírgula, vírgula decimal, regras de domínio, grupos e avisos; store defensivo para os dicionários normalizados. | Pytest cobre valores válidos, duplicidade, inválidos sem zero, textura fora da tolerância, opcionais e ausência de Conjunto 2. | Amostras usam somente `sample_id`, `scope`, `group_1` e `group_2`; não há vínculo com talhão. |
| 2026-10-07 | R1.03 | API, sessão e importação exibem disponibilidade, grupos e quantidade válida de amostras. | Pacote real via API e navegador: 8 amostras, sete arquivos válidos e botão Continuar habilitado. | O solo permanece apenas em memória e no escopo geral do dataset. |
| 2026-10-07 | R1.04 | Identidade marrom aplicada por tokens, com `#895129` como primária e estados semânticos preservados. | Layouts 1440/820/390 sem overflow; contrastes principais entre 6,42:1 e 14,16:1; build Vite. | Hexadecimais de interface ficaram centralizados em `tokens.css`. |
| 2026-10-07 | R1.05 | Fixtures e regressões atualizadas para sete arquivos; pacote acadêmico real revalidado. | Pytest: 56 passaram; Vitest: 4 passaram; Vite build passou; real: 201/`ready_with_warnings`, qualidade 60, 15 avisos, 8 amostras. | A única variação do baseline é o novo aviso agregado sobre unidades/faixas de solo não documentadas; vínculos operacionais permanecem iguais. |
| 2026-10-07 | R1.06 | README, checkboxes, diário e handoff atualizados; execução encerrada antes de W2.01. | Branch `feat/heloisa`; working tree sobre `5bc3e70`; comandos reproduzíveis registrados no handoff. | Nenhum commit foi criado automaticamente e nenhuma tarefa W2 foi iniciada. |
| 2026-10-07 | R1.07 | Os seis documentos-base foram atualizados antes do frontend com a direção visual, o contrato das prévias e os limites dos mocks. | Revisão cruzada de HANDOFF, PIPELINES, PLANEJAMENTO, PROJETO, README e SPEC. | Dados demonstrativos permanecem isolados do backend e não contam como evidência. |
| 2026-10-07 | R1.08 | Shell de dashboard responsivo e prévias clicáveis de Comparação e Investigação concluídos, mantendo `#895129`. | Pytest: 56 passaram; Vitest: 7 passaram; Vite build passou; Chrome validado em 1440/820/390, sem overflow horizontal. | W2.01 não foi iniciado; os mocks devem ser substituídos apenas por contratos analíticos validados. |
| 2026-10-07 | Direção futura de gráficos | Documentos atualizados para priorizar um dashboard analítico de solo mais rico nas Semanas 2 e 4, mantendo a prévia atual como demonstração simples. | Revisão cruzada de SPEC, PROJETO, PIPELINES, PLANEJAMENTO, HANDOFF e README; nenhuma implementação executada. | Os gráficos futuros dependem das evidências reais e não podem inventar mapa, tempo, profundidade, unidade ou classificação agronômica. |
| 2026-10-11 | W2.01 | Contrato comum de evidência com metadados obrigatórios, valores finitos ou nulos e gerador determinístico de IDs por prefixo, local à investigação; verificada reutilização por herança/composição para as sete ferramentas previstas. | Em `backend/`: `.venv/bin/python -m pytest` — 108 passaram, incluindo 52 novos casos do protocolo; `git diff --check` sem erros. | Aviso de depreciação existente de Starlette/httpx; nenhuma dependência adicionada e W2.02 não iniciada. |
| 2026-10-11 | W2.02–W2.09 | Pares nos dois sentidos, cinco critérios de comparabilidade e seis análises determinísticas com evidências tipadas; solo inclui quartis, pares por AMOSTRA e textura normalizada no backend somente para somas entre 95 e 105. | 23 casos manuais de analytics passaram: sinal e datas NDVI, corte pré-plantio, ponderação, divisão por zero, sobreaplicação, quartis, nulos e pares de solo. | NDVI exige ao menos uma data pareada; menos de cinco reduz o score e emite aviso. Baseline real adiado a pedido do usuário. |
| 2026-10-11 | W2.10–W2.11 | Registry local fechado com sete ferramentas, parâmetros tipados e versão; diagnóstico local em `POST /api/diagnostics/tools`, bloqueado fora de development. | Suíte backend: 153 passaram; cobertura de todas as ferramentas, chamadas inválidas, IDs, parâmetros extras e ambientes presentation/production/test. | Sem SDK, chamadas externas, prompt ou harness de IA. Cada chamada isolada de diagnóstico tem IDs locais; um gerador pode ser compartilhado por um chamador futuro. |
| 2026-10-12 | W2.12 | Tela de comparação usa somente talhões dos pares retornados pela API, atualiza a pergunta, mostra cinco critérios e análises disponíveis e bloqueia pares inválidos; diagnóstico local após importação e prévia sem upload claramente separados. | 8 testes de comparação passaram, incluindo Grão × Silagem, resposta atrasada, erro, par ausente e inversão; navegador confirmou importação dos sete CSVs artificiais, score 3/5 e bloqueio do par inválido. | Consulta local disponível em development; o botão abre gráficos demonstrativos, sem executar investigação de IA. |
| 2026-10-12 | W2.13 | Chart.js para NDVI, distribuição de cinco números, pares de solo e textura; filtros de família/métrica/conjunto, unidades, contagens, fontes, estados vazios e tabelas acessíveis; instâncias destruídas em trocas de filtro, aba e página. Mocks decorativos substituídos por contratos numéricos locais validados no backend. | Pytest: 154 passaram; Vitest: 25 passaram; `pnpm build` e `git diff --check` passaram. Navegador: gráficos de solo/NDVI, abas e larguras de desktop/tablet/celular sem overflow horizontal ou erros de console. | W2.14 permanece pendente por solicitação do usuário. Nenhuma integração Gemini ou tarefa W3 iniciada; aviso de depreciação Starlette/httpx já existente. |
| 2026-10-13 | W2.14 | Sete CSVs reais de FarmLab importados pela API; seis análises e comparabilidade conferidas por recálculo independente dos arquivos. Confirmadas 8 amostras, 29 pares NDVI, gap −0,024985204049, população 61.306,27/63.629,03 e calagem 57,327136%/97,500150%. Diferenças do protótipo investigadas e documentadas em BASELINE_W2.md; manifesto SHA-256 e nove regressões sem versionar CSV bruto. | `FARMLAB_REAL_DATA_DIR='/Users/lucashygidio/Downloads/FarmLab' .venv/bin/python -m pytest` em backend: 163 passaram; baseline isolado: 9 passaram; sem variável: 9 ignorados explicitamente. Vitest: 25 passaram; build Vite e `git diff --check` aprovados. | Semana 2 concluída; W3 não iniciada. Mantidos 15 avisos de importação e depreciação Starlette/httpx. Gráficos da investigação continuam demonstrativos; origem exata das aproximações antigas não verificável sem código do protótipo. |
| 2026-10-15 | W3.01 | SDK oficial google-genai 2.31.0 instalado e travado; cliente criado apenas na primeira geração, modelo e timeout configuráveis, erros seguros e encerramento de conexões. httpx passou a dependência de execução. | 25 testes novos do cliente; cliente + health: 27 passaram; suíte backend: 179 passaram e 9 reais ignorados; uv sync --locked, uv pip check e git diff --check aprovados. | Sem chamada real ao Gemini; W3.02 é a próxima etapa. Prazo total, retry único de 429 e fallback serão tratados no harness. Preservadas as correções UTF-8 da instalação no Windows; três avisos de depreciação de terceiros. |
| 2026-10-15 | W3.02 | POST /api/gemini/test registrado com prompt fixo, chamada única limitada a 32 tokens, modelo configurável, sucesso, latência monotônica e mensagens seguras para chave ausente, autenticação, cota, timeout e indisponibilidade. Contrato documentado no OpenAPI e README. | 29 novos testes da rota; suíte backend: 208 passaram e 9 reais ignorados. Uvicorn temporário: health 200, teste sem chave 503/missing_api_key e rota no OpenAPI; servidor encerrado. git diff --check aprovado. | Chave real não testada; respostas externas simuladas inclusive pelo SDK oficial. W3.03 é a próxima tarefa. Mantidos três avisos de depreciação de terceiros. |
| 2026-10-15 | W3.03 | Schemas de requisição, trace, relatório e resposta final; objetos fechados, enums de força/origem, argumentos tipados e gráficos preservando as evidências da W2. Evidence extraída para módulo independente com import público compatível. | 112 novos casos; contratos + evidências: 164 passaram. Suíte backend: 320 passaram, 9 reais ignorados e 3 avisos existentes; git diff --check aprovado. Execução completa repetida com permissão ampliada após interrupção por falta de progresso no sandbox. | Sem chamada externa ou nova dependência. Existência dos IDs, conteúdo numérico/causal e limitações específicas serão validados nas tarefas seguintes. W3.04 é o próximo item e não foi iniciado. |
| 2026-10-15 | W3.04 | SYSTEM_PROMPT estático em português: papel observacional, ferramentas como única fonte de números, referências existentes, proibição de causalidade, pergunta não confiável, limites do solo e síntese conforme InvestigationReport. | Revisão contra SPEC; importação e AST sem chamadas/interpolação; auditoria sem credenciais, IDs concretos, caminhos ou resultados fixos. Suíte backend: 320 passaram, 9 reais ignorados e 3 avisos existentes; git diff --check aprovado. | Sem chamada ao Gemini, novas dependências ou alteração da rota de teste. Integração e validação em execução continuam nas próximas tarefas. W3.05 é o próximo item e não foi iniciado. |
| 2026-10-15 | W3.05 | Adaptador build_gemini_tool gera sete declarações a partir do registry e dos contratos Pydantic, com descrições dos argumentos e sem callables ou parâmetros internos. Corrigida a contagem antiga de cinco no checklist para incluir as ferramentas de solo já previstas. | 17 novos testes; focados de declarações/cliente/schemas: 154 passaram. Suíte backend: 337 passaram, 9 reais ignorados e 3 avisos existentes. Payload HTTP do SDK verificado em memória; git diff --check aprovado. | Sem chamada externa ou nova dependência. Aceitação pelo serviço real permanece em W3.15; validação de chamadas e orchestrator ainda pendentes. Próximo item: W3.06. |
| 2026-10-15 | W3.06 | Validador por investigação com allowlist do registry, parâmetros Pydantic, IDs da sessão, preservação de dataset/par/período e bloqueio de repetições normalizadas. Erros locais seguros e retorno de argumentos tipados para execução futura. | 54 novos casos passaram; suíte backend: 391 passaram, 9 reais ignorados e 3 avisos existentes. Inclui execução local das sete ferramentas após validação; git diff --check aprovado. | Sem chamada externa ou nova dependência. Integração no loop, limite de oito chamadas e ordem de comparabilidade permanecem na W3.08. Próximo item: W3.07. |
| 2026-10-15 | W3.07 | Recorder local por investigação com UUIDs, argumentos normalizados, sequência, versões, evidências/fontes e duração monotônica; integração com validador, gerador de evidências e execução de uma ferramenta. Snapshots defensivos e erros locais sem copiar resultados completos ou exceções brutas. | 26 novos testes passaram; suíte backend: 417 passaram, 9 reais ignorados e 3 avisos existentes. Inclui sete ferramentas, falha real, relógio retrocedendo, isolamento, serialização e privacidade; git diff --check aprovado. | Sem chamada externa ou nova dependência. Rejeições anteriores à execução não geram entrada de execução. Loop Gemini, orçamento e ordem de comparabilidade permanecem na W3.08, próximo item. |
| 2026-10-16 | W3.08 | Loop de ferramentas com contexto mínimo, comparabilidade obrigatória, execução sequencial validada, schemas de retorno, evidências/trace, IDs/assinaturas do SDK, limite de oito chamadas, prazo e retry único de 429. | 34 novos testes de loop e nove de timeout passaram; suíte backend: 460 passaram, 9 reais ignorados e 3 avisos existentes. Cliente fake e SDK com HTTP em memória; git diff --check aprovado. | Sem chamada externa ou nova dependência. Retorno interno para futura síntese; falhas preservam evidências parciais. Prazo verificado entre etapas síncronas. Próximo item: W3.09; não iniciado. |
| 2026-10-16 | W3.09 | Síntese com contexto de evidências/avisos, regras estáticas, JSON Schema e validação Pydantic do texto recebido. Integração ao planejamento com cliente, prazo e retry compartilhados; rascunho interno preserva fatos e trace em falhas. | 43 testes novos passaram; suíte backend: 503 passaram, 9 reais ignorados e 3 avisos existentes. Testes fake e SDK com HTTP em memória; git diff --check aprovado. | Sem chamada externa ou nova dependência. Validação apenas estrutural; evidências/números/limitações na W3.10, linguagem causal na W3.11, reparo/fallback/API nas tarefas seguintes. Próximo item: W3.10; não iniciado. |
| 2026-10-16 | W3.10 | Validador de referências, fatos numéricos citados, sinal/unidade e limitações obrigatórias; catálogo tipado, escopo por trecho, precisão decimal e contexto de data/amostra. Integração na síntese com erros localizados e seguros. | 80 testes de validação e cinco de integração novos passaram; suíte backend: 588 passaram, 9 reais ignorados e 3 avisos existentes. git diff --check aprovado. | Sem API externa ou dependência nova. Regras conservadoras para formatos explícitos; limitações fornecidas pelo backend devem ser preservadas. Não valida causalidade nem repara o relatório. Próximo item: W3.11. |
| 2026-10-16 | W3.11 | Validador de linguagem causal com ressalvas locais, fronteiras de oração, exceções literais/administrativas e cobertura de todos os campos narrativos. Integração na síntese com erros seguros e localizados para futuro reparo. | 91 testes de linguagem e quatro de integração novos passaram; suíte backend: 683 passaram, 9 reais ignorados e 3 avisos existentes. git diff --check aprovado. | Sem API externa ou nova dependência. Validação lexical conservadora; não interpreta toda prosa possível. Reparo, fallback e endpoint permanecem pendentes. Próximo item: W3.12. |
| 2026-10-16 | W3.12 | Uma tentativa de reparo com erros seguros, schema e fatos; sem repetir ferramentas. Revalida o relatório inteiro e registra motivo/resultado em trace.repair, com prazo e repetição de 429 compartilhados. | 34 testes novos passaram; 224 testes focados aprovados; suíte backend: 717 passaram, 9 reais ignorados e 3 avisos existentes. git diff --check aprovado. | Sem API externa ou nova dependência. Segunda falha preserva evidências e retorna erro final. Fallback e endpoint pendentes. Próximo item: W3.13. |
| 2026-10-16 | W3.13 | Gerador de fallback por templates sobre evidências existentes; origem fixa, aviso seguro, achados ordenados, limitações e recomendações. Correção da redação de limitação de solo incompatível com validação causal. | 45 testes novos passaram; suíte backend: 762 passaram, 9 reais ignorados e 3 avisos existentes. Casos sem chave/rede, falha após reparo, timeout parcial, ordem inversa do par, precisão, privacidade e validação completa. git diff --check aprovado. | Sem API externa ou nova dependência. Força conservadora weak. Próximo item W3.14: ativação automática, coleta local sem chave e endpoint; não iniciado. |
| 2026-10-16 | W3.14 | Endpoint síncrono e envelope completo; comparabilidade antes do provedor, plano local sem chave, fallback automático, gráficos/avisos/trace preservados e erros controlados. | 745 testes passaram inicialmente no ambiente restrito. Suíte completa executada pelo usuário e saída conferida: 827 passaram, 9 reais ignorados e 3 avisos existentes em 50,61 s, incluindo 41 novos testes de fluxo/rota direta/SDK/OpenAPI e 24 HTTP. git diff --check aprovado. | Pendência HTTP resolvida pela execução local informada pelo usuário. W3.14 concluída, sem chamada ao Gemini real ou nova dependência. Próximo item W3.15; não iniciado. |
| 2026-10-16 | W3.15 (preparação) | Comando opt-in app.harness.smoke com sete fixtures pequenas, checagem sem provedor, investigação limitada, validação do cenário e artefato local ignorado pelo Git. Pacote escolhido pelo Codex a pedido do usuário. | 14 testes novos; 100 focados passaram. Regressão sem módulos HTTP: 759 passaram, 9 reais ignorados, 3 avisos existentes em 39,39 s. Check-only aprovou os sete arquivos, sem chave configurada. | Preparação entregue; usuário configurará a chave e testará depois. Sem chamada real, ajuste de prompt ou mudança de cálculos. Gate W3.15 permanece pendente; W4 não iniciada. |
| 2026-10-17 | W3.15 | Chave local configurada; teste real com Gemini aprovado e relatório/trace inspecionados. Prompt e contexto reference_findings ajustados para preservar números/unidades e limitações; prazo local 120 s. Nenhuma fórmula ou regra de validação alterada. | Investigação c616c852-424a-45cb-91e6-769a46f56717: passed=true, oito ferramentas com sucesso, sem reparo/fallback. Conexão mínima: sucesso em 872 ms. Suíte completa: 841 passaram, 9 ignorados, 3 avisos em 41,40 s. Após último ajuste textual: 100 focados passaram. | W3.01–W3.15 concluídas; W4 não iniciada. Chave e artefatos locais ignorados pelo Git. Fallback segue disponível para futuras gerações inválidas. |
