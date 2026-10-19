# Roteiro da demonstração — W4.14

Ensaio de 18/10/2026. Meta: concluir a parte interativa em até dois minutos após selecionar os sete arquivos. O pacote definido para este roteiro é **sintético**; a fala deve identificá-lo assim. A demonstração mostra o funcionamento do sistema, não resultados científicos da área real.

## Preparar antes da banca

1. Abra o projeto em `C:\Users\souza\CSIMilho`.
2. Deixe o Explorador em `C:\Users\souza\CSIMilho\demo-data\apresentacao-sintetica`. Essa pasta já contém exatamente os sete CSVs, copiados sem alteração de `backend/tests/fixtures/manual/`.
3. Compile e inicie o servidor em um PowerShell novo, com a chave já configurada no backend:

```powershell
cd C:\Users\souza\CSIMilho\frontend
pnpm build
cd ..\backend
$env:APP_ENV = 'development'
$env:GEMINI_TIMEOUT_SECONDS = '75'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Os ajustes valem para esse terminal/processo, sem editar `.env`. Feche o terminal ao terminar. Mantenha um processo por sessão; não reinicie o servidor nem recarregue a página depois do upload, pois os dados e relatórios são temporários.

4. Abra `http://127.0.0.1:8000/`. Antes de iniciar o cronômetro, confira **Backend: Conectado** e use **Testar Gemini**. Configuração detectada não garante que a investigação inteira será válida. O teste faz uma chamada curta à API.
5. Deixe a pergunta abaixo pronta para colar. Confira a pasta de downloads e os relatórios de reserva antes da apresentação.

### Pacote exato

| Arquivo | Bytes |
| --- | ---: |
| fields.csv | 795 |
| service_orders.csv | 119 |
| ndvi_metadata.csv | 578 |
| LAYER_MAP_PLANTING.csv | 376 |
| LAYER_MAP_FERTILIZATION.csv | 414 |
| service_orders_fields.csv | 147 |
| soil_analysis.csv | 422 |

Total: **2.851 bytes**. Resultado esperado: qualidade **85/100**, quatro talhões, **duas amostras de solo**, zero erros e três avisos (nome normalizado, unidades de solo não documentadas e produtividade ausente). O par Grão tem **3/5 critérios**, uma data NDVI pareada e condição inicial indisponível. Esses avisos são parte da explicação, não falha do upload.

Se a pasta local não existir em outra máquina, execute na raiz do projeto:

```powershell
New-Item -ItemType Directory -Force demo-data/apresentacao-sintetica
Copy-Item -Path backend/tests/fixtures/manual/*.csv -Destination demo-data/apresentacao-sintetica
```

### Pergunta do ensaio

> Compare o NDVI e a condição inicial dos talhões. Resuma também o solo no escopo do dataset, sem atribuí-lo aos talhões. Considere população e calagem quando disponíveis e explicite as limitações.

## Cliques e fala principal

Os tempos abaixo são um orçamento para o apresentador, contado desde a seleção. Avance assim que cada resultado estiver disponível; não espere o fim da janela. A fala durante o processamento ocorre em paralelo à espera.

| Janela alvo | Ação | Fala sugerida |
| --- | --- | --- |
| 0–7 s | Selecionar os sete CSVs → **Validar pacote**. | “Este pacote é sintético. O sistema valida os arquivos, identifica os talhões e informa as limitações antes da análise.” |
| 7–12 s | **Continuar**. Manter Grão 4.0 × Grão Convencional, Safra completa. Colar a pergunta → **Executar investigação**. | “Vamos comparar manejos da mesma cultura e finalidade. A cobertura é limitada: temos uma data de NDVI.” |
| Até 87 s | Aguardar a geração, sem clicar novamente. | “As ferramentas calculam os indicadores. O Gemini organiza a investigação e a narrativa, que é validada contra as evidências. O solo representa o dataset inteiro, sem vínculo com talhões ou profundidades.” |
| Até 94 s | **Visão geral**: apontar a origem e a força da evidência. | Usar uma das falas de origem abaixo. Não ler o resumo inteiro. |
| Até 101 s | **Solo**: apontar conjuntos e métricas. | “Os conjuntos são grupos de medição. Não temos unidades e referências suficientes para prescrever adubação.” |
| Até 107 s | **Gráfico NDVI**. | “Neste exemplo, ambos têm NDVI 0,5 e gap zero. Isso não mede produtividade nem prova efeito do manejo.” |
| Até 113 s | **Evidências** → **Métodos** → **Limitações**, apontando uma referência. | “Cada achado remete a evidências e métodos. As limitações permanecem explícitas.” |
| Até 120 s | **Baixar relatório HTML** → **Nova comparação**. Encerrar com o formulário habilitado. | “O relatório pode ser consultado depois. Podemos comparar novamente sem reenviar os arquivos.” |

**Se aparecer Resultado do Gemini:** “Esta narrativa foi gerada pelo Gemini e passou pelas validações. Os números vêm das ferramentas analíticas.”

**Se aparecer Relatório local · fallback:** “A geração automática não pôde ser aproveitada. O sistema informa o motivo e apresenta um relatório local com as evidências disponíveis. Não estamos apresentando esse texto como uma resposta do Gemini.”

O tempo de geração e a cobertura das ferramentas podem variar. Não prometa oito chamadas, um título específico ou origem Gemini em toda execução. Se o resultado chegar perto do limite, priorize origem, solo, NDVI, limitações e download; deixe os detalhes dos métodos para perguntas. Não inicie uma terceira investigação durante a fala principal.

## Ensaio e plano de reserva

Para ensaiar o fallback sem mexer na chave salva, abra **outro PowerShell novo** e execute:

```powershell
cd C:\Users\souza\CSIMilho\backend
$env:APP_ENV = 'development'
$env:GEMINI_TIMEOUT_SECONDS = '45'
$env:GEMINI_API_KEY = ''
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Abra `http://127.0.0.1:8001/` em outra aba e repita o roteiro. O painel mostrará Gemini não configurado e o teste ficará desabilitado; a investigação local continua disponível. É uma sessão independente: será necessário importar o pacote nessa aba. Fechar esse terminal não altera a chave no `.env`.

Se não houver tempo para reiniciar ou se o servidor falhar, use os arquivos já baixados em `C:\Users\souza\CSIMilho\demo-data\relatorios-reserva`:

- `gemini-sintetico.html`: resultado Gemini deste ensaio.
- `fallback-sintetico.html`: resultado local sem chave deste ensaio.

Abra-os manualmente no navegador do computador antes da banca. Diga: “Este é um resultado salvo do ensaio com dados sintéticos.” Não apresente um arquivo de reserva como execução ao vivo. A abertura visual offline ainda precisa dessa conferência manual: o navegador integrado usado no teste bloqueia URLs `file:`. Os downloads reais foram confirmados e os HTMLs são autocontidos.

## Medições registradas

| Ensaio | Resultado visível após seleção | Percurso completo | Resultado |
| --- | ---: | ---: | --- |
| Gemini configurado, limite 75 s | 36,1 s | **60,4 s** | Gemini |
| Sem chave, limite 45 s | 1,1 s | **42,6 s** | Fallback local |
| Gemini configurado, limite 45 s | 45,0 s | **59,7 s** | Fallback por timeout |

O percurso completo inclui validação, comparação, pergunta, investigação, passagem pelas seis abas, download e retorno a Nova comparação. Cronômetro iniciado após o seletor aceitar os arquivos; servidor, build e health preparados antes. Tempos de parede do navegador automatizado, incluindo chamadas da automação e captura; **não incluem uma pessoa falando**. São três amostras, não garantia de desempenho. O roteiro reserva fala durante a espera e uma passagem curta pelos resultados; faça um ensaio oral com cronômetro antes da banca.

Nenhum erro ou aviso de console foi capturado. Os três downloads concluíram e a sessão voltou a permitir outra comparação. Configuração de 75 s sugerida para o percurso principal; 45 s é uma alternativa mais curta, com maior chance de fallback. O limite de geração não cobre upload, download ou problemas de conexão entre navegador e backend.

Evidências locais em `backend/.local/w4-14/`: `gemini-timing.json`, `fallback-timing.json`, `live-timing.json`, capturas e `package-manifest.json` com SHA-256 dos sete arquivos. Dados copiados e relatórios de reserva estão ignorados pelo Git. A chave não foi alterada; servidores temporários foram encerrados. Versão congelada na W4.15: tag local `apresentacao-w4-2026-10-18`. Consulte [CONGELAMENTO_APRESENTACAO.md](CONGELAMENTO_APRESENTACAO.md).
