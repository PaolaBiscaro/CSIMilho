# Baseline real — W2.14

Validado em **2026-10-13**, na branch `passo_2`, com os sete CSVs encontrados recursivamente em `/Users/lucashygidio/Downloads/FarmLab/`. Os dados brutos continuam nessa pasta, fora do Git. O manifesto em `backend/tests/fixtures/real_baseline.json` identifica os arquivos por SHA-256 e registra somente contagens e resultados agregados.

## Resultado confirmado

Comparação: **Grão 4.0 (`103144`) − Grão Convencional (`103145`)**, safra completa. CALAGEM é a operação selecionada para conformidade.

| Medida | Resultado auditado | Referência aproximada do SPEC §18 |
| --- | --- | --- |
| Datas NDVI pareadas | **29** | cerca de 33 |
| NDVI médio, alvo / referência | 0,413395055318 / 0,438380259367 | — |
| Gap médio de NDVI | **−0,024985204049** | próximo de −0,025 |
| População, alvo / referência | **61.306,266516 / 63.629,025950 plantas/ha** | 61,3 mil / 63,6 mil |
| CALAGEM, alvo / referência | **57,327136% / 97,500150%** | 58,0% / 97,4% |
| Condição inicial | 15 pares antes de 2025-11-11; gap **−0,024657318494** | heurística de módulo ≥ 0,02 |
| Comparabilidade | permitido, **4/5**; condição inicial distinta | cinco critérios |
| Solo | **8 amostras**, escopo geral do dataset | 8 amostras |

As seis análises e a validação de comparabilidade foram executadas pelo endpoint local de diagnóstico após upload multipart em memória. Não houve chamada a serviço externo nem integração com Gemini.

## Conferência independente e diferenças investigadas

`backend/tests/real_baseline_reference.py` relê os CSVs com a biblioteca padrão, resolve ordens e candidatos diretamente nos arquivos e refaz os vínculos geométricos com Shapely. Não importa os normalizadores, o linker ou funções analíticas da aplicação. Os testes comparam as evidências contra esses cálculos, além de fixar os agregados confirmados.

### NDVI

Cada uma das quatro séries contém 49 observações brutas. Após excluir observações sem pixels válidos, sobram **31 datas no alvo e 29 na referência**, com **29 datas comuns**. O pacote todo passa de 196 para 119 observações válidas; 77 são descartadas por ausência de pixels válidos. Os vínculos foram reconferidos a partir dos bounds em EPSG:3857 e dos centroides dos talhões.

Os testes comparam todas as datas e todos os valores da série, sem interpolação. O gap é negativo em 26 pares e positivo em três. **33 pares não são reproduzíveis neste pacote com os filtros exigidos**; a contagem confirmada é 29, enquanto o gap histórico de aproximadamente −0,025 é reproduzido.

### População e calagem

Os vínculos obedecem ao catálogo de ordens e aos talhões candidatos: ponto representativo coberto ou, quando necessário, maior interseção única de pelo menos 50%. O recálculo independente confirma:

| Auditoria das operações | Plantio | Fertilização |
| --- | ---: | ---: |
| Linhas brutas | 6.751 | 26.616 |
| Ordem não cadastrada | 7 | 10 |
| Ordem sem candidatos | 312 | 7.742 |
| Fora dos candidatos | 392 | 1.136 |
| Geometria inválida | 1 | 29 |
| Atribuídas espacialmente | 6.039 | 17.699 |
| Atribuídas, mas sem valores analíticos válidos | 189 | 0 |
| Linhas normalizadas disponíveis | 5.850 | 17.699 |

O total de **23.738 atribuições espaciais** inclui as 189 linhas posteriormente descartadas por valores inválidos; portanto, não deve ser confundido com as 23.549 linhas normalizadas. Há 9.599 linhas sem atribuição e nenhuma ambiguidade espacial, como no histórico da Semana 1.

A população usa 2.197 linhas no alvo e 1.465 na referência, com `Σ(população × área) / Σ(área)`. A diferença é −3,650471%. Os valores continuam arredondando para 61,3 mil e 63,6 mil, como no SPEC §18.

A calagem usa 5.333 linhas no alvo e 1.088 na referência. As doses aplicadas ponderadas são **917,234179790** e **1.560,002400771 kg/ha**; a dose configurada ponderada é **1.600 kg/ha** nos dois talhões. A razão aplicada/configurada confirma 57,327136% e 97,500150%, diferenças de −0,672864 e +0,100150 ponto percentual frente às aproximações históricas.

Também foram investigadas duas alternativas, sem alterar a implementação: médias simples resultam em 52,216856% / 92,174961%; substituir o ponto representativo pelo centroide resulta em 57,350112% / 97,499024%. Nenhuma reproduz 58,0% / 97,4%. O código e os filtros do protótipo histórico não estavam disponíveis na pasta fornecida, portanto **não é possível atribuir a origem exata dessas aproximações**. O baseline adotado é o cálculo diretamente confirmado nos arquivos sob o contrato atual; nenhuma regra ou tolerância foi afrouxada para imitar o protótipo.

### Condição inicial e solo

As primeiras datas de plantio são 2025-11-13 no alvo e 2025-11-11 na referência. O corte estrito pela menor data deixa 15 pares anteriores. O módulo do gap excede 0,02: a condição inicial é distinta pela heurística operacional, sem alegação de significância estatística ou causalidade.

As oito amostras têm 25 variáveis válidas no Conjunto 1 (200 valores) e 17 no Conjunto 2 (136 valores). Os testes verificam todas as médias, medianas, extremos e quartis diretamente contra os CSVs; os quartis usam interpolação linear, reproduzida por `statistics.quantiles(method="inclusive")`.

As 17 variáveis comuns têm oito pares cada, unidos por `AMOSTRA`, com delta Conjunto 2 menos Conjunto 1. Por exemplo, a mediana dos deltas de MO é −0,965. Todas as oito composições de textura do Conjunto 1 têm soma dentro de 95–105 e foram conferidas antes e depois da normalização para 100%. O Conjunto 2 não fornece textura; seu estado vazio é preservado. Unidades não documentadas permanecem nulas, sem vínculo com talhão, data, profundidade ou classificação agronômica.

## Reproduzir a regressão

Na raiz do projeto:

```sh
cd backend
FARMLAB_REAL_DATA_DIR='/Users/lucashygidio/Downloads/FarmLab' .venv/bin/python -m pytest
```

Para executar apenas o baseline, acrescente `tests/test_real_baseline.py`. A pasta pode ter qualquer organização: os sete nomes esperados são procurados recursivamente. Arquivo ausente, duplicado ou com SHA-256 diferente causa falha quando a variável é definida. Sem a variável, os nove casos reais são explicitamente ignorados; as fixtures artificiais continuam disponíveis na suíte comum.

Contagens e hashes são exatos. Resultados em ponto flutuante usam tolerância **absoluta de 1e-8, sem tolerância relativa**, após concordância entre o cálculo da aplicação e o cálculo independente. Essa margem cobre apenas arredondamento numérico, não diferenças frente ao protótipo. Uma mudança no pacote exige nova auditoria antes de atualizar o manifesto ou os resultados esperados.

## Limites da entrega

A importação retorna `201 / ready_with_warnings`, qualidade 60 e 15 avisos conhecidos. Os descartes estão preservados e nenhuma produtividade confiável foi inferida. A interface continua exibindo gráficos locais demonstrativos, claramente identificados; esta validação não conecta os dados reais à tela de investigação. A Semana 3 não foi iniciada.
