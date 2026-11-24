# Validação para apresentação

Data do registro: 23/11/2026.

## Escopo validado

As validações usam somente os sete CSVs sintéticos aprovados em `backend/tests/fixtures/manual`. O pacote foi aceito com status `ready_with_warnings`, qualidade 85/100 e sem uso de dados externos.

## Cenários executados

| Cenário | Tipo | Resultado | Tempo |
| --- | --- | --- | ---: |
| Quais dados estão disponíveis? | catálogo | aprovado | 0,005 s |
| O que a ferramenta consegue analisar? | catálogo de capacidades | aprovado | 0,020 s |
| Descrição do vigor do Grão 4.0 | descritiva | aprovado | 0,020 s |
| Mudanças bruscas no NDVI do Grão 4.0 | investigação de talhão único | aprovado, conclusão indicativa e limitação de dados explícita | 17,079 s |
| Solo, correção e vigor dos dois talhões | investigação combinada | aprovado; resposta parcial com as lacunas identificadas | 74,947 s |

Os cenários investigativos geraram `demo-data/relatorios-reserva/phase7-single_field_temporal.html` e `demo-data/relatorios-reserva/phase7-soil_operations_vigor.html`. Os dois arquivos são autocontidos e não contêm scripts, URLs externas, chaves ou seção de próximos passos. O relatório combinado contém resposta direta, quatro insights, três partes não respondidas explicitamente e confiança baixa coerente com a cobertura do pacote.

## Backend e rotação de chaves

- 60 testes focados em relatório executivo, entrega pelo chat e transporte Gemini passaram em 23/11/2026.
- A suíte do transporte cobre até três chaves, falha sucessiva das chaves 1 e 2, sucesso com a chave 3, cooldown, desativação por credencial, deadline compartilhado e bloqueio seguro quando todas falham.
- Duas chaves reais foram reconhecidas na configuração em 23/11/2026. A rotação com falhas sucessivas continua comprovada pelo transporte simulado; o failover real não foi provocado deliberadamente para não invalidar ou consumir as credenciais.
- O tempo total permitido está configurado em 90 segundos por interação.
- Antes da aprovação, as tentativas rejeitadas por cota, número sem evidência, limite de schema e linguagem causal foram bloqueadas sem publicar relatórios incompletos. Após o fortalecimento das instruções de reparo, a execução final foi aprovada em 74,947 segundos.

## Correções encontradas durante o ensaio

1. O schema completo do Pydantic excedia as restrições aceitas pelo Gemini. Foi criada uma projeção compatível para o provedor, mantendo a validação local completa após a resposta.
2. Números que pertencem ao nome do talhão, como “Grão 4.0”, eram confundidos com alegações numéricas. A validação agora reconhece números presentes na pergunta e nos identificadores selecionados.
3. Recomendações de campo não conseguiam repetir um valor já comprovado em outra evidência. A validação agora permite essa repetição somente quando o número existe nas evidências validadas.

## Pendências antes da banca

- A terceira chave permanece opcional e pode ser adicionada depois, sem mudança de código.
- Se for desejado ensaiar o failover real, usar uma credencial de teste controlada; não invalidar as chaves da apresentação.
- Revisar as respostas com a pessoa responsável pelo domínio agronômico.
- Conferir visualmente desktop, projetor, tablet e celular.

Nenhuma dessas pendências autoriza substituir um relatório bloqueado por texto local. Se o Gemini ficar indisponível, a interface deve informar a falha e permitir nova tentativa com o dataset preservado.
