# Roteiro do vídeo pitch — KernelLab (até 4 min; alvo: 3 min 45 s)

> Regra do enunciado: **demonstrar o sistema funcionando** (não basta slide, código
> parado ou ler o relatório). Fale em tom natural; os textos abaixo são sugestão.
> Grave a tela do terminal (fonte grande) e, se quiser, sua câmera no canto.

## Preparação (antes de gravar)

1. Abra o terminal na pasta do projeto, com a janela larga e fonte grande.
2. Rode uma vez `python src/main.py --no-charts` para garantir que tudo funciona.
3. Tenha abertos em abas: `docs/img/gantt.png` e `docs/img/tempos_medios.png`.
4. Antes de cada trecho, limpe a tela (`cls` no cmd/PowerShell, `clear` no bash).
5. Cronometre: o tempo total **não pode passar de 4:00**. Se estourar, corte o trecho
   de gráficos.

## Roteiro

| Tempo | Tela | Fala (sugestão) |
|---|---|---|
| **0:00–0:25** | Rosto/título "KernelLab" ou o README aberto | "Oi, eu sou **[seu nome]**. A MedControl monitora equipamentos médicos num servidor com uma CPU. Ali rodam monitoramento cardíaco, telemetria, relatórios, alarme crítico, backup e atualização. O problema: alarmes atrasando, tempo de resposta alto, muitas faltas de página, processos de baixa prioridade esperando demais e disputa por dispositivos. Eu construí o **KernelLab**, um simulador que compara políticas de CPU, memória e dispositivos." |
| **0:25–0:50** | README, seção "Algoritmos" (ou `ls src`) | "Na CPU implementei quatro algoritmos: **FCFS**, por ordem de chegada; **SJF**, o menor job primeiro; **Round Robin** com quantum 3; e **Prioridade**, onde menor número é maior prioridade. Também fiz uma variante preemptiva da prioridade, como extra. Os dados vêm de JSON, então dá para trocar processos e quantum sem mexer no código." |
| **0:50–1:30** | Terminal: `python src/main.py --only cpu --compact --no-charts` e rolar até o FCFS e o Round Robin | "Executando o simulador. Aqui está o **Diagrama de Gantt** do FCFS: o alarme, P4, só roda no instante 21, depois do relatório — espera 18. No Round Robin cada processo recebe fatias de 3, e o alarme roda no instante 9. Cada algoritmo mostra ordem de execução, espera, retorno, resposta, médias, trocas de contexto e quem sofre atraso excessivo ou risco de starvation." |
| **1:30–2:05** | Rolar até a tabela "ETAPA 2 - COMPARAÇÃO" (ou mostrar `docs/img/tempos_medios.png`) | "Comparando: o **menor tempo de espera** é de SJF e Prioridade, 10,67. A **melhor resposta** é do Round Robin, 5,33, e também o mais justo, mas com 13 trocas de contexto e a maior espera média. Para o **alarme**, SJF e Prioridade dão espera 5, porque ele precisa esperar o P1 terminar. O **maior risco de starvation** é do backup, P5, que espera 24 em SJF e Prioridade." |
| **2:05–2:40** | Terminal: `python src/main.py --only memory --no-charts` (rolar mostrando a tabela do LRU e o resumo). Opcional: rodar de novo com `--frames 3` | "Na memória, quatro frames e a sequência do enunciado. Aqui o estado dos frames após cada referência. **FIFO**: 5 hits e 12 faltas, 70,6%. **LRU**: 7 hits e 10 faltas. **Optimal**, usado só como referência: 10 hits e 7 faltas. O FIFO expulsa a página mais antiga mesmo que ela volte logo; o LRU usa o passado recente para prever; o Optimal enxerga o futuro. Mudando para 3 frames, as faltas aumentam — o número de frames é configurável." |
| **2:40–3:15** | Terminal: `python src/main.py --only devices` (mostrar a matriz e os dois cenários) | "Nos dispositivos, esta é a **matriz de controle de acesso**: cada processo só tem as permissões dos dispositivos que usa. Aqui simulo quatro processos disputando o disco. **Com mutex e fila FIFO**: um de cada vez, máximo de acessos simultâneos 1, zero violações — o backup usa o disco em sessão exclusiva. O P4 tenta usar o disco sem permissão e é **negado**. **Sem mutex**, os acessos se sobrepõem: aparecem violações de exclusão mútua (na minha execução foram 3)." |
| **3:15–3:45** | Terminal: rolar até "Recomendação" ou README seção 8; opcional: `python -m pytest -q` mostrando 37 testes passando | "Minha recomendação: **escalonamento por prioridade com preempção**, porque o alarme é atendido sem espera e a espera média cai para 10,17; **LRU** na memória; e dispositivos com **fila FIFO e mutex** atrás da matriz de acesso. Limitações: o backup ainda corre risco de starvation — o próximo passo seria *aging* — e o modelo ignora o custo da troca de contexto. O código, os testes e o relatório estão no GitHub. Obrigado!" |

## Comandos usados (na ordem)

```bash
python src/main.py --only cpu --compact --no-charts
python src/main.py --only memory --no-charts
python src/main.py --only memory --frames 3 --no-charts     # opcional
python src/main.py --only devices
python -m pytest -q                                          # opcional
```

## Dicas

- A saída da CPU é longa: use a barra de rolagem/`Shift+PageUp` ou grave por trechos e
  corte na edição. Falar enquanto rola é melhor que deixar a tela parada.
- Ensaie uma vez com cronômetro; o trecho de memória e o de dispositivos são os mais
  fáceis de estourar.
- Os números citados batem com a execução padrão. Se você alterar `data/*.json`, ajuste
  a fala.
- Publique no YouTube como **não listado**, teste o link em aba anônima e cole-o no
  README (topo) e no relatório (`VIDEO_URL` em `docs/gerar_relatorio.py`, depois rode
  `python docs/gerar_relatorio.py`).
