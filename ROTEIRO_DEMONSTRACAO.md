# Roteiro de demonstração do FarmLab

Este roteiro usa exclusivamente o pacote sintético aprovado em `demo-data/apresentacao-sintetica` ou, se essa cópia não existir, os sete arquivos de `backend/tests/fixtures/manual`. A apresentação demonstra o funcionamento da ferramenta; os resultados não representam uma área agrícola real.

## Preparação antes da apresentação

1. Configure de uma a três chaves no arquivo `.env` do backend:

```text
GEMINI_API_KEY=chave_principal
GEMINI_API_KEY_2=chave_reserva_opcional
GEMINI_API_KEY_3=chave_reserva_opcional
GEMINI_TIMEOUT_SECONDS=90
```

As chaves 2 e 3 são opcionais, mas recomendadas para a apresentação. O backend troca de chave durante qualquer interação que falhar por credencial, cota, rede ou indisponibilidade. Nenhuma chave é enviada ao navegador ou gravada no relatório.

2. Em um PowerShell, compile o frontend e inicie o backend:

```powershell
cd C:\Users\heloi\pasta-centralizada-heloisa\faculdade\fabrica-projetos-ageis\projeto-farmlab\frontend
npm run build
cd ..\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

3. Abra `http://127.0.0.1:8000/` e confirme que o backend está conectado.
4. Use **Testar Gemini**. Esse teste verifica a conexão, mas a investigação completa ainda depende da cota disponível.
5. Importe os sete CSVs e valide o pacote. O resultado esperado para o fixture atual é qualidade 85/100, status com avisos e quatro talhões.
6. Deixe abertos os relatórios-reserva validados em `demo-data/relatorios-reserva/phase7-single_field_temporal.html` e `demo-data/relatorios-reserva/phase7-soil_operations_vigor.html`. Eles devem ser apresentados como resultados salvos de ensaios, nunca como execuções ao vivo.

## Fluxo principal na tela

1. Selecione os sete CSVs e valide o pacote.
2. Continue para o chat analítico.
3. Faça uma pergunta e clique em **Enviar pergunta**.
4. Durante o processamento, mostre o tempo decorrido. Abra **Ver detalhes da análise** somente se quiser exibir os eventos operacionais: intenção identificada, ferramentas selecionadas, evidências calculadas e síntese em andamento. Esses eventos não expõem o raciocínio interno nem as chaves.
5. No relatório, comece pela aba **Resposta**. Leia primeiro o bloco destacado que responde diretamente à pergunta.
6. Mostre os insights e gráficos como sustentação da resposta. Não leia tabelas de números como se fossem conclusão.
7. Abra **Detalhes técnicos** para mostrar testes, métodos, fontes, evidências e limitações.
8. Baixe o relatório HTML, se solicitado. O arquivo é autocontido e preparado para impressão A4.

## Perguntas para demonstrar

### 1. Conhecer os dados

> Quais tipos de dados estão disponíveis neste pacote?

Resposta esperada: catálogo objetivo dos arquivos e informações disponíveis, sem transformar a pergunta em investigação.

### 2. Conhecer as capacidades

> O que a ferramenta consegue analisar com estes dados?

Resposta esperada: descrição das análises descritivas, temporais, comparativas e testes disponíveis, separando o que os dados atuais permitem do que exigiria outras informações.

### 3. Descrição de um talhão

> Descreva as informações de vigor disponíveis para o talhão Grão 4.0.

Resposta esperada: resumo descritivo, sem inventar teste de hipótese ou comparação.

### 4. Investigação de um único talhão

> Na série temporal de NDVI do talhão Grão 4.0, houve mudanças bruscas ou divergências relevantes durante a safra?

Resposta esperada: relatório Top-Down explicando que existe apenas uma observação válida e que a série não sustenta a detecção de mudanças. A insuficiência é dos dados, não do ferramental.

### 5. Investigação combinada

> O que as análises de solo indicam sobre o contexto da área e quais sinais aparecem na execução de correção e no vigor dos talhões Grão 4.0 e Grão Convencional?

Resposta esperada: separar claramente três partes. Solo é contexto geral do dataset, porque não existe vínculo entre amostras e talhões. Operações e vigor podem ser descritos ou comparados apenas na cobertura disponível. Qualquer parte não sustentada deve aparecer identificada no início do relatório.

## Fala curta sugerida

“O FarmLab aceita perguntas descritivas e investigativas. Primeiro ele identifica o que foi pedido; depois seleciona os módulos analíticos compatíveis com os dados, calcula as evidências e só então usa o Gemini para organizar uma resposta executiva. O primeiro bloco responde diretamente à pergunta. Abaixo ficam os insights e gráficos, e os detalhes técnicos mostram como a conclusão foi obtida. Quando faltam dados, a resposta informa quais dados faltam. Quando falta uma ferramenta, informa qual capacidade ainda não existe.”

## Comportamento correto em falhas

- Se uma chave falhar e outra estiver configurada, o backend tenta a próxima dentro do mesmo limite total de 90 segundos.
- Se todas as chaves falharem, o relatório investigativo é bloqueado. O sistema preserva o dataset e permite tentar novamente sem novo upload.
- Não existe relatório local de contingência apresentado como resposta do Gemini.
- Se a pergunta estiver apenas parcialmente sustentada, o relatório responde a parte possível e destaca separadamente o que não pôde ser respondido.
- O botão pode ser cancelado durante o processamento e deve ser liberado após sucesso, erro, timeout ou cancelamento.

## Reserva e transparência

Os relatórios-reserva aprovados são:

- `demo-data/relatorios-reserva/phase7-single_field_temporal.html`
- `demo-data/relatorios-reserva/phase7-soil_operations_vigor.html`

Eles foram gerados com o pacote sintético e não contêm scripts nem recursos externos. A investigação individual concluiu em 17,079 segundos e a combinada em 74,947 segundos. Não apresente uma reserva como resultado recém-gerado.

Antes da banca, faça uma execução completa com as chaves que serão usadas no dia, revise o conteúdo com a pessoa responsável pelo domínio e confirme visualmente em tela de projetor.
