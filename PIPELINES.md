# Pipelines — FarmLab Investigator

Este documento descreve os fluxos do MVP. Os diagramas usam Mermaid e devem permanecer alinhados ao `SPEC.md`.

## 1. Arquitetura geral

```mermaid
flowchart TB
    U["Pessoa usuária"] --> F["Frontend HTML, CSS e JavaScript"]
    F --> A["API FastAPI"]
    A --> D["Dados temporários da sessão"]
    A --> H["Harness de investigação"]
    H --> T["Ferramentas analíticas em Python"]
    H --> G["API do Gemini"]
    T --> H
    G --> H
    H --> A
    A --> F
```

Responsabilidades:

- o frontend coleta arquivos e escolhas, mostra progresso e renderiza a resposta;
- a API valida requisições e mantém o estado temporário;
- as ferramentas calculam as métricas;
- o Gemini decide quais ferramentas usar e organiza a explicação;
- o harness controla chamadas, valida evidências e produz o trace.

## 2. Fluxo completo da apresentação

```mermaid
sequenceDiagram
    actor U as Pessoa usuária
    participant W as Interface web
    participant A as FastAPI
    participant H as Harness
    participant G as Gemini

    U->>W: Seleciona os cinco CSVs
    W->>A: Envia pacote multipart
    A->>A: Lê, normaliza, liga e valida
    A-->>W: Talhões, pares, avisos e qualidade
    U->>W: Escolhe alvo, referência e pergunta
    W->>A: Solicita investigação
    A->>H: Inicia estado e trace
    H->>G: Envia contexto e ferramentas permitidas
    loop Até concluir ou atingir o limite
        G-->>H: Solicita uma ferramenta tipada
        H->>H: Valida e executa cálculo Python
        H->>G: Devolve evidência estruturada
    end
    H->>G: Solicita síntese no schema final
    G-->>H: Retorna relatório estruturado
    H->>H: Valida números, evidências e linguagem
    H-->>A: Relatório, evidências, gráfico e trace
    A-->>W: Resposta da investigação
    W-->>U: Mostra visão geral e detalhes
```

## 3. Pipeline de importação

```mermaid
flowchart TB
    I["Cinco arquivos selecionados"] --> N["Validar nomes e limites"]
    N --> R["Ler CSV e detectar delimitador"]
    R --> C["Validar colunas e tipos"]
    C --> Z["Normalizar dados"]
    Z --> L["Relacionar ordens, talhões e séries"]
    L --> Q["Calcular qualidade e avisos"]
    Q --> P{"Existe erro impeditivo?"}
    P -- "Sim" --> E["Retornar erros e bloquear"]
    P -- "Não" --> S["Criar dataset temporário"]
    S --> O["Retornar talhões e pares válidos"]
```

### Saída do pipeline

```text
dataset_id
status
quality_score
files[]
fields[]
valid_pairs[]
available_operations[]
warnings[]
errors[]
```

## 4. Relacionamento dos dados

```mermaid
flowchart TB
    F["fields.csv"] --> FI["Catálogo de talhões"]
    SO["service_orders_fields.csv"] --> OM["Ordem de serviço para talhão"]
    P["LAYER_MAP_PLANTING.csv"] --> OM
    A["LAYER_MAP_FERTILIZATION.csv"] --> OM
    N["ndvi_metadata.csv"] --> SM["season_id para talhão por proximidade"]
    FI --> OM
    FI --> SM
    OM --> DS["Dataset normalizado da sessão"]
    SM --> DS
```

Regras de ligação:

- plantio e fertilização usam `Service Order`;
- a ordem é convertida em `idField` por `service_orders_fields.csv`;
- a série NDVI usa o centro dos bounds convertido para longitude e latitude;
- o centro é ligado ao centroide mais próximo em `fields.csv`;
- ligações ambíguas ou acima do limite são rejeitadas.

## 5. Pipeline de NDVI

```mermaid
flowchart TB
    N["Linhas de ndvi_metadata.csv"] --> V["Manter NDVI e pixels válidos"]
    V --> D["Extrair data do filename"]
    D --> M["Ligar season_id ao talhão"]
    M --> G["Agrupar por talhão e data"]
    G --> J["Parear alvo e referência por data"]
    J --> K["Calcular gap alvo menos referência"]
    K --> O["Gerar evidência e série do gráfico"]
```

Não há interpolação. Uma data só entra na comparação se estiver válida nos dois talhões.

## 6. Pipeline de condição inicial

```mermaid
flowchart TB
    P["Dados de plantio"] --> C["Encontrar primeira data de plantio"]
    N["NDVI pareado"] --> B["Filtrar datas anteriores ao corte"]
    C --> B
    B --> Q{"Há pelo menos três pares?"}
    Q -- "Não" --> U["Marcar análise indisponível"]
    Q -- "Sim" --> G["Calcular gap médio inicial"]
    G --> T{"Gap absoluto é pelo menos 0,02?"}
    T -- "Sim" --> L["Registrar condição inicial diferente"]
    T -- "Não" --> S["Registrar condição inicial semelhante"]
```

O limiar é uma regra operacional explícita, não um teste de significância.

## 7. Pipeline de população

```mermaid
flowchart TB
    P["Linhas do mapa de plantio"] --> L["Ligar ordem ao talhão"]
    L --> V["Filtrar área e população válidas"]
    V --> W["Calcular média ponderada por área"]
    W --> C["Comparar alvo e referência"]
    C --> E["Gerar evidência de população"]
```

Fórmula:

```text
Σ(população × área) / Σ(área)
```

## 8. Pipeline de conformidade de aplicação

```mermaid
flowchart TB
    F["Linhas do mapa de fertilização"] --> L["Ligar ordem ao talhão"]
    L --> V["Validar área e doses"]
    V --> O["Agrupar por operação"]
    O --> W["Ponderar doses pela área"]
    W --> C["Calcular aplicada sobre configurada"]
    C --> E["Gerar evidência por operação"]
```

Fórmula:

```text
conformidade = dose_aplicada_ponderada / dose_configurada_ponderada × 100
```

## 9. Pipeline do harness

```mermaid
stateDiagram-v2
    [*] --> Preparando
    Preparando --> Planejando: contexto válido
    Planejando --> ValidandoChamada: Gemini pede ferramenta
    ValidandoChamada --> Executando: chamada permitida
    ValidandoChamada --> Falha: chamada inválida
    Executando --> Registrando: ferramenta conclui
    Registrando --> Planejando: ainda há análise
    Planejando --> Sintetizando: Gemini finaliza plano
    Sintetizando --> ValidandoRelatorio
    ValidandoRelatorio --> Concluido: schema válido
    ValidandoRelatorio --> Reparando: primeira falha
    Reparando --> ValidandoRelatorio
    ValidandoRelatorio --> Fallback: segunda falha
    Planejando --> Fallback: API indisponível
    Fallback --> Concluido
    Falha --> [*]
    Concluido --> [*]
```

## 10. Registro de uma evidência

```mermaid
flowchart LR
    S["Arquivo fonte"] --> T["Ferramenta analítica"]
    T --> E["Evidência com ID"]
    E --> F["Achado do relatório"]
    E --> R["Recomendação"]
```

Cada evidência deve carregar:

- identificador;
- métrica e unidade;
- valor do alvo;
- valor da referência;
- diferença;
- quantidade de observações;
- arquivos fonte;
- método;
- versão da ferramenta.

## 11. Validação da síntese do Gemini

```mermaid
flowchart TB
    G["JSON estruturado do Gemini"] --> S{"Schema válido?"}
    S -- "Não" --> X["Solicitar um reparo"]
    S -- "Sim" --> E{"Evidence IDs existem?"}
    E -- "Não" --> X
    E -- "Sim" --> N{"Números existem nos fatos?"}
    N -- "Não" --> X
    N -- "Sim" --> C{"Há linguagem causal?"}
    C -- "Sim" --> X
    C -- "Não" --> O["Aceitar relatório"]
    X --> R{"Reparo já foi usado?"}
    R -- "Não" --> G
    R -- "Sim" --> F["Gerar fallback determinístico"]
```

## 12. Pipeline de resposta na interface

```mermaid
flowchart TB
    A["Resposta validada da API"] --> V["Visão geral escrita"]
    A --> E["Cards de evidência"]
    A --> G["Gráfico de NDVI"]
    A --> L["Limitações"]
    A --> M["Métodos e trace"]
    V --> H["Relatório HTML"]
    E --> H
    G --> H
    L --> H
    M --> H
```

## 13. Fluxo de erro e fallback

```mermaid
flowchart TB
    I["Investigação iniciada"] --> G{"Gemini disponível?"}
    G -- "Sim" --> R["Executar harness"]
    G -- "Não" --> F["Executar relatório por regras"]
    R --> V{"Relatório válido?"}
    V -- "Sim" --> O["Mostrar resultado Gemini"]
    V -- "Não, após reparo" --> F
    F --> W["Mostrar resultado com aviso de fallback"]
    O --> D["Permitir download"]
    W --> D
```

O fallback é uma proteção para a apresentação. Ele não pode ocultar a falha da API nem se identificar como resposta do Gemini.

## 14. Pipeline de execução local

```mermaid
flowchart TB
    E["Variáveis de ambiente"] --> B["Iniciar FastAPI"]
    F["Build do frontend"] --> B
    B --> H["Verificar health"]
    H --> T["Testar Gemini"]
    T --> D["Abrir aplicação no navegador"]
    D --> P["Executar apresentação"]
```

## 15. Limites entre componentes

| Componente | Pode fazer | Não pode fazer |
| --- | --- | --- |
| Frontend | selecionar arquivos, chamar API, renderizar | acessar chave ou calcular fatos oficiais |
| FastAPI | validar entrada, manter sessão, servir resposta | inventar evidências |
| Ferramentas Python | calcular e retornar evidências | escrever conclusão narrativa livre |
| Gemini | escolher ferramentas e redigir síntese | ler CSV bruto ou executar código |
| Harness | controlar, validar e rastrear | alterar valores calculados |
| Fallback | montar texto por regras | fingir que é Gemini |

