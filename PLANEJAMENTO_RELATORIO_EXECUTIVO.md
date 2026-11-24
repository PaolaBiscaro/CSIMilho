# Planejamento do chat analítico, da investigação e do relatório executivo

## 1. Objetivo deste documento

Este documento redefine a entrega esperada do FarmLab Investigator antes de uma nova rodada de implementação.

O objetivo não é apenas melhorar a aparência da página. É transformar o produto em um chat analítico capaz de responder perguntas sobre os dados e, quando a intenção for investigativa, gerar um relatório executivo. O fluxo completo deve garantir que:

1. a pergunta seja decomposta em hipóteses analisáveis;
2. o backend selecione e execute os testes adequados;
3. resultados descritivos e estatísticos sejam combinados em conclusões rastreáveis;
4. o Gemini organize as evidências em um relatório executivo;
5. o frontend apresente uma resposta clara, visual e pronta para apresentação;
6. nenhuma análise possível com os dados atuais seja devolvida como “próximo passo”.

Este arquivo é um planejamento. Nenhuma das mudanças descritas abaixo deve ser considerada implementada até que as perguntas da seção 4 sejam respondidas e a etapa correspondente seja aprovada.

### Decisões confirmadas em 22/11/2026

- **Público principal:** produtor rural, mantendo linguagem compreensível também para pessoas leigas.
- **Formato recomendado como base:** síntese executiva curta no topo, relatório completo com rolagem na tela e versão reorganizada para impressão/PDF em A4.
- **Identidade visual:** manter a identidade marrom do FarmLab.
- **Dados disponíveis:** trabalhar somente com as informações já presentes nos arquivos atuais. Não inventar nem exigir para a apresentação campos que a pessoa usuária não possui.
- **Solo:** pode haver evolução futura do contrato, mas o pacote atual continuará sem vínculo entre amostra e talhão. O solo será tratado como contexto geral do dataset e nunca como explicação específica de um talhão.
- **Cobertura de perguntas:** qualquer pergunta válida pode ser enviada. “Funcionar” inclui concluir a análise ou informar claramente que os dados ou as ferramentas não sustentam a resposta.
- **Falha do Gemini:** se todas as chaves configuradas falharem, a entrega do relatório será bloqueada. Não publicar relatório de contingência como se fosse a resposta final.
- **Próximos passos analíticos:** não haverá seção genérica de próximos passos. Análises possíveis devem ser executadas dentro da investigação.
- **Experiência principal:** chat de perguntas e respostas sobre o dataset, as capacidades disponíveis e os resultados analíticos.
- **Tipos de pergunta:** catálogo de dados, catálogo de capacidades, descrição, investigação e pergunta complementar contextual.
- **Relatório:** relatório completo com rolagem, gerado quando a pergunta for investigativa.
- **Resposta parcial:** quando apenas parte da pergunta puder ser analisada, responder a parte sustentada, exibir gráficos relevantes e destacar separadamente o trecho não respondido e o motivo.
- **Linguagem técnica:** nomes de testes, p-valores e detalhes estatísticos ficam nos detalhes técnicos; a resposta principal permanece simples.
- **Tempo máximo:** até 90 segundos por investigação, com progresso visível e possibilidade de acompanhar os logs operacionais.
- **Continuidade:** perguntas complementares podem reutilizar o contexto e as evidências válidas da mesma conversa.
- **Hipóteses agronômicas:** conhecimento geral pode aparecer como hipótese explicativa, sempre separado do que os dados efetivamente sustentam.
- **Recomendação de campo:** permitida quando derivada de um sinal relevante, apresentada como recomendação operacional e nunca como substituição de análise pendente.

## 2. Diagnóstico do estado atual

### 2.1 Por que a resposta atual não atende

A saída atual apresenta resultados das ferramentas quase individualmente. Isso produz textos como médias, medianas, conformidades e contagens, mas não produz uma linha de raciocínio analítica.

O problema não é apenas de redação. Hoje faltam, principalmente:

- hipóteses explícitas derivadas da pergunta;
- testes estatísticos e temporais suficientes no registry;
- uma etapa que relacione resultados de módulos diferentes;
- critérios para transformar resultados em insights;
- um contrato de relatório orientado a conclusões, e não a uma lista de achados;
- uma distinção entre evidência, interpretação, hipótese explicativa e conclusão;
- uma síntese de contingência capaz de gerar relatório executivo quando o Gemini falha.

### 2.2 Limite atual do solo

O `soil_analysis.csv` atual possui escopo geral do dataset. As amostras não têm vínculo documentado com:

- talhão;
- coordenada;
- data da coleta;
- profundidade;
- unidade das variáveis;
- referência agronômica para classificação.

Consequentemente, o sistema pode comparar os conjuntos presentes no arquivo, mas não pode afirmar que um elemento químico:

- pertence ao talhão Grão 4.0 ou ao Grão Convencional;
- explica uma diferença de NDVI;
- está baixo, adequado ou alto;
- influenciou o manejo ou a produtividade.

Esse limite não deve ser resolvido por uma redação mais convincente. Deve ser resolvido com novos dados ou com um escopo de conclusão mais restrito.

### 2.3 Limite atual das séries temporais

Um teste deve ser escolhido de acordo com o desenho dos dados, e não apenas pelo nome citado na pergunta.

- Mann–Whitney é apropriado para duas amostras independentes.
- Para NDVI dos mesmos períodos ou datas pareadas, Wilcoxon pareado ou teste de permutação pareado tende a ser mais coerente.
- Para mudanças dentro de uma única série, devem ser considerados módulos de anomalia, tendência, segmentação por período ou detecção de mudança.
- Dependência temporal, poucos pontos e múltiplos testes precisam aparecer na validação do método.

O Gemini poderá selecionar o tipo de pergunta, mas a escolha final do teste deve ser validada por regras determinísticas do backend.

## 3. Saída esperada

### 3.0 Chat analítico e tipos de resposta

Antes de gerar qualquer relatório, o sistema classifica a intenção da mensagem:

| Intenção | Exemplo | Saída esperada |
|---|---|---|
| `data_catalog` | “Quais dados estão disponíveis?” | Lista compreensível dos arquivos, períodos, talhões, métricas, vínculos e limitações do pacote atual. |
| `capability_catalog` | “O que a ferramenta consegue me informar?” | Lista dinâmica das análises descritivas, testes de hipótese, séries, comparações e limitações registradas no backend. |
| `descriptive_query` | “Como foi o NDVI deste talhão?” | Resposta descritiva curta, com números e gráficos relevantes, sem forçar hipótese ou relatório executivo. |
| `investigative_query` | “Houve uma mudança significativa no vigor após determinado período?” | Planejamento de hipóteses, execução das ferramentas e relatório executivo completo. |
| `contextual_followup` | “E isso também ocorreu no outro talhão?” | Nova resposta usando o contexto explícito da conversa, sem reutilizar fatos incompatíveis ou evidências vencidas. |
| `unsupported_query` | Pedido fora dos dados e capacidades | Explicação clara do que não pode ser respondido, distinguindo falta de dados, ferramenta ou escopo. |

O catálogo de capacidades não deve ser escrito manualmente no prompt. Ele será projetado a partir do registry de ferramentas, de seus metadados e dos dados efetivamente presentes no pacote.

Respostas descritivas podem apresentar resumo, tabela curta e gráfico, mas não devem inventar hipótese estatística. Uma resposta descritiva pode ser transformada em investigação por uma pergunta complementar ou por uma ação explícita na interface.

Quando a intenção for investigativa, a conversa transita para o relatório com rolagem descrito abaixo. O histórico da conversa permanece visível acima ou em uma coluna lateral, sem competir com a leitura do relatório.

### 3.1 Princípio editorial

O relatório seguirá uma estrutura Top-Down e BLUF — *Bottom Line Up Front*:

1. resposta direta à pergunta;
2. conclusões principais que sustentam a resposta;
3. evidências visuais e quantitativas;
4. interpretação e riscos;
5. metodologia e rastreabilidade técnica.

Não haverá uma seção genérica de “Próximos passos”.

Se uma análise pode ser executada com os dados e ferramentas atuais, ela deve acontecer durante a própria investigação. Se não pode, o relatório registra a lacuna na seção de limitações, especificando:

- **dados ausentes:** quais colunas, vínculos, períodos ou amostras faltam;
- **ferramenta ausente:** qual método ainda precisa ser implementado;
- **limite científico:** qual conclusão o desenho observacional não permite.

Uma recomendação de verificação em campo poderá existir apenas como consequência da conclusão, nunca como substituta de uma análise que o sistema já poderia ter executado.

### 3.2 Estrutura proposta do relatório

#### Cabeçalho executivo

- pergunta investigada;
- escopo: talhão único ou comparação;
- período;
- data de geração;
- nível de confiança;
- origem da síntese e estado da execução do Gemini, sem expor chaves.

#### Resposta executiva

Um bloco destacado contendo:

- resposta direta em uma ou duas frases;
- conclusão principal;
- principal ressalva;
- indicação clara de `conclusivo`, `indicativo`, `inconclusivo` ou `não analisável`.

#### Insights principais

No máximo três a cinco insights. Cada insight deve conter:

1. **Conclusão:** o que foi observado;
2. **Como foi verificado:** teste ou análise aplicada;
3. **Evidência:** valores relevantes, período e fontes;
4. **Interpretação:** o que o resultado pode significar;
5. **Limite:** o que não pode ser concluído.

Uma média ou mediana isolada não é um insight. Ela só aparece quando sustenta uma conclusão.

#### Gráficos com takeaway

Cada gráfico deve ter:

- título que já expresse a conclusão;
- visualização;
- período e unidade;
- fontes;
- texto curto “O que este gráfico mostra”.

Os gráficos atuais que já funcionam devem ser preservados, mas reorganizados dentro do relatório.

#### Relações entre sinais

Quando houver chave temporal ou espacial compatível, o relatório poderá relacionar:

- NDVI e operações;
- NDVI e população;
- mudanças da série e eventos registrados;
- grupos de solo e outras variáveis, somente quando existir vínculo válido.

Associação não será descrita como causalidade.

#### Limitações

Somente limitações relevantes para a pergunta, agrupadas por:

- dados;
- ferramental;
- desenho estatístico;
- interpretação agronômica.

#### Detalhes técnicos

Em aba separada ou seção recolhível:

- hipótese nula e alternativa;
- teste aplicado e justificativa;
- unidade observacional;
- tamanho da amostra;
- pressupostos;
- estatística, p-valor, tamanho de efeito e intervalo, quando aplicáveis;
- correção de múltiplos testes;
- ferramentas executadas;
- IDs das evidências;
- arquivos de origem;
- avisos e falhas controladas.

### 3.3 Exemplo de resposta desejada para a pergunta de solo

Pergunta:

> O que as análises de solo indicam sobre o contexto da área e quais sinais aparecem na execução de correção e no vigor dos talhões Grão 4.0 e Grão Convencional?

Com dados adequados, o relatório deveria seguir esta lógica:

1. verificar vínculo das amostras de solo com cada talhão;
2. testar diferenças nas variáveis de solo com método compatível e correção para múltiplas métricas;
3. estimar tamanho das diferenças, não apenas significância;
4. analisar execução de correção em cada talhão;
5. analisar trajetória, diferença e mudanças do NDVI;
6. verificar coincidência temporal entre operações e mudanças da série;
7. sintetizar quais sinais aparecem juntos, sem afirmar causalidade;
8. entregar uma resposta direta e três a cinco conclusões sustentadas.

Com o CSV atual, a resposta correta deve declarar que o solo fornece contexto geral, mas não pode ser atribuído aos talhões. O sistema não deve inventar a influência de um elemento químico.

## 4. Perguntas que precisam ser respondidas antes da implementação

### 4.1 Perguntas prioritárias

1. O relatório será dirigido principalmente a professor/banca, produtor, gestor da fazenda ou analista agronômico?
2. Você quer um relatório de uma página, como as imagens, ou um relatório executivo mais longo com rolagem e versão para impressão?
3. A resposta executiva deve usar linguagem totalmente leiga ou pode empregar termos como p-valor, intervalo de confiança e tamanho de efeito fora da aba técnica?
4. Podemos alterar o modelo do `soil_analysis.csv` para incluir `field_id`, data, profundidade, unidade e referência, ou precisamos trabalhar obrigatoriamente com o arquivo atual? **Decisão:** o sistema deve funcionar com o arquivo atual; campos futuros podem ser opcionais, mas não podem ser usados na apresentação enquanto não existirem.
5. Na apresentação, quais perguntas precisam funcionar obrigatoriamente? **Decisão:** todas as perguntas devem receber uma saída correta; quando a análise não for suportada, a saída correta é explicar se faltam dados, ferramenta ou sustentação científica.
6. O sistema poderá responder “não é possível relacionar solo e talhão com estes dados” mesmo quando essa não for a resposta esperada pela banca?

### 4.2 Escopo científico

7. Existe um agrônomo ou material de referência autorizado para classificar nutrientes e atributos do solo?
8. Podemos usar apenas interpretação estatística, sem diagnóstico ou prescrição agronômica?
9. Qual nível de significância deve ser o padrão: 5% ou outro?
10. O relatório deve priorizar mediana e métodos robustos quando a amostra for pequena?
11. Quando houver poucas observações, prefere-se omitir o teste ou apresentar resultado exploratório com aviso?
12. O período da safra possui fases documentadas que possam ser usadas para segmentar a série?

### 4.3 Produto e interação

13. A investigação deve gerar um relatório novo a cada pergunta ou manter histórico de perguntas sobre o mesmo dataset?
14. O usuário poderá fazer uma pergunta complementar mantendo as evidências anteriores?
15. O relatório HTML baixado deve reproduzir exatamente a tela e ser preparado para A4?
16. Devem existir filtros por talhão, período e métrica dentro do relatório final?
17. A identidade visual marrom atual deve ser preservada ou o relatório pode adotar uma direção editorial azul semelhante às referências?
18. A aba técnica deve começar recolhida para a apresentação?

### 4.4 Contingência e Gemini

19. Quando todas as chaves Gemini falharem, o sistema deve gerar um relatório local mais limitado ou bloquear a entrega? **Decisão:** bloquear a entrega e informar a indisponibilidade.
20. A interface deve informar apenas “síntese de contingência” ou mostrar que houve troca de chave?
21. As três chaves pertencem ao mesmo projeto/cota do Google ou a projetos diferentes?
22. Devemos permitir configurar uma, duas ou três chaves somente por `.env`, sem entrada pela interface?

## 5. Arquitetura proposta para a investigação

### 5.1 Pipeline

```text
pergunta
→ classificação da intenção
├── catálogo de dados → resposta de disponibilidade
├── catálogo de capacidades → resposta gerada pelo registry
├── pergunta descritiva → ferramentas descritivas → resposta curta + gráficos
├── pergunta não suportada → classificação da lacuna → resposta explicativa
└── pergunta investigativa ou complementar
    → classificação do escopo
    → decomposição em hipóteses
    → inventário de dados e capacidades
    → plano fechado de análises
    → execução de todos os módulos possíveis
    → validação estatística e de evidências
    → integração dos resultados
    → síntese executiva pelo Gemini
    → verificação factual da síntese
    → relatório executivo com rolagem + detalhes técnicos
```

Perguntas complementares carregam apenas contexto estruturado: pergunta anterior, escopo, IDs de evidência e conclusões validadas. O histórico textual completo não se torna automaticamente uma nova fonte factual.

### 5.2 Papéis do Gemini

O Gemini poderá:

- interpretar a intenção da pergunta;
- selecionar capacidades registradas;
- organizar hipóteses;
- relacionar evidências já calculadas;
- redigir o relatório executivo;
- adaptar a linguagem ao público definido.

O Gemini não poderá:

- calcular estatísticas diretamente;
- criar um teste não registrado;
- ler CSV bruto;
- inventar unidade, vínculo ou referência agronômica;
- afirmar influência causal a partir de associação;
- devolver como “próximo passo” uma análise que o harness poderia executar.

### 5.3 Estado da investigação

Estados propostos:

1. `question_understood`;
2. `hypotheses_planned`;
3. `data_checked`;
4. `analyses_executed`;
5. `evidence_integrated`;
6. `report_synthesized`;
7. `report_validated`;
8. `completed` ou `completed_with_limitations`.

LangGraph pode ser avaliado para representar esse fluxo e suas transições. A adoção só será justificada se reduzir a complexidade do orquestrador atual, facilitar retomada e tornar o trace mais claro. Não será incluído apenas por preferência tecnológica.

### 5.4 Progresso e logs visíveis

Durante os até 90 segundos de processamento, a interface mostra uma linha de progresso simples e um painel de detalhes que pode ser aberto pela pessoa usuária.

Exemplos de eventos permitidos:

- identificando o tipo da pergunta;
- verificando quais dados estão disponíveis;
- hipótese selecionada para teste;
- ferramenta escolhida e motivo operacional;
- teste estatístico iniciado e concluído;
- quantidade de observações válidas;
- análise bloqueada por dados ausentes;
- análise bloqueada por ferramenta indisponível;
- integrando evidências;
- redigindo o relatório;
- validando números, fontes e linguagem;
- chave do provedor substituída, sem identificar ou revelar a chave;
- relatório concluído ou entrega bloqueada.

Esses eventos são logs operacionais e auditáveis. A interface não exibirá cadeia de pensamento, prompt interno, raciocínio privado do modelo, credenciais, respostas brutas do provedor ou conteúdo dos CSVs.

O painel detalhado ficará recolhido por padrão, mas o status atual e o tempo decorrido permanecerão visíveis. A investigação poderá ser cancelada com segurança e repetida sem novo upload enquanto o dataset continuar na sessão.

## 6. Ferramentas analíticas a priorizar

### 6.1 Série temporal e comparação de vigor

- diferença pareada de NDVI por data;
- Wilcoxon pareado ou permutação pareada, conforme pressupostos;
- tamanho de efeito e intervalo por reamostragem;
- tendência robusta;
- detecção de mudanças bruscas/anomalias;
- segmentação por fases documentadas da safra;
- comparação entre períodos;
- correção para dependência temporal e cobertura insuficiente.

### 6.2 Solo

- comparação pareada entre grupos por métrica;
- teste adequado ao desenho das amostras;
- tamanho de efeito;
- correção de múltiplos testes;
- ranking das métricas com maior diferença estatística e prática;
- classificação agronômica somente com unidade e referência autorizadas;
- relação com talhão somente com `field_id` ou vínculo espacial documentado.

### 6.3 Operações

- variabilidade da aplicação;
- desvio entre dose aplicada e configurada;
- cobertura e qualidade dos registros;
- alinhamento temporal entre aplicação e mudanças de NDVI;
- análise conjunta somente em granularidade compatível.

### 6.4 Regra de seleção de testes

Cada ferramenta deve declarar:

- pergunta que responde;
- dados mínimos;
- desenho independente ou pareado;
- hipótese nula e alternativa;
- pressupostos;
- tratamento de ausências e empates;
- estatística e tamanho de efeito;
- limitações;
- formato de evidência;
- testes automatizados.

O roteador pode sugerir Mann–Whitney, Wilcoxon, permutação ou análise descritiva, mas um validador determinístico confirma se o método é compatível com os dados.

## 7. Novo contrato de relatório

Estrutura conceitual proposta:

```text
ExecutiveInvestigationReport
├── question
├── scope
├── executive_answer
│   ├── status
│   ├── headline
│   ├── answer
│   ├── confidence
│   └── main_caveat
├── insights[]
│   ├── claim
│   ├── analytical_method
│   ├── evidence_summary
│   ├── interpretation
│   ├── uncertainty
│   ├── evidence_ids[]
│   └── chart_ids[]
├── charts[]
│   ├── title
│   ├── takeaway
│   └── evidence_id
├── limitations[]
│   ├── type: data | tooling | scientific
│   ├── impact
│   └── requirement
└── technical_appendix
    ├── hypotheses[]
    ├── tests[]
    ├── tool_calls[]
    └── sources[]
```

O schema final deve ser fechado e validado. Somente relatórios sintetizados pelo Gemini e aprovados pelos validadores serão entregues; estruturas locais podem apoiar testes internos, mas não substituem a resposta final quando as três chaves falharem.

## 8. Estratégia para até três chaves Gemini

### 8.1 Configuração

Compatibilidade proposta:

```text
GEMINI_API_KEY=<chave principal, mantida por compatibilidade>
GEMINI_API_KEY_2=<reserva opcional>
GEMINI_API_KEY_3=<reserva opcional>
```

Alternativamente, após decisão, poderá ser adotada uma variável única `GEMINI_API_KEYS` com lista separada por vírgula. O formato final não deve permitir que as chaves sejam enviadas ao frontend, trace ou logs.

### 8.2 Rotação por interação

Cada chamada ao modelo — planejamento, continuação do loop, síntese e reparo — passa por um `GeminiKeyPool`.

Comportamento proposto:

1. selecionar a primeira chave saudável;
2. executar uma única tentativa do SDK;
3. em erro associado à chave ou cota (`401`, `403`, `429`), marcar a chave em cooldown e repetir a mesma interação com a próxima;
4. em timeout, erro de rede ou indisponibilidade, permitir rotação conforme política definida;
5. não trocar de chave em erro de schema, prompt, argumento inválido ou validação local;
6. quando todas falharem, bloquear a entrega do relatório e retornar erro claro e recuperável;
7. preservar o orçamento total de tempo e chamadas da investigação.

A troca deve ocorrer no nível de cada chamada à LLM. Assim, uma investigação pode começar com a chave 1, continuar com a 2 e terminar com a 3 sem perder as evidências já calculadas.

### 8.3 Segurança e observabilidade

- nunca registrar a chave ou seu fragmento;
- identificar apenas `key_slot: 1 | 2 | 3` no trace interno;
- expor ao frontend apenas que houve recuperação de provedor, se essa informação for desejada;
- testar rotação em planejamento, loop de ferramentas, síntese e reparo;
- garantir que uma repetição de chamada da LLM não repita efeitos externos;
- manter ferramentas Python determinísticas e independentes da chave usada.

## 9. Plano de implementação por fases

### Fase 0 — Alinhamento do produto

- [x] Responder às perguntas prioritárias da seção 4.1.
- [x] Definir público e linguagem.
- [x] Definir três a cinco perguntas obrigatórias da apresentação.
- [x] Decidir se o contrato do CSV de solo pode mudar.
- [x] Aprovar o wireframe textual do relatório.

Perguntas de aceite escolhidas para a implementação inicial:

1. investigar mudanças relevantes na série temporal de um único talhão;
2. comparar o comportamento de vigor entre Grão 4.0 e Grão Convencional;
3. responder corretamente a uma tentativa de relacionar solo e talhão quando o vínculo necessário não existe.

**Critério de saída:** exemplos de entrada e saída aprovados antes de alterar código.

### Fase 1 — Contratos e critérios de aceite

- [x] Criar contrato fechado para intenção e tipo de resposta do chat.
- [x] Criar respostas estruturadas para catálogo de dados, capacidades, descrição, investigação e pergunta não suportada.
- [x] Criar o schema `ExecutiveInvestigationReport`.
- [x] Definir o contrato de hipótese e resultado estatístico.
- [x] Remover recomendações analíticas genéricas do novo contrato do relatório.
- [x] Definir limites de tamanho e quantidade de insights.
- [x] Criar fixtures de relatórios esperados para as perguntas obrigatórias.

Implementação concluída em `backend/app/harness/chat_contracts.py`, validada por testes fechados de schema e pelos três cenários de aceite em `backend/tests/test_chat_contracts.py`. O contrato novo ainda não substitui a API atual; a migração ocorrerá nas fases de orquestração e síntese.

**Critério de saída:** testes de schema e snapshots sem integração com Gemini.

### Fase 2 — Ferramental analítico

- [x] Implementar os testes priorizados para NDVI.
- [x] Implementar tamanho de efeito e incerteza.
- [x] Implementar análise de anomalias/mudanças na série.
- [x] Implementar testes de solo compatíveis com o contrato aprovado.
- [x] Implementar associação temporal entre operações e NDVI quando houver pares válidos.
- [x] Validar seleção de teste por desenho e tamanho da amostra.

Implementação concluída com módulos determinísticos para teste exato pareado de NDVI, tamanho de efeito bisserial por postos, intervalo não paramétrico para a mediana, detecção robusta de mudanças por mediana/MAD, associação temporal observacional entre operações e NDVI e testes pareados de solo com ajuste de Holm. O solo permanece estritamente no escopo do dataset. Amostras pequenas são classificadas como insuficientes em vez de receberem um teste inadequado.

**Critério de saída:** cada pergunta de aceite produz evidências determinísticas suficientes sem Gemini.

### Fase 3 — Orquestração analítica

- [x] Implementar classificação entre catálogo, descrição, investigação, complemento contextual e pergunta não suportada.
- [x] Gerar catálogo de capacidades a partir do registry e do dataset ativo.
- [x] Implementar memória estruturada da conversa, sem transformar texto anterior em evidência.
- [x] Implementar decomposição da pergunta em hipóteses.
- [x] Garantir que todas as análises possíveis sejam executadas antes da síntese.
- [x] Impedir “próximos passos” que correspondam a ferramentas já disponíveis.
- [x] Integrar resultados de múltiplos módulos.
- [x] Classificar lacunas como dados, ferramental ou limite científico.
- [x] Avaliar LangGraph com prova de conceito pequena antes de adoção.

Implementação concluída em `backend/app/harness/chat_orchestrator.py`, com contratos fechados em `backend/app/harness/orchestration_contracts.py` e rotas `/api/chat/route` e `/api/chat/capabilities/{dataset_id}`. O trace operacional preserva a sequência pergunta → intenção → hipóteses → ferramentas → evidências → conclusão, sem expor argumentos, prompts, chaves ou raciocínio interno. A memória mantém somente escopo, IDs de hipóteses/evidências, conclusão validada e tipos de lacuna.

**Decisão sobre LangGraph:** não adotar nesta versão. A prova conceitual foi representada pelo fluxo de estados tipado e validado do próprio harness. O processo atual é linear, limitado e executado em uma sessão; não há necessidade de checkpoints distribuídos, retomada entre processos ou ramificação dinâmica suficiente para justificar a dependência. Reavaliar somente se esses requisitos aparecerem.

**Critério de saída:** trace mostra pergunta → hipóteses → ferramentas → evidências → conclusão.

### Fase 4 — Pool de chaves Gemini

- [x] Adicionar configuração de até três chaves.
- [x] Criar seleção, cooldown e rotação por chamada.
- [x] Aplicar rotação em todas as interações com o Google.
- [x] Preservar deadline e orçamento de chamadas.
- [x] Adicionar testes para falha da primeira e segunda chaves.
- [x] Garantir ausência de segredos em API, logs e relatórios.

Implementação concluída no transporte central `GeminiClient`, utilizado por planejamento, continuação do loop, síntese, reparo e teste de conexão. As três credenciais permanecem como `SecretStr`; clientes SDK são criados sob demanda e fechados em conjunto. Cada interação começa na próxima chave saudável, erros permanentes desativam apenas a chave afetada e falhas transitórias aplicam cooldown. A repetição usa somente o tempo restante do prazo compartilhado de 90 segundos. Erros de requisição e validação, que não dependem da credencial, não provocam rotação.

**Critério de saída:** uma investigação simulada conclui após falhas sucessivas nas chaves 1 e 2 usando a chave 3.

### Fase 5 — Síntese e validação do relatório

- [x] Criar prompt orientado a BLUF e insights.
- [x] Fornecer ao Gemini apenas evidências validadas.
- [x] Validar toda afirmação numérica e referência.
- [x] Validar que cada insight contém método, evidência, interpretação e limite.
- [x] Remover a publicação do fallback como relatório final quando todas as chaves falharem.
- [x] Criar estado de erro claro, preservando o dataset e permitindo tentar novamente sem novo upload.
- [x] Rejeitar texto genérico, repetição de tabelas e causalidade não sustentada.

Implementação concluída em `backend/app/harness/executive_report.py`. O novo fluxo recebe o resultado tipado da orquestração, projeta apenas evidências calculadas, lacunas classificadas, gráficos permitidos e um apêndice técnico determinístico. O Gemini redige o relatório `ExecutiveInvestigationReportV2` em formato Top-Down e pode realizar um único reparo dentro do mesmo prazo. Antes da entrega, o backend confere pergunta, IDs de evidência, números narrativos, gráficos, partes não respondidas, limitações, fontes, métodos, linguagem causal e recomendações analíticas indevidas.

A rota `POST /api/chat/investigate` entrega somente um `ChatEnvelopeV2` aprovado. O endpoint anterior de investigação também deixou de publicar fallback como relatório concluído: falha de credencial, cota, timeout, provedor ou validação bloqueia a resposta, não salva relatório e preserva o dataset da sessão para nova tentativa.

**Critério de saída:** todo relatório entregue pelo Gemini passa pelos validadores; a indisponibilidade das três chaves bloqueia a entrega sem fabricar uma resposta final.

### Fase 6 — Interface e relatório baixável

- [x] Transformar a entrada de investigação em chat analítico.
- [x] Exibir histórico de perguntas e respostas do dataset ativo.
- [x] Criar respostas próprias para catálogo, descrição e indisponibilidade.
- [x] Permitir que uma resposta descritiva seja aprofundada como investigação.
- [x] Reestruturar a aba Resposta conforme o HTML de referência.
- [x] Criar cabeçalho executivo e bloco BLUF.
- [x] Criar cards de insights com hierarquia visual.
- [x] Integrar gráficos atuais com títulos conclusivos e takeaways.
- [x] Manter detalhes técnicos separados.
- [x] Mostrar progresso resumido e painel de logs operacionais recolhível.
- [x] Exibir tempo decorrido, cancelamento e limite total de 90 segundos.
- [x] Atualizar relatório HTML autocontido e impressão A4.
- [ ] Validar desktop, projetor, tablet e mobile.

Implementação funcional concluída em 23/11/2026. O frontend usa `POST /api/chat/respond/stream`, preserva a conversa do dataset ativo e apresenta catálogo de dados, catálogo de capacidades, descrição, indisponibilidade ou relatório investigativo conforme a intenção. O relatório investigativo possui somente **Resposta** e **Detalhes técnicos**; a resposta começa pelo BLUF, separa partes não respondidas e não contém próximos passos analíticos. Eventos do orquestrador são transmitidos como logs operacionais seguros, recolhidos por padrão, com tempo decorrido e cancelamento. O HTML baixável é autocontido, sem scripts ou recursos externos, e possui CSS A4. A validação visual por viewport permanece na Fase 7 porque o navegador integrado não conseguiu alcançar o servidor local nesta execução; estrutura responsiva, acessibilidade, fluxo e build foram cobertos por 139 testes Vitest.

**Critério de saída:** o relatório é compreensível sem abrir a aba técnica e pode ser apresentado ou impresso.

### Fase 7 — Validação de apresentação

- [x] Executar as perguntas obrigatórias com datasets aprovados.
- [ ] Validar respostas com pessoa responsável pelo domínio.
- [x] Ensaiar falha e rotação das três chaves com transporte simulado.
- [x] Ensaiar bloqueio controlado quando as três chaves estiverem indisponíveis com transporte simulado.
- [x] Medir tempo total da investigação.
- [x] Congelar exemplos de reserva para a apresentação.

Validação registrada em 23/11/2026 em `VALIDACAO_APRESENTACAO.md`. Catálogo de dados, catálogo de capacidades, descrição e as duas investigações obrigatórias foram aprovados. A investigação individual concluiu em 17,079 segundos; a investigação combinada concluiu em 74,947 segundos, com resposta direta, quatro insights, três lacunas explícitas e confiança baixa. Os dois HTMLs de reserva passaram pela verificação de segurança. Duas chaves reais foram reconhecidas; rotação e bloqueio após falhas sucessivas passaram nos testes de transporte. A única pendência de aceite da fase é a revisão com a pessoa responsável pelo domínio e a conferência visual nos dispositivos da apresentação.

**Critério de saída:** todas as perguntas de aceite geram relatório útil, rastreável e dentro do tempo definido.

## 10. Critérios de aceite globais

O projeto só será considerado pronto quando:

- o chat diferencia perguntas sobre dados, capacidades, descrições e investigações;
- a resposta sobre capacidades reflete o registry e o pacote atual;
- perguntas descritivas não são forçadas a virar testes de hipótese;
- perguntas investigativas geram o relatório completo com rolagem;
- perguntas complementares preservam o contexto sem misturar evidências incompatíveis;
- a resposta direta aparece antes de qualquer tabela ou gráfico;
- o relatório contém conclusões, não apenas métricas;
- cada insight é sustentado por teste ou análise identificável;
- o sistema executa internamente as análises que já possui;
- não existe seção genérica de próximos passos;
- dados ausentes, ferramenta ausente e limite científico são diferenciados;
- o solo não é atribuído a talhão sem vínculo válido;
- o teste estatístico é compatível com o desenho dos dados;
- os gráficos possuem takeaway e fonte;
- o relatório técnico permite auditoria;
- a síntese não inventa valores, causas ou referências;
- a falha de uma ou duas chaves não interrompe a interação quando ainda houver chave saudável;
- a falha das três chaves bloqueia o relatório e permite nova tentativa sem perder o dataset;
- nenhuma chave aparece no frontend, log, trace público ou arquivo baixado;
- nenhum fallback descritivo é apresentado como relatório executivo final.
- o processamento respeita o limite de 90 segundos;
- o progresso permanece visível e os logs operacionais podem ser abertos sob demanda;
- nenhuma cadeia de pensamento, prompt interno ou segredo aparece nos logs;
- partes não respondidas aparecem separadas das conclusões sustentadas;

## 11. Primeira rodada de decisão

Para iniciar a implementação depois deste planejamento, responder primeiro:

1. Quem é o público principal do relatório?
2. Uma página executiva ou relatório com rolagem e versão A4?
3. Podemos alterar o CSV de solo para vincular amostra e talhão?
4. Quais são as três perguntas que obrigatoriamente precisam funcionar na apresentação?
5. Quando todas as chaves falharem, gerar relatório local limitado ou bloquear?
6. Manter identidade marrom ou adotar visual editorial azul nas páginas de relatório?

### Respostas registradas

1. Produtor rural, com compreensão possível por pessoas leigas.
2. Adotar síntese executiva no topo, rolagem para o relatório completo e saída A4 para impressão/PDF.
3. Não existem novos dados de solo além dos arquivos atuais; vínculos inexistentes não serão fabricados.
4. Todas as perguntas devem ser tratadas corretamente, inclusive com negativa fundamentada por falta de dados, ferramenta ou sustentação.
5. Bloquear a entrega quando as três chaves falharem.
6. Preservar a identidade marrom.

## 12. Segunda rodada de decisão

1. O relatório pode apresentar conhecimento agronômico geral como **hipótese explicativa**, claramente separado do que foi comprovado pelos dados?
2. Quando uma pergunta não puder ser respondida, ainda devemos exibir os gráficos e análises parciais relevantes ou mostrar apenas a negativa e a justificativa?
3. Termos como p-valor, intervalo de confiança, Mann–Whitney e Wilcoxon devem aparecer somente nos detalhes técnicos? A recomendação é manter a resposta executiva em linguagem simples.
4. Qual tempo máximo aceitável para gerar o relatório durante a apresentação: 30 segundos, 60 segundos ou até 2 minutos?
5. O relatório deve permitir uma pergunta complementar sobre o mesmo resultado ou cada pergunta sempre inicia uma investigação independente?
6. Quando o sistema encontrar um sinal relevante, ele pode sugerir uma verificação de campo, desde que isso apareça como **recomendação operacional** e não como análise pendente?

### Respostas registradas

1. Sim. Hipóteses agronômicas gerais podem ser apresentadas, claramente separadas do que os dados sustentam.
2. Mostrar análises e gráficos parciais relevantes, indicando de forma explícita qual parte da pergunta não pôde ser respondida e por quê.
3. Sim. Termos e resultados estatísticos detalhados ficam na área técnica; o texto principal permanece acessível.
4. Limite total de 90 segundos, com indicação visível do que está sendo executado e logs disponíveis sob demanda.
5. Sim. Permitir perguntas complementares e ampliar o produto para perguntas descritivas, catálogo de dados e catálogo de capacidades.
6. Sim, dependendo da apresentação. Usar recomendação operacional claramente rotulada, sem tratar verificação de campo como análise pendente.

## 13. Terceira rodada de decisão

1. A classificação da pergunta deve ser automática, com um rótulo visível como “Descrição” ou “Investigação”, permitindo que a pessoa usuária corrija o modo antes da execução?
2. Perguntas gerais sobre agricultura que não dependem dos CSVs devem ser respondidas ou o chat deve permanecer restrito aos dados e às capacidades do FarmLab?
3. A conversa precisa permanecer apenas durante a sessão atual ou deve continuar disponível depois de fechar e abrir o sistema? A persistência exigiria armazenamento além do estado em memória atual.
4. Respostas descritivas também precisam de botão para baixar HTML/PDF ou o download será exclusivo dos relatórios investigativos?
5. Quando houver recomendação de campo, prefere o título “O que observar em campo”, “Recomendação operacional” ou outro nome?
6. No catálogo de capacidades, devemos mostrar somente o que pode ser executado com o pacote atual ou também uma seção separada com análises que o sistema conhece, mas para as quais faltam dados?

