# Dados de demonstração

Mantenha o pacote acadêmico real fora do Git. A importação exige **sete arquivos**:

- `fields.csv`
- `ndvi_metadata.csv`
- `LAYER_MAP_PLANTING.csv`
- `LAYER_MAP_FERTILIZATION.csv`
- `service_orders_fields.csv`
- `service_orders.csv`
- `soil_analysis.csv`

Os testes automatizados usam somente fixtures artificiais pequenas em `backend/tests/fixtures/`.

Na W4.14, o pacote definido para o roteiro foi copiado para `apresentacao-sintetica/`: sete CSVs idênticos aos de `backend/tests/fixtures/manual/`, total de 2.851 bytes. Esses dados são artificiais e devem ser identificados assim durante a apresentação. O pacote privado não está disponível nesta cópia do projeto.

`relatorios-reserva/` contém dois resultados sintéticos baixados no ensaio: `gemini-sintetico.html` e `fallback-sintetico.html`. São arquivos de reserva, não execuções ao vivo. CSVs copiados e relatórios são locais, ignorados pelo Git; em outra máquina, recrie o pacote e gere seus relatórios.

Comandos, pergunta, sequência de cliques, falas e medições estão no [roteiro da demonstração](../ROTEIRO_DEMONSTRACAO.md).
