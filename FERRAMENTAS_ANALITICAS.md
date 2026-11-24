# Mapa de ferramentas analíticas do harness

## Objetivo

A pergunta livre deve aprofundar a investigação além dos gráficos padrão. O
Gemini escolhe entre ferramentas fechadas, mas todo cálculo continua sendo feito
por funções Python tipadas, testadas e rastreáveis. Quando o pedido não estiver
coberto, o relatório informa o método ou o dado que ainda falta.

O harness usa dois tipos de bloqueio, que não devem ser misturados:

- **Ferramenta ausente:** os dados podem até existir, mas não há um módulo
  determinístico, validado e registrado para executar o método solicitado.
- **Dados ausentes:** a ferramenta existe, mas faltam valores válidos, cobertura
  mínima ou o vínculo necessário entre talhão, data, operação ou amostra.

Uma análise opcional bloqueada por dados não encerra a investigação. A chamada
fica registrada com erro, a limitação informa exatamente os dados necessários e
o orquestrador continua com os demais módulos relevantes. Falhas de validação,
infraestrutura ou resultado inválido continuam encerrando o fluxo por segurança.

Cada resposta possui dois níveis:

1. **Explicação em linguagem simples:** conclusão direta, significado prático e
   incerteza, sem exigir conhecimento estatístico.
2. **Detalhamento técnico:** método, hipótese, unidade observacional, valores,
   evidências, fontes, pressupostos e limitações.

## Critérios para uma nova ferramenta

Uma ferramenta só entra no registro quando tiver:

- pergunta analítica claramente definida;
- fonte e unidade observacional identificadas;
- argumentos e evidência de saída tipados;
- método determinístico, sem código gerado pelo modelo;
- condições mínimas de amostra e tratamento de ausências;
- interpretação que não confunda associação, significância e causalidade;
- fallback, validação numérica, trace e testes de regressão.

## Prioridade recomendada

### Prioridade imediata — dados atuais

| Ferramenta proposta | Perguntas que atende | Dados e método | Proteções obrigatórias |
|---|---|---|---|
| `test_ndvi_paired_difference` | “A diferença de NDVI é compatível com variação aleatória?” | NDVI pareado pelas mesmas datas; teste de permutação pareado ou Wilcoxon sobre os gaps | hipótese bilateral por padrão; mínimo de pares; tratamento explícito de zeros/empates; alerta de dependência temporal; p-valor não prova relevância agronômica |
| `estimate_ndvi_effect` | “Qual é o tamanho e a incerteza da diferença?” | gap por data; mediana ou média pareada, intervalo por reamostragem e direção | informar estimativa e intervalo, não apenas p-valor; semente fixa; não converter NDVI em produtividade |
| `test_soil_group_difference` | “Os conjuntos de solo diferem para esta variável?” | pares por `AMOSTRA`; teste pareado por métrica | manter os nomes Conjunto 1/Conjunto 2; não presumir profundidade ou tempo; corrigir múltiplos testes; bloquear interpretação agronômica sem unidade/referência |
| `summarize_ndvi_periods` | “A diferença ocorre antes, durante ou depois de determinada fase?” | datas pareadas segmentadas por períodos documentados | segmentos definidos por dados, não inventados pelo modelo; mínimo de observações por período; sem inferência causal |

O primeiro módulo recomendado é `test_ndvi_paired_difference`: o backend já
possui o pareamento por data e 29 pares no pacote de apresentação. A documentação
do SciPy descreve o Wilcoxon para amostras relacionadas e ressalta as hipóteses
sobre as diferenças; `permutation_test` oferece permutação que preserva pares.

### Segunda prioridade — aprofundamento descritivo

| Ferramenta proposta | Perguntas que atende | Dados e método | Proteções obrigatórias |
|---|---|---|---|
| `describe_application_variability` | “A aplicação foi uniforme?” | distribuição ponderada por área, quantis, dispersão e cobertura por talhão | não tratar pontos da máquina como repetições independentes; separar uniformidade de adequação agronômica |
| `describe_population_variability` | “A população registrada foi estável dentro do talhão?” | distribuição e cobertura dos registros válidos de plantio | mostrar descartes e cobertura; não inferir emergência ou produtividade |
| `detect_ndvi_anomalies` | “Há datas atípicas ou mudanças abruptas?” | série pareada, diferenças entre datas e regras robustas de anomalia | exigir cobertura temporal; registrar limiar; anomalia não é diagnóstico de causa |
| `correlate_linked_metrics` | “Duas métricas variam juntas?” | correlação de Spearman em observações realmente ligadas | bloquear quando houver apenas dois valores agregados por talhão; exigir pares suficientes; correlação não implica causa |

A correlação de Spearman mede associação monotônica, mas seu p-valor assintótico
exige amostra grande; para amostras menores, o plano deve usar permutação ou
apresentar apenas a estimativa com limitação explícita.

### Dependem de novos dados ou desenho

| Pedido | O que falta |
|---|---|
| produtividade, sacas ou rendimento | produtividade confiável vinculada ao talhão e módulo de comparação |
| lucro, custo ou retorno | custos, preços, operações e regra econômica documentada |
| clima, chuva ou temperatura | série meteorológica ligada por local e data |
| umidade ou irrigação | sensores/registro de irrigação com vínculo espacial e temporal |
| pragas e doenças | eventos e severidade ligados ao talhão e período |
| mapas e zonas de manejo | observações georreferenciadas na granularidade necessária e módulo espacial |
| previsão | histórico suficiente, divisão temporal de treino/validação e métricas de erro |
| atribuição de resultado ao manejo | desenho experimental ou quase experimental e variáveis de controle |

## Roteamento do orquestrador

1. Classificar a pergunta pelas capacidades conhecidas.
2. Separar partes executáveis de partes sem ferramenta ou dados.
3. Chamar somente as ferramentas pertinentes; nunca executar todos os módulos por
   padrão.
4. Produzir evidências determinísticas e validar valores, unidades e fontes.
5. Na resposta simples, explicar a conclusão e a incerteza.
6. Na parte técnica, apresentar método, resultados e limitações.
7. Para uma lacuna, classificar `missing_tooling` ou `missing_data`, declarar o
   módulo ou as informações necessárias e não fabricar cálculo, p-valor,
   diagnóstico ou conclusão.

## Ordem de implementação sugerida

1. `test_ndvi_paired_difference`.
2. `estimate_ndvi_effect`.
3. `test_soil_group_difference`, com correção de múltiplos testes.
4. `summarize_ndvi_periods`.
5. variabilidade de aplicação e população.
6. correlação apenas depois de existir uma chave observacional comum.

## Referências técnicas

- [SciPy — Wilcoxon para amostras pareadas](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html)
- [SciPy — testes de permutação](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html)
- [SciPy — correlação de Spearman](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html)
- [statsmodels — correção de múltiplos testes](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html)

