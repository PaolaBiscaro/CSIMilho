# SPEC — FarmLab Investigator

## 1. Status e prioridade

- **Produto:** FarmLab Investigator
- **Versão da especificação:** 1.3
- **Tipo:** MVP acadêmico para demonstração ao vivo
- **Prazo:** quatro semanas
- **Prioridade:** fluxo completo e rastreável antes de amplitude funcional

Esta especificação é normativa. O Codex deve implementar apenas o que está descrito aqui e no planejamento. Funcionalidades adicionais precisam ser registradas como evolução, não incluídas silenciosamente no MVP.

## 2. Objetivo técnico

Construir uma aplicação web com frontend em HTML, CSS e JavaScript e backend em Python/FastAPI. A aplicação recebe sete CSVs, com foco principal na análise descritiva do solo, executa análises determinísticas por meio de ferramentas tipadas e usa a API do Gemini, controlada por um harness, para gerar uma investigação estruturada.

## 3. Princípios obrigatórios

1. **Cálculo fora do LLM:** todo valor numérico vem de uma função Python testada.
2. **LLM com acesso restrito:** o Gemini só acessa ferramentas declaradas pelo harness.
3. **Sem dados brutos no prompt:** CSVs completos nunca são enviados à API.
4. **Saída estruturada:** a resposta final segue um schema Pydantic.
5. **Rastreabilidade:** todo achado referencia uma ou mais evidências existentes.
6. **Sem causalidade:** o sistema usa linguagem descritiva ou associativa.
7. **Falha controlada:** indisponibilidade do Gemini gera fallback, não tela quebrada.
8. **Sem persistência:** arquivos e resultados existem apenas durante a sessão local.
9. **Sem segredo no frontend:** a chave da API permanece no backend.
10. **Escopo fechado:** somente as seis análises definidas entram na primeira versão.
11. **Solo sem vínculo inventado:** enquanto `soil_analysis.csv` não possuir chave de talhão, coordenada, data ou profundidade documentada, seus resultados pertencem ao conjunto de dados como um todo e não a um talhão específico.

## 4. Stack fixada

### 4.1 Frontend

- HTML5 semântico;
- CSS3 responsivo, sem framework CSS;
- JavaScript ES Modules;
- Vite para ambiente de desenvolvimento e build;
- Chart.js para o gráfico de NDVI;
- Vitest para funções puras do frontend, quando aplicável.

#### Identidade visual obrigatória

A cor principal vem da referência visual fornecida e deve ser usada por tokens CSS, nunca repetida de forma dispersa nos componentes:

```css
:root {
  --brown-900: #4f2d18;
  --brown-800: #6b3f22;
  --brown-700: #895129;
  --brown-500: #b5784d;
  --brown-200: #e5cdbb;
  --brown-100: #f1e4da;
  --brown-50: #f8f2ee;
  --canvas: #f7f3ef;
  --paper: #ffffff;
  --ink: #2d2119;
}
```

- `#895129` é a cor primária exata para barra lateral, botões principais, item ativo e série principal dos gráficos;
- `#6b3f22` é o estado hover/foco escuro;
- `#f1e4da` e `#f8f2ee` são fundos de destaque;
- verde, laranja e vermelho continuam reservados para sucesso, aviso e erro;
- texto e controles devem manter contraste acessível.

#### Direção de layout baseada nas referências visuais

A interface deve adotar a linguagem de dashboard das referências fornecidas em 2026-10-07, sem copiar marca, conteúdo financeiro, fotografias ou ícones proprietários:

- aplicação centralizada sobre canvas claro, com moldura ampla e cantos arredondados;
- cabeçalho horizontal branco com marca, navegação em formato de pílula e estado ativo evidente;
- conteúdo organizado em grade de cards brancos, compactos, com hierarquia por tamanho e pouco ruído visual;
- indicadores principais grandes, metadados discretos, bordas suaves e sombras leves;
- visualizações analíticas integradas aos cards, com variedade proporcional ao dado — linhas, barras, distribuições, composição e comparações pareadas — usando a paleta marrom do FarmLab;
- responsividade sem rolagem horizontal em 1440 px, 820 px e 390 px;
- `#895129` permanece a cor primária obrigatória para navegação ativa, botões e séries principais.

As referências orientam composição, densidade e hierarquia. Elas não autorizam alterar a identidade marrom escolhida nem introduzir funcionalidades financeiras.

### 4.2 Backend

- Python 3.12 ou versão compatível disponível;
- FastAPI;
- Uvicorn;
- Pandas;
- NumPy;
- Shapely;
- Pydantic v2;
- `python-multipart`;
- SDK oficial `google-genai`;
- Pytest.

### 4.3 Não usar no MVP

- Streamlit;
- React, Vue, Angular ou Svelte;
- banco de dados;
- LangChain, CrewAI ou framework multiagente;
- Docker como requisito da apresentação;
- serviço pago;
- execução de código gerado pelo LLM.

## 5. Estrutura esperada do repositório

```text
farmlab-investigator/
├── README.md
├── SPEC.md
├── PROJETO.md
├── PIPELINES.md
├── PLANEJAMENTO_CODEX.md
├── .env.example
├── .gitignore
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── src/
│   │   ├── main.js
│   │   ├── api.js
│   │   ├── state.js
│   │   ├── mocks/
│   │   │   └── preview-data.js
│   │   ├── ui/
│   │   │   ├── navigation.js
│   │   │   ├── upload.js
│   │   │   ├── comparison.js
│   │   │   ├── comparison-preview.js
│   │   │   ├── progress.js
│   │   │   ├── results.js
│   │   │   └── investigation-preview.js
│   │   ├── charts/
│   │   │   └── ndvi-chart.js
│   │   └── styles/
│   │       ├── tokens.css
│   │       ├── base.css
│   │       ├── layout.css
│   │       └── components.css
│   └── tests/
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── health.py
│   │   │   ├── datasets.py
│   │   │   └── investigations.py
│   │   ├── data/
│   │   │   ├── contracts.py
│   │   │   ├── loader.py
│   │   │   ├── normalizer.py
│   │   │   ├── linker.py
│   │   │   └── session_store.py
│   │   ├── analytics/
│   │   │   ├── comparability.py
│   │   │   ├── ndvi.py
│   │   │   ├── population.py
│   │   │   ├── application.py
│   │   │   └── soil.py
│   │   ├── harness/
│   │   │   ├── orchestrator.py
│   │   │   ├── prompts.py
│   │   │   ├── registry.py
│   │   │   ├── schemas.py
│   │   │   ├── validators.py
│   │   │   └── fallback.py
│   │   └── reports/
│   │       └── html_report.py
│   └── tests/
│       ├── fixtures/
│       ├── test_loader.py
│       ├── test_linker.py
│       ├── test_analytics.py
│       ├── test_harness.py
│       └── test_api.py
└── demo-data/
    └── README.md
```

Arquivos de dados reais não devem ser versionados sem autorização. O diretório `demo-data/` pode conter apenas amostras acadêmicas autorizadas ou instruções de onde colocá-las localmente.

## 6. Configuração

### 6.1 Variáveis de ambiente

O arquivo `.env.example` deve conter:

```dotenv
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TIMEOUT_SECONDS=45
GEMINI_MAX_TOOL_CALLS=8
MAX_UPLOAD_MB=100
APP_ENV=development
```

Regras:

- `.env` deve estar no `.gitignore`;
- a aplicação deve iniciar sem chave, mas indicar `gemini_configured: false`;
- uma investigação sem chave deve usar fallback e exibir aviso;
- o modelo deve ser configurável, pois disponibilidade e cota podem mudar;
- o código não deve conter uma chave padrão.

## 7. Jornada e estados da interface

### 7.1 Estados globais

```text
EMPTY
UPLOADING
VALIDATING
READY
INVESTIGATING
COMPLETED
ERROR
```

### 7.2 Transições permitidas

- `EMPTY → UPLOADING`: arquivos selecionados;
- `UPLOADING → VALIDATING`: envio recebido pelo backend;
- `VALIDATING → READY`: pacote válido ou válido com avisos;
- `VALIDATING → ERROR`: erro impeditivo;
- `READY → INVESTIGATING`: requisição aceita;
- `INVESTIGATING → COMPLETED`: relatório válido ou fallback válido;
- `INVESTIGATING → ERROR`: erro sem fallback possível;
- `ERROR → EMPTY`: reiniciar pacote;
- `COMPLETED → READY`: iniciar nova comparação com o mesmo pacote.

### 7.3 Telas

Enquanto as etapas analíticas e o harness ainda não estiverem implementados, a navegação pode abrir prévias visuais das telas 2 e 3. Essas prévias devem ser explicitamente rotuladas como **dados demonstrativos**, usar apenas objetos locais de `frontend/src/mocks/` e nunca chamar endpoints de investigação. Navegar pela prévia não altera o estado real do dataset nem marca tarefas `W2.*` ou `W3.*` como concluídas.

#### Tela 1 — Dados

Deve conter:

- área para selecionar os sete CSVs;
- lista de arquivos esperados;
- status individual: ausente, recebido, válido ou inválido;
- resumo da validação;
- talhões reconhecidos;
- avisos não impeditivos;
- botão **Continuar** habilitado somente quando o pacote estiver pronto.

#### Tela 2 — Comparação

Deve conter:

- seleção de talhão analisado;
- seleção de talhão de referência;
- período disponível;
- campo de pergunta, preenchido por padrão;
- pontuação e critérios de comparabilidade;
- análises disponíveis;
- botão **Executar investigação**.

Na prévia visual anterior à Semana 2:

- os selects, período, pergunta e cards de comparabilidade devem ser clicáveis;
- as opções vêm de dados mockados e não representam cálculo real;
- o botão principal abre a prévia de investigação, sem chamar o backend;
- um selo persistente deve informar **Prévia · dados demonstrativos**.

Pergunta padrão:

```text
O que as análises de solo indicam sobre o contexto da área e quais sinais aparecem na execução de correção e no vigor dos talhões {alvo} e {referencia}?
```

#### Estado de processamento

Enquanto a requisição estiver em andamento, mostrar etapas informativas:

1. validando o recorte;
2. planejando a investigação;
3. executando ferramentas analíticas;
4. validando evidências;
5. gerando a visão geral.

Não inventar percentuais exatos. Pode usar indicador indeterminado e destacar a etapa atual.

#### Tela 3 — Investigação

Deve conter as abas:

1. **Visão geral:** resposta escrita pelo Gemini ou fallback identificado;
2. **Solo:** resumo descritivo, comparação entre conjuntos de medição e alertas de qualidade;
3. **Evidências:** cards com valores e fontes;
4. **Gráfico:** série temporal de NDVI pareada;
5. **Métodos:** ferramentas, argumentos normalizados e arquivos usados;
6. **Limitações:** restrições e proibições de conclusão.

Deve haver botões para **Nova comparação** e **Baixar relatório HTML**.

Na prévia visual anterior às Semanas 3 e 4:

- as abas internas devem ser clicáveis e trocar o painel visível;
- cards, números, gráfico ilustrativo, fontes e textos são mockados e devem ser rotulados como demonstração;
- **Nova comparação** retorna à prévia de comparação;
- **Baixar relatório HTML** permanece desabilitado ou identificado como indisponível na prévia;
- nenhum texto mockado pode ser apresentado como resposta do Gemini ou evidência calculada.

#### Direção dos gráficos analíticos finais

O gráfico ilustrativo da prévia não define a qualidade final. Nas Semanas 2 e 4, a investigação deve evoluir para um dashboard analítico mais rico, inspirado na densidade, na hierarquia e na narrativa visual da referência fornecida em 2026-10-07. A identidade marrom permanece obrigatória.

A aba **Solo** é uma área prioritária do produto e deve combinar:

1. cards-resumo com quantidade de amostras, cobertura de valores válidos e alertas de qualidade;
2. gráfico de distribuição por métrica com mínimo, Q1, mediana, Q3 e máximo;
3. comparação visual de Conjunto 1 × Conjunto 2 por barras agrupadas ou gráfico de pontos conectados, sempre exibindo delta e quantidade de pares válidos;
4. composição de areia, silte e argila em barras empilhadas a 100%, com um resumo agregado em rosca somente quando a soma válida permitir;
5. controles para selecionar família e métrica, tooltips com valor, unidade ou **unidade não documentada**, fonte e tamanho da amostra;
6. tabela acessível equivalente aos valores do gráfico e estado vazio quando não houver observações suficientes.

A aba **Gráfico** mantém a trajetória temporal de NDVI com alvo e referência, legenda, datas pareadas e tooltips. Diferentes famílias de dados ou unidades não podem compartilhar o mesmo eixo apenas para preencher espaço visual.

Como `soil_analysis.csv` não possui coordenada, data, profundidade ou vínculo com talhão, a interface não pode criar mapa, linha temporal, camada de profundidade ou comparação por talhão para o solo. Também não pode usar faixas vermelha/amarela/verde de suficiência agronômica sem referência técnica documentada. Todo valor visual deve vir das evidências determinísticas do backend; o frontend apenas seleciona, formata e apresenta.

## 8. Contrato dos arquivos

### 8.1 Regras gerais

- aceitar `.csv` individualmente ou todos de uma vez;
- nomes devem corresponder exatamente aos sete arquivos esperados;
- tamanho total padrão máximo: 100 MB;
- tentar `utf-8-sig`; se necessário, usar `latin-1` com aviso;
- detectar delimitador entre vírgula e ponto e vírgula;
- remover espaços externos dos nomes de colunas;
- representar valores vazios como nulos;
- nunca substituir valor inválido silenciosamente por zero.

Arquivos obrigatórios:

1. `fields.csv`;
2. `ndvi_metadata.csv`;
3. `service_orders.csv`;
4. `service_orders_fields.csv`;
5. `LAYER_MAP_PLANTING.csv`;
6. `LAYER_MAP_FERTILIZATION.csv`;
7. `soil_analysis.csv`.

### 8.2 `fields.csv`

Colunas mínimas:

| Coluna | Tipo normalizado | Regra |
| --- | --- | --- |
| `idField` | string | obrigatória e única |
| `idFarm` | string | obrigatória |
| `fieldName` | string | obrigatória |
| `fieldAreaCentroid` | objeto ou string JSON | longitude e latitude válidas |
| `fieldGeom` | string WKT | polígono ou multipolígono válido |

O backend deve produzir:

```json
{
  "field_id": "103144",
  "farm_id": "25213",
  "name": "Grão 4.0 - 19,3 ha",
  "label": "Grão 4.0",
  "purpose": "grain",
  "management": "digital",
  "centroid": {"longitude": -49.98, "latitude": -22.24},
  "geometry_available": true
}
```

As classificações `purpose` e `management` são regras de demonstração baseadas no nome:

- contém `Grão` → `grain`;
- contém `Silagem` → `silage`;
- contém `4.0` → `digital`;
- contém `Convencional` → `conventional`.

Antes da classificação, aplicar normalização Unicode, remoção de espaços externos e comparação sem diferença entre maiúsculas e minúsculas. O erro conhecido `Convecional` deve ser convertido explicitamente para `Convencional`, preservando o nome original e registrando um aviso `field_name_normalized`.

Se uma classificação não puder ser feita, registrar `unknown` e não inventar.

### 8.3 `ndvi_metadata.csv`

Colunas mínimas:

| Coluna | Tipo | Uso |
| --- | --- | --- |
| `filename` | string | extrair a data `YYYY-MM-DD` |
| `season_id` | string | agrupar a série |
| `crs` | string | validar `EPSG:3857` no conjunto atual |
| `bounds_left` | float | centro do raster |
| `bounds_bottom` | float | centro do raster |
| `bounds_right` | float | centro do raster |
| `bounds_top` | float | centro do raster |
| `b1_valid_pixels` | inteiro | descartar observação sem pixels válidos |
| `b1_mean` | float nulo | NDVI médio |

Regras:

- observação válida exige `b1_valid_pixels > 0` e `b1_mean` numérico;
- NDVI deve estar no intervalo `[-1, 1]`;
- a data é extraída do final do nome do arquivo;
- duplicatas por talhão e data devem ser agregadas por média ponderada por pixels válidos;
- não interpolar datas ausentes no MVP.

#### Ligação entre `season_id` e talhão

Para cada `season_id`:

1. calcular o centro médio dos bounds em EPSG:3857;
2. converter o centro para longitude e latitude WGS84;
3. calcular a distância de Haversine até os centroides de `fields.csv`;
4. ligar ao talhão mais próximo se a distância for menor ou igual a 1.000 metros;
5. impedir a validação se dois `season_id` forem ligados ao mesmo talhão ou se não houver correspondência segura;
6. registrar distância e regra aplicada na rastreabilidade.

Fórmulas de conversão, com raio terrestre `R = 6.378.137` metros:

```text
longitude = (x / R) × 180 / π
latitude  = (2 × atan(exp(y / R)) - π / 2) × 180 / π
```

### 8.4 `service_orders.csv`

Colunas mínimas:

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `idServiceOrder` | string | obrigatória e única |
| `serviceOrderNumber` | string | obrigatória e única no pacote atual |
| `idAgriculturalOperation_agriculturalOperationName` | string | nome da operação |

Regras:

- normalizar números como string canônica, de modo que `1`, `1.0` e espaços externos representem a mesma ordem `1`;
- produzir o mapa `service_order_number → service_order_id`;
- impedir a validação quando o mesmo `serviceOrderNumber` apontar para IDs diferentes;
- preservar o nome da operação para auditoria e conferência, sem usá-lo como substituto da geometria.

### 8.5 `service_orders_fields.csv`

Colunas mínimas:

| Coluna | Tipo |
| --- | --- |
| `idField` | string |
| `idServiceOrder` | string |
| `fieldName` | string |

Produzir um mapa um-para-muitos `service_order_id → set[field_id]`. Uma ordem ligada a vários talhões é uma situação válida e define o conjunto de talhões candidatos; não é erro nem duplicidade.

### 8.6 `LAYER_MAP_PLANTING.csv`

Colunas mínimas:

| Coluna | Tipo |
| --- | --- |
| `Timestamp` | float |
| `Date Time` | datetime |
| `Service Order` | string |
| `Operation` | string |
| `Area - ha` | float |
| `Population - ha` | float |
| `geometry` | string WKT |

Regras:

- interpretar `Service Order` como `serviceOrderNumber`, não como `idServiceOrder`;
- resolver ordem e talhão pelo pipeline espacial da seção 8.9;
- usar somente área positiva e população positiva;
- registrar quantidade de linhas descartadas;
- usar `Date Time` como data operacional e `Timestamp` como fallback.

### 8.7 `LAYER_MAP_FERTILIZATION.csv`

Colunas mínimas:

| Coluna | Tipo |
| --- | --- |
| `Timestamp` | float |
| `Date Time` | datetime |
| `Service Order` | string |
| `operation` | string |
| `Area - ha` | float |
| `AppliedDos - kg/ha` | float |
| `Configured - kg/ha` | float |
| `geometry` | string WKT |

Regras:

- normalizar `operation` para maiúsculas e sem espaços externos;
- interpretar `Service Order` como `serviceOrderNumber`, não como `idServiceOrder`;
- resolver ordem e talhão pelo pipeline espacial da seção 8.9;
- usar somente área positiva, dose aplicada não negativa e dose configurada positiva;
- agrupar por talhão e operação.

### 8.8 `soil_analysis.csv`

O arquivo usa `;` como delimitador e vírgula decimal no pacote atual. Seu escopo é o conjunto de dados completo, pois não há coluna que permita relacionar uma amostra a um talhão. É proibido criar esse vínculo por posição da linha, nome parecido ou suposição.

Colunas mínimas:

| Grupo | Colunas | Regra |
| --- | --- | --- |
| Identificação | `AMOSTRA` | obrigatória, não vazia e única |
| Textura | `ARGILA`, `SILTE`, `AREIA` | numéricas entre 0 e 100 |
| Fertilidade principal | `MO`, `CTC`, `CTCE`, `PHCACL2`, `CA`, `SATCA`, `MG`, `SATMG`, `K`, `SATK`, `P`, `SATB`, `AL`, `SATAL`, `S`, `HAL`, `SB` | numéricas e não negativas; pH entre 0 e 14 |
| Micronutrientes | `B`, `ZN`, `MN`, `CU`, `FE` | opcionais; numéricas e não negativas quando presentes |
| Segundo conjunto | nomes principais com sufixo `_2` | opcional; aplicar as mesmas validações |

Regras:

- normalizar vírgula decimal sem substituir valores inválidos por zero;
- emitir aviso quando `ARGILA + SILTE + AREIA` estiver fora do intervalo de tolerância de 95 a 105;
- chamar as colunas sem sufixo de **Conjunto 1** e as colunas `_2` de **Conjunto 2**;
- não afirmar que `_2` representa profundidade, data ou repetição até existir metadado que documente isso;
- não classificar valores como baixo, adequado ou alto sem unidade e referência agronômica documentadas;
- preservar o nome original da variável e indicar quando a unidade não está disponível;
- gerar avisos para valores nulos, micronutrientes ausentes ou ausência do Conjunto 2;
- guardar as linhas normalizadas no store como `soil_samples`.

`agricultural_inputs.csv` não é obrigatório neste MVP: apesar de conter insumos como calcário e gesso, o pacote atual não fornece uma ligação segura dessas linhas às aplicações espaciais. A execução de calagem e gessagem continua sendo analisada a partir de `LAYER_MAP_FERTILIZATION.csv`.

### 8.9 Ligação das operações aos talhões

O vínculo das linhas de plantio e fertilização deve combinar metadados da ordem e geometria. Não é permitido atribuir diretamente uma ordem compartilhada a apenas um talhão.

Para cada linha de `LAYER_MAP_PLANTING.csv` ou `LAYER_MAP_FERTILIZATION.csv`:

1. normalizar `Service Order` como `serviceOrderNumber`;
2. obter `idServiceOrder` em `service_orders.csv`;
3. obter o conjunto de `idField` candidatos em `service_orders_fields.csv`;
4. interpretar `geometry` e `fieldGeom` como WKT usando Shapely;
5. calcular `representative_point()` da geometria operacional;
6. procurar, entre os candidatos, o talhão cujo polígono cobre esse ponto;
7. se houver exatamente um, atribuir a linha a esse talhão;
8. se não houver cobertura, calcular para cada candidato a razão `área_interseção / área_operação` e aceitar um único maior resultado quando a razão for pelo menos `0,50`;
9. se não houver interseção suficiente, descartar a linha e registrar aviso;
10. se dois candidatos permanecerem empatados ou espacialmente ambíguos, registrar erro impeditivo com a ordem e o índice da linha.

Regras adicionais:

- todas as geometrias dessa ligação devem estar em longitude e latitude compatíveis;
- a razão de interseção é usada apenas para escolher o talhão, não para calcular hectares;
- linhas fora dos quatro talhões do FarmLab são esperadas e devem ser contabilizadas como descartadas, não atribuídas ao talhão mais próximo;
- registrar por arquivo as quantidades `assigned_rows`, `unassigned_rows`, `invalid_geometry_rows` e `ambiguous_rows`;
- se um talhão ficar sem linhas válidas para uma análise, marcar essa análise como indisponível para o talhão;
- se nenhum par possuir os dados mínimos para investigação, bloquear o pacote.

## 9. Validação do pacote

### 9.1 Erros impeditivos

- arquivo obrigatório ausente;
- arquivo duplicado;
- coluna mínima ausente;
- CSV ilegível;
- nenhum talhão reconhecido;
- `serviceOrderNumber` ligado a mais de um `idServiceOrder`;
- geometria espacialmente ambígua entre talhões candidatos;
- geometria ausente ou inválida quando sua ausência impede os dados mínimos de todos os pares;
- nenhuma série de NDVI ligada a talhão;
- nenhuma amostra de solo válida;
- nenhum par comparável disponível.

### 9.2 Avisos

- encoding alternativo utilizado;
- linhas inválidas descartadas;
- nome de talhão normalizado por alias conhecido;
- ordem do mapa sem correspondência em `service_orders.csv`;
- ordem sem talhões candidatos em `service_orders_fields.csv`;
- linha operacional fora dos talhões candidatos;
- geometria inválida descartada sem impedir todas as análises;
- observações NDVI sem pixels válidos;
- operação disponível em apenas um talhão;
- ausência de produtividade confiável;
- poucas datas pareadas;
- distância de ligação espacial acima de 500 m e até 1.000 m.
- soma de argila, silte e areia fora da tolerância de 95 a 105;
- valor ausente ou inválido descartado em `soil_analysis.csv`;
- micronutrientes ou Conjunto 2 ausentes;
- unidade ou significado agronômico não documentado.

### 9.3 Resposta da validação

```json
{
  "dataset_id": "uuid",
  "status": "ready_with_warnings",
  "quality_score": 82,
  "files": [],
  "fields": [],
  "valid_pairs": [],
  "available_operations": [],
  "soil": {
    "sample_count": 0,
    "scope": "dataset",
    "measurement_groups": ["group_1", "group_2"]
  },
  "operation_linkage": {
    "assigned_rows": 0,
    "unassigned_rows": 0,
    "invalid_geometry_rows": 0,
    "ambiguous_rows": 0
  },
  "warnings": [],
  "errors": []
}
```

O `quality_score` é informativo, nunca substitui a lista de erros e avisos. Sua regra deve ser documentada e testada; não pode ser gerado pelo Gemini.

## 10. Pares permitidos e comparabilidade

O MVP aceita pares com a mesma finalidade e manejos diferentes:

- Grão 4.0 × Grão Convencional;
- Silagem 4.0 × Silagem Convencional;
- ordem inversa dos mesmos pares.

### Pontuação de cinco critérios

1. mesma cultura identificada nas operações de plantio;
2. mesma finalidade (`grain` ou `silage`);
3. ao menos cinco datas de NDVI pareadas;
4. plantio e fertilização disponíveis para ambos;
5. condição inicial sem gap relevante.

O critério 5 pode falhar sem bloquear a investigação, mas deve reduzir a força da conclusão. Critérios 1 ou 2 incompatíveis bloqueiam o par.

## 11. Ferramentas analíticas

As ferramentas de comparação recebem IDs e período normalizados. As ferramentas de solo recebem apenas `dataset_id` e filtros de métricas permitidos. Nenhuma ferramenta recebe DataFrames enviados pelo modelo.

### 11.1 `validate_comparison`

Entrada:

```json
{
  "target_field_id": "string",
  "reference_field_id": "string",
  "period": "full_season"
}
```

Saída mínima:

```json
{
  "allowed": true,
  "score": 4,
  "max_score": 5,
  "criteria": [],
  "warnings": [],
  "evidence_id": "EV-COMP-001"
}
```

### 11.2 `compare_ndvi`

Processamento:

1. filtrar os dois talhões e o período;
2. realizar inner join por data;
3. calcular `gap = target_ndvi - reference_ndvi` por data;
4. calcular médias e gap médio;
5. contar sinal e persistência sem preencher ausências.

Saída mínima:

```json
{
  "evidence_id": "EV-NDVI-001",
  "paired_dates": 33,
  "target_mean": 0.0,
  "reference_mean": 0.0,
  "mean_gap": -0.025,
  "unit": "ndvi",
  "series": [],
  "source_files": ["ndvi_metadata.csv"],
  "method": "inner join por data e média do gap"
}
```

### 11.3 `check_initial_condition`

Definição:

- data de corte = menor primeira data de plantio entre os dois talhões;
- usar pares NDVI anteriores à data de corte;
- exigir ao menos três pares;
- calcular gap médio inicial;
- considerar condição inicial diferente quando `abs(gap_medio_inicial) >= 0.02`.

O limiar `0.02` é uma regra operacional do MVP, não um teste estatístico. Isso deve aparecer nos métodos.

Saída mínima:

```json
{
  "evidence_id": "EV-INITIAL-001",
  "available": true,
  "cutoff_date": "YYYY-MM-DD",
  "paired_dates": 0,
  "mean_gap": 0.0,
  "threshold": 0.02,
  "different": true,
  "source_files": ["ndvi_metadata.csv", "LAYER_MAP_PLANTING.csv"]
}
```

### 11.4 `compare_population`

Para cada talhão:

```text
populacao_ponderada = Σ(populacao_i × area_i) / Σ(area_i)
```

Depois:

```text
diferenca_percentual = (alvo - referencia) / referencia × 100
```

Saída mínima:

```json
{
  "evidence_id": "EV-POP-001",
  "target_population_per_ha": 61304,
  "reference_population_per_ha": 63611,
  "difference_percent": -3.6,
  "unit": "plants/ha",
  "source_files": ["LAYER_MAP_PLANTING.csv", "service_orders.csv", "service_orders_fields.csv", "fields.csv"]
}
```

### 11.5 `application_compliance`

Para cada talhão e operação:

```text
dose_aplicada_ponderada = Σ(dose_aplicada_i × area_i) / Σ(area_i)
dose_configurada_ponderada = Σ(dose_configurada_i × area_i) / Σ(area_i)
conformidade = dose_aplicada_ponderada / dose_configurada_ponderada × 100
```

Saída mínima:

```json
{
  "evidence_id": "EV-APP-CALAGEM-001",
  "operation": "CALAGEM",
  "target_compliance_percent": 58.0,
  "reference_compliance_percent": 97.4,
  "source_files": ["LAYER_MAP_FERTILIZATION.csv", "service_orders.csv", "service_orders_fields.csv", "fields.csv"]
}
```

Não limitar artificialmente a conformidade a 100%; valores acima de 100% representam sobreaplicação e devem ser reportados.

### 11.6 `summarize_soil_analysis`

Resume o contexto do solo sem aplicar faixas agronômicas não documentadas. Deve calcular, por variável disponível, contagem válida, média, mediana, mínimo, máximo, primeiro quartil e terceiro quartil. O retorno deve separar textura, acidez/fertilidade, bases e micronutrientes.

Entrada:

```json
{
  "dataset_id": "uuid",
  "measurement_group": "group_1"
}
```

Saída mínima:

```json
{
  "evidence_id": "EV-SOIL-SUMMARY-001",
  "scope": "dataset",
  "measurement_group": "group_1",
  "sample_count": 8,
  "metrics": [
    {
      "name": "PHCACL2",
      "unit": null,
      "valid_n": 8,
      "mean": 0.0,
      "median": 0.0,
      "min": 0.0,
      "max": 0.0,
      "q1": 0.0,
      "q3": 0.0
    }
  ],
  "warnings": [],
  "source_files": ["soil_analysis.csv"],
  "method": "estatísticas descritivas sem classificação agronômica"
}
```

### 11.7 `compare_soil_measurement_groups`

Compara apenas variáveis que existam nos dois conjuntos. O cálculo é pareado por `AMOSTRA` e usa `delta = Conjunto 2 - Conjunto 1`. Deve retornar deltas por amostra, mediana do delta e quantidade de pares válidos. A apresentação usa os rótulos **Conjunto 1** e **Conjunto 2**, nunca profundidades presumidas.

Entrada:

```json
{
  "dataset_id": "uuid",
  "metrics": ["PHCACL2", "MO", "CTC", "AL", "SATB"]
}
```

Saída mínima:

```json
{
  "evidence_id": "EV-SOIL-GROUPS-001",
  "scope": "dataset",
  "comparison": "group_2_minus_group_1",
  "metrics": [],
  "source_files": ["soil_analysis.csv"],
  "method": "comparação pareada por AMOSTRA",
  "limitations": ["O significado do sufixo _2 não está documentado."]
}
```

Nenhuma das duas ferramentas pode associar a análise de solo a `target_field_id` ou `reference_field_id` enquanto o arquivo não fornecer uma chave segura.

## 12. Harness do Gemini

### 12.1 Componentes

- `orchestrator.py`: controla o ciclo da investigação;
- `registry.py`: lista fechada de ferramentas e schemas;
- `prompts.py`: instruções do sistema e contexto;
- `schemas.py`: modelos de entrada, evidência, trace e relatório;
- `validators.py`: valida chamadas e resposta final;
- `fallback.py`: produz relatório sem Gemini.

### 12.2 Contexto enviado ao modelo

O primeiro pedido ao Gemini contém somente:

- pergunta da pessoa usuária;
- nomes e IDs normalizados dos dois talhões;
- período;
- inventário das fontes disponíveis;
- avisos de qualidade;
- regras de linguagem e conclusão;
- declarações das ferramentas.

Não incluir linhas dos CSVs.

### 12.3 Loop de ferramentas

1. iniciar um trace com `trace_id`;
2. enviar contexto e ferramentas ao Gemini;
3. receber uma chamada de função ou pedido de finalização;
4. verificar se a ferramenta está no allowlist;
5. validar argumentos com Pydantic;
6. garantir que os IDs pertencem ao dataset da sessão;
7. executar a função Python;
8. validar o retorno da ferramenta;
9. registrar a chamada e devolver o resultado ao Gemini;
10. repetir até finalizar ou atingir oito chamadas;
11. exigir que `validate_comparison` tenha sido executada;
12. se o par for inválido, interromper antes das demais ferramentas.

O harness deve impedir:

- nomes de ferramenta desconhecidos;
- argumentos adicionais não previstos;
- troca de talhões no meio da investigação;
- mais de oito chamadas;
- repetição idêntica da mesma ferramenta;
- acesso a caminhos de arquivo;
- instruções da pergunta que tentem alterar as regras do sistema.

### 12.4 Síntese estruturada

Após as ferramentas, realizar uma chamada de síntese com os resultados acumulados e exigir o seguinte schema lógico:

```json
{
  "overview": {
    "headline": "string",
    "summary": "string",
    "evidence_strength": "weak | moderate | strong"
  },
  "findings": [
    {
      "title": "string",
      "explanation": "string",
      "evidence_ids": ["EV-..."]
    }
  ],
  "limitations": [
    {
      "title": "string",
      "explanation": "string",
      "rule_id": "string"
    }
  ],
  "recommendations": [
    {
      "action": "string",
      "reason": "string",
      "evidence_ids": ["EV-..."]
    }
  ]
}
```

### 12.5 Validação da resposta

Rejeitar a resposta quando:

- não cumprir o schema;
- usar `evidence_id` inexistente;
- omitir limitações obrigatórias;
- trouxer afirmação causal;
- incluir número não presente nas evidências;
- contradizer o sinal ou a unidade de uma evidência;
- recomendar ação sem relação com evidência.

Permitir uma única tentativa de reparo, enviando apenas os erros de validação e os fatos estruturados. Se a segunda resposta falhar, usar fallback.

### 12.6 Regras de linguagem

Termos permitidos:

- `associado a`;
- `compatível com`;
- `os dados indicam`;
- `a comparação mostra`;
- `não é possível concluir`.

Termos proibidos quando descrevem o manejo:

- `causou`;
- `provou`;
- `foi responsável por`;
- `garantiu`;
- `levou a`, quando usado causalmente.

### 12.7 Fallback

O fallback deve usar os mesmos objetos de evidência e templates locais. Deve gerar:

- título;
- resumo;
- achados ordenados;
- limitações obrigatórias;
- recomendações básicas;
- identificação `generated_by: deterministic_fallback`.

O fallback não deve fingir que veio do Gemini.

## 13. Rastreabilidade

Cada chamada deve registrar:

```json
{
  "trace_id": "uuid",
  "sequence": 1,
  "tool": "compare_ndvi",
  "arguments": {},
  "result_evidence_ids": ["EV-NDVI-001"],
  "source_files": ["ndvi_metadata.csv"],
  "tool_version": "1.0.0",
  "started_at": "ISO-8601",
  "duration_ms": 0,
  "status": "success"
}
```

O relatório final deve registrar:

- `investigation_id`;
- `trace_id`;
- `dataset_id`;
- modelo configurado;
- `generated_by: gemini | deterministic_fallback`;
- data e hora;
- ferramentas executadas;
- evidências utilizadas;
- avisos do pacote.

Prompts completos, chave da API e dados brutos não devem aparecer na interface nem no relatório baixado.

## 14. API HTTP

### 14.1 `GET /api/health`

Resposta:

```json
{
  "status": "ok",
  "gemini_configured": true,
  "model": "configured-model",
  "version": "1.0.0"
}
```

Não realizar uma chamada cobrada apenas para o health check. Um botão separado **Testar Gemini** pode fazer uma requisição mínima antes da apresentação.

### 14.2 `POST /api/gemini/test`

Executa uma chamada mínima e retorna sucesso, latência e modelo. Deve ter timeout e mensagem clara para `401`, `403`, `429` e indisponibilidade.

### 14.3 `POST /api/datasets`

- conteúdo: `multipart/form-data`;
- campo repetido: `files`;
- recebe exatamente os arquivos esperados;
- retorna o contrato de validação da seção 9.3;
- status HTTP `201` para pacote pronto, `422` para erro de conteúdo e `413` para limite excedido.

### 14.4 `POST /api/investigations`

Entrada:

```json
{
  "dataset_id": "uuid",
  "target_field_id": "string",
  "reference_field_id": "string",
  "period": "full_season",
  "question": "string"
}
```

Regras:

- pergunta entre 10 e 500 caracteres;
- uma investigação por vez no frontend;
- timeout total configurável;
- resposta síncrona para reduzir complexidade do MVP;
- o frontend mostra progresso indeterminado enquanto aguarda.

Saída:

```json
{
  "investigation_id": "uuid",
  "status": "completed",
  "generated_by": "gemini",
  "report": {},
  "evidence": [],
  "chart_data": {},
  "trace": {},
  "warnings": []
}
```

### 14.5 `GET /api/investigations/{investigation_id}/report`

Retorna um arquivo HTML autocontido. O HTML deve escapar todo texto externo e não executar scripts do Gemini.

## 15. Segurança e tratamento de conteúdo

- nunca usar `innerHTML` com conteúdo vindo da API;
- preencher textos com `textContent` ou criação explícita de elementos;
- limitar extensões e tamanho de upload;
- não confiar em MIME type enviado pelo navegador;
- validar todos os números finitos;
- não registrar a chave;
- não retornar stack trace ao frontend;
- configurar CORS somente para origens locais de desenvolvimento;
- limpar os dados temporários ao reiniciar o servidor;
- impedir path traversal usando somente nomes esperados;
- tratar a pergunta como dado não confiável dentro do prompt;
- manter as instruções do sistema fora do controle da pessoa usuária.

## 16. Resiliência para apresentação

### Antes da apresentação

- executar `GET /api/health`;
- executar `POST /api/gemini/test`;
- confirmar que o modelo configurado responde;
- manter a chave válida no ambiente local;
- testar o pacote exato da demonstração;
- manter o fallback habilitado;
- não depender de deploy que possa estar adormecido.

### Erros visíveis

| Situação | Comportamento |
| --- | --- |
| Arquivo ausente | indicar o nome e bloquear continuação |
| Coluna ausente | indicar arquivo e coluna |
| Par incompatível | explicar qual critério falhou |
| Gemini sem chave | executar fallback e mostrar aviso |
| Rate limit `429` | uma repetição com espera curta; depois fallback |
| Timeout | fallback e aviso de indisponibilidade |
| Saída inválida | uma tentativa de reparo; depois fallback |
| Erro de cálculo | interromper e não pedir ao Gemini para preencher |

## 17. Testes obrigatórios

### 17.1 Dados

- leitura de CSV com `;`;
- leitura de CSV com `,`;
- encoding alternativo;
- coluna ausente;
- valor numérico inválido;
- data inválida;
- normalização `Convecional → Convencional` com aviso;
- conversão de `serviceOrderNumber` para `idServiceOrder`;
- ordem de serviço ligada validamente a dois ou mais talhões candidatos;
- rejeição de `serviceOrderNumber` duplicado com IDs diferentes;
- atribuição espacial pelo ponto representativo;
- fallback por maior interseção com razão mínima de 0,50;
- descarte com aviso de linha fora dos talhões candidatos;
- rejeição de empate espacial real;
- ligação espacial de `season_id`;
- rejeição de ligação ambígua.
- leitura de `soil_analysis.csv` com `;`, BOM e vírgula decimal;
- rejeição de `AMOSTRA` duplicada;
- validação de textura, pH e valores não negativos;
- aviso para soma de textura fora de 95 a 105;
- preservação explícita de Conjunto 1 e Conjunto 2 sem inferir profundidade.

### 17.2 Analytics

- inner join de datas NDVI;
- ausência não interpolada;
- gap com sinal correto;
- condição inicial com três ou mais pares;
- condição inicial indisponível com menos de três pares;
- população ponderada por área;
- conformidade ponderada por área;
- conformidade acima de 100%;
- divisão por zero impedida.
- estatísticas descritivas do solo calculadas sobre valores válidos;
- comparação de Conjunto 2 menos Conjunto 1 pareada por `AMOSTRA`;
- ausência de vínculo entre solo e talhão mantida no resultado e no texto.

### 17.3 Harness

- ferramenta desconhecida bloqueada;
- argumentos extras bloqueados;
- IDs fora do dataset bloqueados;
- repetição idêntica bloqueada;
- limite de chamadas aplicado;
- evidência inexistente rejeitada;
- número inventado rejeitado;
- termo causal rejeitado;
- reparo aceito quando válido;
- fallback ativado quando necessário.

### 17.4 API e frontend

- upload completo;
- upload incompleto;
- fluxo até relatório;
- mensagem de erro acessível;
- botão desabilitado durante requisição;
- renderização sem `innerHTML` de texto externo;
- gráfico destruído e recriado ao trocar resultado;
- gráficos de solo usam os mesmos valores, unidades, contagens e deltas das evidências determinísticas;
- distribuição de solo apresenta mínimo, quartis, mediana e máximo sem inventar observações;
- composição de textura só aparece para linhas válidas e total compatível com 100%;
- ausência de coordenada, data e profundidade impede mapa, tendência temporal e camadas de solo;
- cada visualização possui tabela ou resumo textual acessível equivalente;
- download do relatório.

## 18. Critérios de aceitação do cenário principal

Dado o pacote acadêmico de sete arquivos usado no protótipo:

1. os quatro talhões devem ser reconhecidos;
2. `Grão Convecional` deve ser apresentado internamente como `Grão Convencional`, com aviso de normalização;
3. ordens compartilhadas por mais de um talhão devem ser aceitas como relação válida;
4. as linhas de plantio e fertilização devem ser atribuídas espacialmente a um único talhão;
5. Grão 4.0 e Grão Convencional devem formar par válido;
6. a trajetória deve usar somente datas presentes nos dois talhões;
7. o gap deve ser apresentado como `alvo - referência`;
8. a condição pré-plantio deve aparecer como limitação quando diferente;
9. população e conformidade devem ser calculadas somente das linhas espacialmente atribuídas aos talhões corretos;
10. as oito amostras válidas de `soil_analysis.csv` devem ser reconhecidas no escopo geral do dataset;
11. Conjunto 1 e Conjunto 2 devem ser comparados sem dizer que representam profundidades;
12. nenhuma amostra de solo deve ser atribuída a um talhão;
13. o Gemini deve receber os objetos de evidência, não os CSVs;
14. a visão geral deve citar evidências válidas;
15. o texto deve impedir conclusão de que agricultura 4.0 causou menor produtividade ou que o solo explica um talhão específico;
16. o relatório deve continuar disponível se o Gemini falhar.

Valores conhecidos do protótipo podem ser usados como teste de regressão aproximado, nunca como valores hardcoded da interface:

- cerca de 33 datas NDVI pareadas;
- gap médio de NDVI próximo de `-0,025` para Grão 4.0 contra Grão Convencional;
- população próxima de `61,3 mil/ha` contra `63,6 mil/ha`;
- conformidade de calagem próxima de `58,0%` contra `97,4%`.

As tolerâncias devem ser definidas depois que a implementação de referência for validada diretamente nos arquivos.

## 19. Definição de pronto por tarefa

Uma tarefa só pode ser marcada como concluída quando:

- o código correspondente foi implementado;
- os critérios daquela tarefa foram verificados;
- testes relevantes passam;
- não foram adicionadas dependências sem necessidade;
- documentação afetada foi atualizada;
- não há segredo ou dado bruto adicionado ao Git;
- o Codex informa arquivos alterados, comandos executados e limitações restantes.

## 20. Referências técnicas

- Gemini Function Calling: <https://ai.google.dev/gemini-api/docs/function-calling>
- Gemini Structured Outputs: <https://ai.google.dev/gemini-api/docs/structured-output>
- Chaves da Gemini API: <https://ai.google.dev/gemini-api/docs/api-key>
- SDKs da Gemini API: <https://ai.google.dev/gemini-api/docs/libraries>
- Vite: <https://vite.dev/guide/>
- FastAPI: <https://fastapi.tiangolo.com/>
- Pydantic: <https://docs.pydantic.dev/latest/>
- Chart.js: <https://www.chartjs.org/docs/latest/>
