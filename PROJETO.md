# FarmLab Investigator

## 1. Visão do projeto

O **FarmLab Investigator** é uma aplicação web de investigação agrícola. Durante a demonstração, a pessoa usuária importa um pacote de arquivos CSV, escolhe dois talhões comparáveis e pede uma investigação. A aplicação valida os dados, executa cálculos determinísticos e usa a API do Gemini para organizar os resultados em uma explicação escrita, rastreável e apresentada na própria interface.

O projeto não tenta provar causalidade nem substituir uma análise agronômica. Seu objetivo é transformar dados dispersos de uma safra em uma investigação reproduzível, deixando claro:

- o que os dados sustentam;
- quais sinais operacionais merecem atenção;
- quais explicações alternativas continuam possíveis;
- quais dados faltam para uma conclusão mais forte;
- de quais arquivos e funções cada evidência veio.

## 2. Problema que será resolvido

Os dados do FarmLab estão distribuídos entre arquivos de talhões, séries de NDVI e registros de operações. A leitura manual desses arquivos torna lenta a resposta a perguntas como:

> Por que o talhão Grão 4.0 apresentou vigor vegetal inferior ao Grão Convencional?

O FarmLab Investigator transforma essa pergunta em um processo único:

1. receber os arquivos;
2. verificar se eles podem ser relacionados;
3. comparar os talhões nas mesmas datas e operações;
4. gerar evidências numéricas;
5. pedir ao Gemini uma síntese baseada somente nessas evidências;
6. mostrar conclusão, limitações, recomendações e rastreabilidade.

## 3. Experiência da apresentação

A apresentação deve funcionar de forma direta, sem dados pré-carregados escondidos.

1. A aplicação é aberta no navegador.
2. Os cinco CSVs são importados ao vivo.
3. A tela mostra quais arquivos foram reconhecidos, avisos e qualidade do pacote.
4. A pessoa escolhe o talhão analisado, o talhão de referência e o período.
5. A pergunta aparece preenchida, mas pode ser editada.
6. Ao clicar em **Executar investigação**, o harness aciona o Gemini e as ferramentas analíticas permitidas.
7. A aplicação apresenta o resultado sem redirecionar para outro sistema.
8. A primeira área do resultado exibe a **Visão geral do Gemini**, em texto.
9. As áreas seguintes mostram evidências, gráficos, limitações, recomendações e métodos.

## 4. Escopo funcional do MVP

### Incluído

- importação manual de cinco arquivos CSV;
- validação de nomes, colunas, tipos, chaves e disponibilidade;
- descoberta dos quatro talhões da demonstração;
- seleção de talhão analisado e talhão de referência;
- bloqueio ou aviso para comparações incoerentes;
- comparação da trajetória de NDVI em datas pareadas;
- verificação da condição inicial anterior ao plantio;
- comparação de população de plantas;
- cálculo da conformidade entre dose aplicada e configurada;
- harness com Gemini Function Calling e ferramentas analíticas fechadas;
- resposta final estruturada e validada;
- visão geral escrita pelo Gemini;
- rastreabilidade de cada evidência;
- fallback determinístico quando o Gemini falhar;
- download do relatório da investigação em HTML;
- execução local para a apresentação.

### Fora do MVP

- login e gestão de usuários;
- banco de dados permanente;
- múltiplas propriedades e múltiplas safras genéricas;
- chat aberto com acesso irrestrito aos dados;
- SQL ou código Python gerado e executado pelo modelo;
- inferência causal;
- previsão de produtividade;
- processamento dos mapas raster TIFF;
- mapas geoespaciais avançados;
- clima, pragas, combustível, telemetria e alertas;
- agentes múltiplos, filas, microsserviços ou infraestrutura paga;
- publicação pública obrigatória.

## 5. Arquivos de entrada

O pacote mínimo é composto por:

| Arquivo | Uso no MVP |
| --- | --- |
| `fields.csv` | Identificação, nome e centroide dos talhões |
| `ndvi_metadata.csv` | Datas e estatísticas de NDVI por área |
| `LAYER_MAP_PLANTING.csv` | População de plantas e data de plantio |
| `LAYER_MAP_FERTILIZATION.csv` | Dose aplicada, dose configurada e operação |
| `service_orders_fields.csv` | Ligação entre ordem de serviço e talhão |

Os demais arquivos disponíveis ficam reservados para uma evolução.

## 6. Análises da primeira versão

### 6.1 Trajetória de NDVI

Compara o NDVI médio dos dois talhões apenas nas datas válidas presentes nos dois lados. A saída deve informar quantidade de datas pareadas, média de cada talhão, diferença média e série temporal para o gráfico.

### 6.2 Condição inicial

Verifica se já existia diferença de NDVI antes do início do plantio. Se o gap já existia, a conclusão deve tratá-lo como explicação alternativa e impedir qualquer frase causal sobre o manejo.

### 6.3 População de plantas

Calcula a população média ponderada pela área registrada no mapa de plantio para cada talhão e compara os dois resultados.

### 6.4 Conformidade de aplicação

Compara dose aplicada e configurada nas operações de fertilização ou correção. O cálculo é ponderado pela área. A primeira entrega deve priorizar `CALAGEM`; outras operações podem ser exibidas quando existirem para os dois talhões.

## 7. Papel do Gemini

O Gemini faz parte obrigatória do fluxo apresentado, mas não calcula as métricas.

O modelo pode:

- interpretar a pergunta da pessoa usuária;
- escolher, entre ferramentas permitidas, quais análises devem ser executadas;
- organizar os fatos retornados pelas ferramentas;
- redigir a visão geral, os achados, as limitações e as recomendações;
- relacionar cada afirmação aos identificadores das evidências.

O modelo não pode:

- ler os CSVs brutos diretamente;
- executar código livre;
- inventar métricas;
- alterar resultados calculados;
- afirmar causalidade;
- produzir uma evidência sem fonte;
- chamar ferramentas fora da lista definida pelo sistema.

## 8. O que é o harness

O **harness** é a camada de controle entre a interface, os cálculos e o Gemini. Ele não é apenas um prompt. Ele é responsável por:

1. manter o estado da investigação;
2. fornecer ao Gemini somente contexto necessário;
3. expor ferramentas analíticas com parâmetros tipados;
4. validar cada chamada solicitada pelo modelo;
5. executar as funções Python determinísticas;
6. registrar entradas, saídas, fontes, versão e tempo de execução;
7. limitar o número de iterações;
8. solicitar uma resposta final em schema fixo;
9. validar a resposta e rejeitar evidências inexistentes;
10. gerar um relatório por regras se a API falhar.

Portanto, o fluxo correto é:

> Gemini decide o plano e redige; Python calcula; o harness controla e valida.

## 9. Resultado mostrado na interface

A investigação concluída deve conter:

- **Visão geral do Gemini:** título, resumo em dois ou três parágrafos e força da evidência;
- **Achados:** lista ordenada de sinais relevantes;
- **Evidências:** valores, unidades, diferença, quantidade de observações e fonte;
- **Gráfico:** trajetória pareada do NDVI;
- **Limitações:** o que os dados não permitem concluir;
- **Recomendações:** ações proporcionais às evidências;
- **Métodos:** função executada e arquivos utilizados;
- **Rastreamento:** modelo, horário, ferramentas chamadas e identificador da investigação.

## 10. Arquitetura escolhida

### Frontend

- HTML semântico;
- CSS responsivo;
- JavaScript em módulos;
- Vite apenas para desenvolvimento e build;
- Chart.js para o gráfico;
- nenhum framework de interface.

### Backend

- Python;
- FastAPI;
- Pandas e NumPy para leitura e cálculo;
- Pydantic para contratos e validação;
- SDK oficial `google-genai`;
- arquivos e estado mantidos temporariamente em memória durante a sessão;
- nenhuma base de dados.

### Execução da apresentação

O build do frontend será servido pelo próprio FastAPI. Assim, a apresentação usa uma única URL local, por exemplo `http://localhost:8000`, e a chave do Gemini permanece no backend por meio da variável `GEMINI_API_KEY`.

## 11. Custo e privacidade

O projeto deve operar sem custo obrigatório:

- bibliotecas de código aberto;
- execução local;
- API do Gemini configurada em um projeto no free tier;
- sem banco, storage ou hospedagem pagos.

O free tier possui limites de uso que podem mudar. Antes da apresentação, deve ser realizado um teste de conectividade e de cota.

Os CSVs brutos não devem ser enviados ao Gemini. O modelo recebe somente inventário de dados e resultados estruturados das ferramentas. Como dados processados no free tier podem estar sujeitos às condições do provedor, a demonstração deve usar apenas dados acadêmicos ou autorizados.

## 12. Critérios de sucesso

O MVP estará pronto quando:

1. os cinco arquivos puderem ser importados na interface;
2. erros de pacote forem mostrados em linguagem compreensível;
3. os quatro talhões forem reconhecidos corretamente;
4. a comparação Grão 4.0 × Grão Convencional puder ser executada ao vivo;
5. as quatro ferramentas analíticas retornarem resultados testados;
6. o Gemini produzir uma resposta aderente ao schema;
7. cada número mostrado puder ser rastreado até uma ferramenta e um arquivo;
8. a interface exibir uma visão geral escrita, achados, evidências e limitações;
9. uma falha da API não derrubar a aplicação;
10. o fluxo completo puder ser demonstrado em até dois minutos após a seleção dos arquivos.

## 13. Definição de pronto para apresentação

- `GEMINI_API_KEY` configurada e não versionada;
- endpoint de saúde indicando backend e Gemini configurados;
- pacote de demonstração separado e conferido;
- execução completa testada ao menos duas vezes;
- fallback testado com a chave removida;
- relatório baixado e aberto com sucesso;
- nenhuma etapa exige edição de código durante a apresentação;
- interface não contém referências antigas ao Streamlit.

## 14. Documentos que governam o desenvolvimento

- `PROJETO.md`: visão, objetivo e limites do produto;
- `SPEC.md`: comportamento técnico e critérios de aceitação;
- `PIPELINES.md`: fluxos e arquitetura em Mermaid;
- `PLANEJAMENTO_CODEX.md`: ordem de implementação em passos pequenos.

Em caso de conflito, a ordem de prioridade é: `SPEC.md`, `PROJETO.md`, `PIPELINES.md` e `PLANEJAMENTO_CODEX.md`.

