# KernelLab

**Simulador de gerenciamento de CPU, memória e dispositivos em sistemas multitarefa.**
Trabalho da disciplina Sistemas Operacionais (UniFECAF) — cenário MedControl Systems.

- Relatório técnico (PDF): [`docs/relatorio_tecnico.pdf`](docs/relatorio_tecnico.pdf)
- Vídeo pitch: https://drive.google.com/file/d/1LoJspIvDFljWNC1lrjUZcHG6iQ36kUoS/view?usp=sharing
- Saída completa de uma execução: [`docs/saida_simulador.txt`](docs/saida_simulador.txt)

## 1. Problema e objetivo

A MedControl executa, em um servidor com uma CPU, processos de monitoramento, alarme,
telemetria, relatórios, backup e atualização. Foram observados atraso nos alarmes,
aumento do tempo de resposta, disputa pela CPU, muitas faltas de página, processos de
baixa prioridade esperando demais, concorrência em dispositivos e risco de acesso não
autorizado.

O KernelLab **não é um sistema operacional**: reproduz as decisões que um SO toma e
permite medir o impacto de cada algoritmo sobre os mesmos dados:

```
Entrada dos processos -> escalonamento da CPU -> métricas -> memória -> dispositivos -> comparação
```

## 2. Arquitetura

```
kernellab/
├── src/
│   ├── main.py         # interface de terminal, orquestra as etapas e imprime resultados
│   ├── schedulers.py   # FCFS, SJF, Round Robin, Prioridade (+ variante preemptiva)
│   ├── metrics.py      # espera, retorno, resposta, justiça (Jain), starvation, comparação
│   ├── memory.py       # FIFO, LRU, Optimal, varredura de frames
│   ├── devices.py      # matriz de acesso, fila FIFO + mutex, cenário concorrente
│   └── charts.py       # gráficos PNG (matplotlib)
├── data/
│   ├── processes.json      # processos (entrada)
│   ├── config.json         # quantum, frames, sequência de páginas, critérios
│   └── access_matrix.json  # matriz de controle de acesso
├── tests/              # 37 testes (unittest/pytest)
├── docs/               # relatório PDF, gráficos (docs/img) e saída de exemplo
├── demo.ps1            # demonstração passo a passo (ENTER avança)
├── requirements.txt
└── README.md
```

Os algoritmos não contêm dados fixos: processos, quantum, frames e sequência de páginas
vêm de arquivos JSON ou de opções de linha de comando.

## 3. Algoritmos implementados

| Área | Algoritmo | Observação |
|---|---|---|
| CPU | FCFS | não preemptivo, ordem de chegada |
| CPU | SJF | não preemptivo, menor burst entre os prontos |
| CPU | Round Robin | quantum configurável (padrão 3); chegada simultânea ao fim do quantum entra na fila antes do processo preemptado |
| CPU | Prioridade | menor número = maior prioridade; não preemptiva (padrão) |
| CPU | Prioridade preemptiva | **variante extra** (além dos 4 obrigatórios); desative com `--no-extra` |
| Memória | FIFO, LRU, Optimal | Optimal = referência (empate: menor slot) |
| Dispositivos | Matriz de acesso | ler, gravar, executar, usar, exclusivo |
| Dispositivos | Fila FIFO + mutex | `FifoMutex`; cenário com e sem mutex |

**Métricas** — retorno = término − chegada; espera = retorno − burst; resposta = 1ª
execução − chegada; troca de contexto = CPU passando de um processo para outro
diferente (primeiro despacho não conta; custo em tempo nulo).

**Critérios do simulador** (configuráveis em `data/config.json`):

- *atraso excessivo*: espera ≥ 2 × o próprio burst;
- *risco de starvation*: ultrapassado por algum processo que chegou depois **e** espera
  ≥ 2 × a espera média do algoritmo;
- *justiça*: índice de Jain sobre burst/retorno (1 = mais justo).

## 4. Instalação e execução

Requer Python 3.9+ (testado em 3.13).

```bash
git clone <URL-DO-REPOSITORIO>
cd KernelLab            # ou o nome da pasta clonada
python -m venv .venv
# Windows: .venv\Scripts\activate      Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python src/main.py
```

Sem argumentos, executa as Etapas 1 a 5 com os dados do enunciado e grava os gráficos
em `docs/img/`.

### Opções

| Opção | Efeito |
|---|---|
| `--only cpu\|memory\|devices\|all` | executa só uma etapa |
| `--quantum N` | quantum do Round Robin |
| `--frames N` | quantidade de frames |
| `--refs 1,2,3,...` | sequência de páginas |
| `--processes ARQ.json` | outro conjunto de processos |
| `--config ARQ.json` / `--access-matrix ARQ.json` | outras configurações |
| `--compact` | CPU: omite a tabela por processo |
| `--no-extra` | omite a Prioridade preemptiva |
| `--no-charts` / `--out PASTA` | sem gráficos / pasta dos gráficos |
| `--max-frames N` | limite da varredura de frames (padrão 7) |

## 5. Formato dos dados de entrada

`data/processes.json`:

```json
{
  "processes": [
    {"pid": "P1", "name": "Monitoramento cardíaco", "arrival": 0, "burst": 8,
     "priority": 1, "memory_mb": 120, "devices": ["rede"]}
  ]
}
```

Campos obrigatórios: `pid` (único), `arrival` (≥ 0), `burst` (> 0), `priority`
(inteiro; menor = mais prioritário). Opcionais: `name`, `memory_mb`, `devices`.

`data/config.json`: `quantum`, `frames`, `reference_string` (lista de páginas),
`excessive_delay_factor`, `starvation_factor`, `alarm_pid`.

`data/access_matrix.json`: `devices`, `permissions` e `matrix` (`{"P1": {"rede":
["use","read","write"]}}`). Permissões: `read`, `write`, `execute`, `use`, `exclusive`.

## 6. Exemplos de uso

```bash
python src/main.py --only cpu --compact --no-extra     # Gantt + médias dos 4 algoritmos
python src/main.py --only cpu --quantum 5              # RR com quantum 5
python src/main.py --only memory --frames 3            # memória com 3 frames
python src/main.py --only memory --refs 7,0,1,2,0,3,0,4,2,3 --frames 3
python src/main.py --only devices                      # matriz + disputa pelo disco
python src/main.py --processes meus_processos.json
```

Demonstração guiada, uma tela por ENTER (PowerShell):

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\demo.ps1
```

Saída em arquivo (no PowerShell 5, use `| Out-File -Encoding utf8 saida.txt`, pois `>`
grava em UTF-16):

```bash
python src/main.py --no-charts > saida.txt
```

Exemplo de Gantt (Round Robin, quantum 3), uma linha por processo:

```
P1 ###........###..........##...............
P2 ...###..............#....................
P4 .........##..............................
```

## 7. Testes

```bash
python -m pytest -q          # ou: python -m unittest discover -s tests
```

37 testes cobrem: ordem e Gantt de cada escalonador, conservação do tempo de CPU,
ausência de execução antes da chegada, CPU ociosa, quantum configurável, médias das
métricas (conferidas à mão), FIFO/LRU/Optimal (hits, faltas, estado dos frames,
anomalia de Belady, Optimal como limite inferior), matriz de acesso, exclusão mútua com
e sem mutex, ordem FIFO de atendimento e negação de acessos não autorizados.

## 8. Resultados principais (dados do enunciado, quantum 3, 4 frames)

**CPU** (unidades de tempo)

| Algoritmo | Espera | Retorno | Resposta | Trocas | Jain | Espera do alarme P4 | Starvation |
|---|---|---|---|---|---|---|---|
| FCFS | 13,67 | 20,50 | 13,67 | 5 | 0,674 | 18 | — |
| SJF | 10,67 | 17,50 | 10,67 | 5 | 0,761 | 5 | P5 |
| Round Robin (q=3) | 18,00 | 24,83 | 5,33 | 13 | 0,972 | 6 | — |
| Prioridade | 10,67 | 17,50 | 10,67 | 5 | 0,761 | 5 | P5 |
| *Prioridade preemptiva (extra)* | 10,17 | 17,00 | 9,83 | 6 | 0,799 | 0 | P5 |

- Menor espera média: SJF e Prioridade (empatam; nesta carga a ordem por prioridade
  coincide com a ordem por burst).
- Melhor resposta e maior justiça: Round Robin (ao custo de 13 trocas e maior espera).
- Alarme: sem preempção o P4 espera o P1 terminar (5 unidades); só a variante
  preemptiva o atende sem espera.
- Maior risco de starvation: SJF e Prioridade (backup P5 espera 24).

**Memória** (17 referências, 4 frames)

| Algoritmo | Hits | Faults | Taxa de faltas |
|---|---|---|---|
| FIFO | 5 | 12 | 70,6% |
| LRU | 7 | 10 | 58,8% |
| Optimal | 10 | 7 | 41,2% |

**Dispositivos**: com mutex + fila FIFO, o máximo de acessos simultâneos ao disco é 1
(0 violações); sem mutex, o mesmo cenário apresenta sobreposição. O acesso do P4 ao
disco é negado pela matriz.

**Recomendação**: escalonamento por **prioridade com preempção** (o alarme é atendido
sem espera e a espera média é a menor), **LRU** para substituição de páginas e acesso
aos dispositivos por **fila FIFO com mutex** sob a matriz de controle de acesso.
Detalhes e justificativas no relatório.

## 9. Limitações e melhorias possíveis

- O starvation do backup (P5) persiste na prioridade; falta implementar
  *envelhecimento* (aging).
- Custo da troca de contexto considerado nulo; processos sem E/S durante o burst
  (bloqueio por dispositivo é simulado à parte, na Etapa 4).
- Memória: uma única sequência global de páginas; não há tabela de páginas por processo
  nem relação entre os MB dos processos e o número de páginas.
- SJF supõe burst conhecido (sem estimativa); não há SRTF.
- A matriz de acesso é estática e é uma decisão de projeto (o enunciado só informa
  quais dispositivos cada processo usa); o dispositivo *log* aceita gravação de todos.
- O Gantt em texto assume tempos inteiros (os gráficos aceitam valores reais).
- Os números da execução sem mutex variam com o escalonamento de threads do SO
  hospedeiro; o resultado com mutex (máximo 1 acesso simultâneo) é determinístico.

## 10. Referências

- TANENBAUM, A. S.; BOS, H. *Sistemas Operacionais Modernos*.
- UNIVASF. *Organização e Arquitetura de Computadores II — Sistemas Multiprogramados*.
- PUC-Rio. *INF 1316/INF 1019: Sistemas Operacionais*, cap. 1.
- Tecnoblog. *O que é um sistema operacional?*
- JAIN, R.; CHIU, D.; HAWE, W. *A Quantitative Measure of Fairness...*, DEC-TR-301, 1984.
