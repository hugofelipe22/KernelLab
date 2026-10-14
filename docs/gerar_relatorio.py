"""Gera docs/relatorio_tecnico.pdf (Parte Teórica) usando os resultados do simulador.

Uso:  python docs/gerar_relatorio.py
Requer: reportlab (requirements.txt) e os gráficos em docs/img (rode src/main.py antes).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_JUSTIFY  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.platypus import (Image, PageBreak, Paragraph,  # noqa: E402
                                SimpleDocTemplate, Spacer, Table, TableStyle)

import devices  # noqa: E402
import memory  # noqa: E402
import metrics  # noqa: E402
import schedulers  # noqa: E402

# ---- Preencha antes de entregar ------------------------------------------------
VIDEO_URL = "https://drive.google.com/file/d/1LoJspIvDFljWNC1lrjUZcHG6iQ36kUoS/view?usp=sharing"
REPO_URL = "https://github.com/hugofelipe22/KernelLab"
AUTOR = "Hugo Vieira"
# --------------------------------------------------------------------------------

cfg = json.loads((ROOT / "data" / "config.json").read_text(encoding="utf-8"))
procs = schedulers.load_processes(ROOT / "data" / "processes.json")
results = schedulers.run_all(procs, cfg["quantum"])
S = [metrics.compute_metrics(r, procs, cfg["excessive_delay_factor"],
                             cfg["starvation_factor"]) for r in results]
REQUIRED = S[:4]
mem = memory.run_all(cfg["reference_string"], cfg["frames"])
sweep = memory.sweep(cfg["reference_string"], 7)
acl = devices.AccessControlMatrix.load(ROOT / "data" / "access_matrix.json")
reqs = [devices.Request("P3", "write", 0.25, 0.00),
        devices.Request("P5", "write", 0.25, 0.05, exclusive_ops=2),
        devices.Request("P6", "read", 0.25, 0.10),
        devices.Request("P4", "write", 0.25, 0.15)]
with_mutex = devices.run_scenario(acl, "disco", reqs, True)
no_mutex = devices.run_scenario(acl, "disco", reqs, False)

by_name = {s.algorithm: s for s in S}
FCFS, SJF = by_name["FCFS"], by_name["SJF"]
RR = next(s for s in S if s.algorithm.startswith("Round Robin"))
PRI, PREM = by_name["Prioridade"], by_name["Prioridade (preemptiva)"]
M = {r.algorithm: r for r in mem}

# ------------------------------------------------------------------ estilos ---
ss = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=ss["BodyText"], fontSize=10, leading=14,
                      alignment=TA_JUSTIFY, spaceAfter=6)
H1 = ParagraphStyle("h1", parent=ss["Heading1"], fontSize=15, spaceBefore=12, spaceAfter=8)
H2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=12, spaceBefore=8, spaceAfter=4)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8.5, leading=11, alignment=0)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=8.5, leading=10.5, alignment=0,
                      spaceAfter=0)
BULLET = ParagraphStyle("bullet", parent=BODY, leftIndent=14, bulletIndent=4, spaceAfter=3)


def P(t, st=BODY):
    return Paragraph(t, st)


def bullets(items):
    return [Paragraph(i, BULLET, bulletText="•") for i in items]


def tbl(rows, widths=None, header=True):
    data = [[Paragraph(str(c), CELL) for c in r] for r in rows]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
             ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCE6F1")))
    t.setStyle(TableStyle(style))
    return t


def img(name, width_cm=16):
    from reportlab.lib.utils import ImageReader
    path = ROOT / "docs" / "img" / name
    w, h = ImageReader(str(path)).getSize()
    width = width_cm * cm
    return Image(str(path), width=width, height=width * h / w)


def f2(x):
    return f"{x:.2f}".replace(".", ",")


def g(x):
    return f"{x:g}".replace(".", ",")


story = []

# ------------------------------------------------------------------- capa -----
story += [Spacer(1, 4 * cm),
          P("<b>KernelLab - Simulador de Gerenciamento de CPU, Memória e "
            "Dispositivos em Sistemas Multitarefa</b>",
            ParagraphStyle("t", parent=H1, fontSize=20, leading=26, alignment=1)),
          Spacer(1, 1 * cm),
          P("Relatório técnico - Parte Teórica",
            ParagraphStyle("st", parent=BODY, fontSize=13, alignment=1)),
          P("Disciplina: Sistemas Operacionais - UniFECAF",
            ParagraphStyle("st2", parent=BODY, alignment=1)),
          Spacer(1, 1.5 * cm),
          P(f"Autor(a): {AUTOR}", ParagraphStyle("a", parent=BODY, alignment=1)),
          P(f"Repositório: {REPO_URL}", ParagraphStyle("a", parent=BODY, alignment=1)),
          P(f"Vídeo: {VIDEO_URL}", ParagraphStyle("a", parent=BODY, alignment=1)),
          PageBreak()]

# --------------------------------------------------------- 1. contextualização --
total_mem = sum(p.memory_mb for p in procs)
total_burst = sum(p.burst for p in procs)
story += [
    P("1. Contextualização do problema", H1),
    P("A MedControl Systems opera uma plataforma de monitoramento de equipamentos "
      "médicos conectados. Em um único servidor, com <b>uma CPU</b>, executam "
      "simultaneamente seis processos: monitoramento cardíaco (P1), transmissão de "
      "telemetria (P2), geração de relatórios (P3), emissão de alarme crítico (P4), "
      "backup (P5) e atualização de dados (P6). Juntos demandam "
      f"{g(total_burst)} unidades de CPU e {total_mem} MB de memória, e competem por "
      "disco, rede e áudio."),
    P("Os sintomas observados pela empresa correspondem diretamente a tópicos da "
      "disciplina:"),
    tbl([["Sintoma", "Conceito de SO envolvido", "Onde é tratado no KernelLab"],
         ["Atraso no processamento de alarmes", "Política de escalonamento; prioridade; "
          "efeito comboio", "Etapas 1 e 2 (espera do P4 em cada algoritmo)"],
         ["Aumento do tempo de resposta", "Tempo de resposta; tamanho do quantum; "
          "preempção", "Etapa 1 (métrica de resposta)"],
         ["Disputa pela CPU", "Multiprogramação; troca de contexto", "Etapa 1 (trocas de contexto)"],
         ["Elevado número de faltas de página", "Memória virtual; política de "
          "substituição", "Etapa 3 (FIFO, LRU, Optimal)"],
         ["Processos de baixa prioridade esperando demais", "Starvation / inanição; "
          "justiça", "Etapas 1 e 2 (atraso excessivo, índice de Jain)"],
         ["Concorrência no acesso a dispositivos", "Condição de corrida; exclusão mútua; "
          "mutex e semáforos", "Etapa 4 (fila FIFO + mutex)"],
         ["Processos não autorizados usando recursos críticos", "Proteção; matriz de "
          "controle de acesso; menor privilégio", "Etapa 4 (matriz de acesso)"]],
        [5 * cm, 6 * cm, 5.5 * cm]),
    Spacer(1, 6),
    P("O objetivo do KernelLab não é ser um sistema operacional, e sim reproduzir as "
      "<i>decisões</i> que um SO toma (quem usa a CPU, qual página sai da memória, "
      "quem acessa o dispositivo) para que o impacto de cada política possa ser "
      "medido e comparado sobre os mesmos dados."),
]

# ------------------------------------------------------ 2. estados dos processos --
story += [
    P("2. Estados e ciclo de vida dos processos", H1),
    P("Um processo é um programa em execução, com seu contexto (registradores, contador "
      "de programa, espaço de endereços). Em um sistema multiprogramado, cada processo "
      "percorre os estados:"),
    tbl([["Estado", "Significado", "Exemplo na MedControl"],
         ["Novo", "Processo sendo criado", "P5 (backup) é disparado no instante 5"],
         ["Pronto", "Pode executar, aguarda a CPU", "P3, P4, P5 e P6 aguardando enquanto "
          "P1 usa a CPU"],
         ["Executando", "Está de fato usando a CPU", "P4 emitindo o alarme"],
         ["Bloqueado (espera)", "Aguarda evento externo, p. ex. dispositivo de E/S",
          "P5 aguardando o disco ocupado por P3"],
         ["Terminado", "Concluiu a execução", "P1 após consumir seus 8 de burst"]],
        [3.2 * cm, 6 * cm, 7.3 * cm]),
    Spacer(1, 6),
    P("As transições relevantes são: <b>novo -> pronto</b> (admissão), <b>pronto -> "
      "executando</b> (despacho pelo escalonador), <b>executando -> pronto</b> "
      "(preempção por fim de quantum ou por chegada de processo mais prioritário), "
      "<b>executando -> bloqueado</b> (pedido de E/S ou de recurso ocupado), "
      "<b>bloqueado -> pronto</b> (recurso liberado) e <b>executando -> terminado</b>. "
      "O escalonador de CPU atua nas transições envolvendo o estado <i>pronto</i>; o "
      "KernelLab modela cada processo apenas com tempo de chegada e burst de CPU, de "
      "modo que a transição para <i>bloqueado</i> aparece na Etapa 4 (fila de "
      "dispositivo), não na Etapa 1."),
]

# ----------------------------------------------------------- 3. escalonamento --
story += [
    P("3. Escalonamento de CPU", H1),
    P("O escalonador decide, a cada instante, qual processo pronto recebe a CPU. A "
      "<b>troca de contexto</b> é o custo de salvar o estado de um processo e "
      "restaurar o de outro; no simulador é contada cada vez que a CPU passa de um "
      "processo para outro diferente (o primeiro despacho não conta e o custo em "
      "tempo da troca é considerado nulo)."),
    P("3.1 Algoritmos implementados", H2),
    *bullets([
        "<b>FCFS</b> (First Come, First Served): não preemptivo; atende na ordem de "
        "chegada. Simples e sem starvation, mas sofre com o <i>efeito comboio</i>: "
        "processos curtos esperam atrás de processos longos.",
        "<b>SJF</b> (Shortest Job First, não preemptivo): entre os prontos, escolhe o "
        "de menor burst. Minimiza a espera média, porém exige conhecer o burst e "
        "pode adiar indefinidamente processos longos.",
        f"<b>Round Robin</b> (quantum = {g(cfg['quantum'])}): preemptivo; cada processo "
        "usa a CPU por no máximo um quantum e volta ao fim da fila. Dá boa resposta e "
        "justiça, ao custo de mais trocas de contexto e maior retorno para processos "
        "longos.",
        "<b>Prioridade</b> (menor número = maior prioridade): escolhe o pronto mais "
        "prioritário. Expressa criticidade, mas pode causar starvation dos de baixa "
        "prioridade. Implementada na forma não preemptiva (padrão do enunciado) e, "
        "como <b>variante extra</b>, na forma preemptiva, em que a chegada de um "
        "processo mais prioritário interrompe a CPU.",
    ]),
    P("3.2 Métricas", H2),
    *bullets([
        "<b>Tempo de retorno</b> = instante de término - chegada.",
        "<b>Tempo de espera</b> = retorno - burst (tempo parado na fila de prontos).",
        "<b>Tempo de resposta</b> = primeira vez na CPU - chegada.",
        "<b>Atraso excessivo</b> (critério do simulador): espera >= "
        f"{g(cfg['excessive_delay_factor'])} x o próprio burst.",
        "<b>Risco de starvation</b> (critério do simulador): o processo foi "
        "ultrapassado por algum processo que chegou depois dele <i>e</i> sua espera é "
        f">= {g(cfg['starvation_factor'])} x a espera média do algoritmo. Em uma "
        "simulação finita não é possível provar inanição; o critério sinaliza o "
        "<i>risco</i>.",
        "<b>Justiça</b>: índice de Jain sobre burst/retorno de cada processo "
        "(fração do tempo no sistema em que ele recebeu CPU); varia de 1/n a 1.",
    ]),
    P("3.3 Resultados sobre os processos do enunciado", H2),
    img("gantt.png", 16),
    Spacer(1, 6),
]
rows = [["Algoritmo", "Espera média", "Retorno médio", "Resposta média", "Trocas de contexto",
         "Jain", "Espera do alarme (P4)", "Em risco de starvation"]]
for s in S:
    rows.append([s.algorithm, f2(s.avg_waiting), f2(s.avg_turnaround), f2(s.avg_response),
                 s.context_switches, f"{s.fairness:.3f}".replace(".", ","),
                 g(s.get("P4").waiting), ", ".join(s.starving_pids) or "nenhum"])
story += [tbl(rows, [3.3 * cm, 1.8 * cm, 1.9 * cm, 1.9 * cm, 1.9 * cm, 1.4 * cm,
                     2.2 * cm, 2.2 * cm]),
          P("Valores em unidades de tempo. A linha 'Prioridade (preemptiva)' é a "
            "variante extra.", SMALL),
          Spacer(1, 6), img("tempos_medios.png", 13), img("espera_por_processo.png", 14)]

story += [
    P("3.4 Respostas da comparação (Etapa 2)", H2),
    tbl([["Pergunta", "Resposta (entre os 4 algoritmos obrigatórios)", "Justificativa"],
         ["Menor tempo médio de espera",
          f"SJF e Prioridade (empate, {f2(SJF.avg_waiting)})",
          "Ambos executam P1, P4, P2, P6, P3, P5. Nesta carga a ordem por prioridade "
          "coincide com a ordem por burst; por isso os resultados são idênticos."],
         ["Melhor tempo de resposta",
          f"Round Robin ({f2(RR.avg_response)})",
          "O quantum faz todo processo ver a CPU logo após chegar (pior resposta "
          "individual: 11, de P6)."],
         ["Alarme (P4) tratado com mais eficiência",
          f"SJF e Prioridade (espera {g(SJF.get('P4').waiting)}, retorno "
          f"{g(SJF.get('P4').turnaround)}); RR: espera {g(RR.get('P4').waiting)}; "
          f"FCFS: espera {g(FCFS.get('P4').waiting)}",
          "Sem preempção, o P4 precisa esperar P1 terminar (instante 8). Só a "
          "variante preemptiva atende o alarme imediatamente: espera "
          f"{g(PREM.get('P4').waiting)}."],
         ["Maior risco de starvation",
          "SJF e Prioridade (P5: espera 24, ultrapassado por P6)",
          "Processos longos e/ou de baixa prioridade são sempre preteridos. FCFS e RR "
          "não ultrapassam ninguém; no FCFS o dano é o comboio (P4 espera 18)."],
         ["CPU distribuída de forma mais justa",
          f"Round Robin (Jain {RR.fairness:.3f})".replace(".", ","),
          "Todos recebem a CPU em fatias iguais e nenhum é ultrapassado; o preço é "
          f"{RR.context_switches} trocas de contexto e a pior espera média "
          f"({f2(RR.avg_waiting)})."]],
        [3.6 * cm, 5.2 * cm, 7.7 * cm]),
    Spacer(1, 6),
    img("justica.png", 11), img("trocas_contexto.png", 11),
]

story += [
    P("3.5 Qual é o mais adequado à MedControl?", H2),
    P("Nenhuma métrica isolada decide. O processo P4 (alarme crítico) tem prioridade "
      "0 e burst de apenas 2: o que importa para ele é <i>não esperar</i>. O Round "
      f"Robin é o mais justo e o de melhor resposta média, mas faz o alarme esperar "
      f"{g(RR.get('P4').waiting)} unidades e tem a maior espera média "
      f"({f2(RR.avg_waiting)}), além de {RR.context_switches} trocas de contexto. O "
      f"FCFS é o pior para o alarme (espera {g(FCFS.get('P4').waiting)}): ele fica "
      "atrás do relatório (P3), um processo sem urgência. O SJF reduz bem a espera "
      "média, mas só conhece duração, não criticidade: um alarme longo seria "
      "penalizado."),
    P(f"<b>Recomendação:</b> escalonamento por <b>prioridade</b>. Entre os quatro "
      f"algoritmos obrigatórios, a Prioridade empata com o SJF em desempenho "
      f"({f2(PRI.avg_waiting)} de espera média) e é a única que expressa "
      "criticidade explicitamente. Com <b>preempção</b> (variante extra), o alarme é "
      f"atendido sem espera (P4: 0, retorno {g(PREM.get('P4').turnaround)}), a espera "
      f"média cai para {f2(PREM.avg_waiting)} e o custo é uma única troca de contexto "
      "a mais (6 contra 5). Como a prioridade sozinha mantém o risco de starvation "
      "do backup (P5 espera 24), a política deve ser acompanhada de um mecanismo "
      "contra inanição (ver seção 8)."),
]

# -------------------------------------------------------------- 4. memória -----
story += [
    P("4. Memória virtual e substituição de páginas", H1),
    P("Na memória virtual, o espaço de endereços de cada processo é dividido em "
      "<b>páginas</b>, mapeadas para <b>frames</b> da memória física. Nem todas as "
      "páginas precisam estar na RAM: ao referenciar uma página ausente ocorre uma "
      "<b>falta de página (page fault)</b>, o SO a busca no disco e, se não há frame "
      "livre, precisa escolher uma <b>vítima</b>. Como o acesso ao disco é ordens de "
      "grandeza mais lento que o da RAM, o número de faltas determina diretamente a "
      "latência dos processos. Na MedControl, os seis processos somam "
      f"{total_mem} MB; se a memória física não comporta tudo, páginas do alarme e "
      "do monitoramento podem ser expulsas por processos pesados como o backup "
      "(300 MB), atrasando respostas."),
    *bullets([
        "<b>FIFO</b>: expulsa a página que está há mais tempo na memória. Fácil de "
        "implementar, mas ignora o uso: pode expulsar uma página muito utilizada e "
        "sofre da <i>anomalia de Belady</i> (mais frames podem gerar mais faltas).",
        "<b>LRU</b> (Least Recently Used): expulsa a página usada há mais tempo, "
        "aproximando o futuro pelo passado recente (princípio da localidade).",
        "<b>Optimal</b>: expulsa a página cujo próximo uso é o mais distante. É "
        "irrealizável na prática (exige conhecer o futuro) e serve de limite inferior "
        "para comparação.",
    ]),
    P(f"Sequência: {', '.join(map(str, cfg['reference_string']))}, com "
      f"{cfg['frames']} frames."),
    tbl([["Algoritmo", "Page hits", "Page faults", "Taxa de faltas"]] +
        [[r.algorithm, r.hits, r.faults, f"{r.fault_rate:.1%}".replace(".", ",")]
         for r in mem], [4 * cm, 3 * cm, 3 * cm, 3.5 * cm]),
    Spacer(1, 6),
]
# trace for LRU (exemplo)
lru = M["LRU"]
trace = [["Ref"] + [f"F{i + 1}" for i in range(cfg["frames"])] + ["Resultado"]]
for st in lru.steps:
    trace.append([st.ref] + [("-" if f is None else f) for f in st.frames] +
                 ["FALTA (sai " + str(st.victim) + ")" if st.fault and st.victim
                  else ("FALTA" if st.fault else "hit")])
story += [P("Estado dos frames do LRU após cada referência (os de FIFO e Optimal "
            "estão na saída do simulador):", SMALL),
          tbl(trace, [1.5 * cm] + [1.5 * cm] * cfg["frames"] + [3.5 * cm]),
          Spacer(1, 6),
          P("<b>Melhor resultado e justificativa.</b> O Optimal faz "
            f"{M['Optimal'].faults} faltas, o LRU {M['LRU'].faults} e o FIFO "
            f"{M['FIFO'].faults}. Entre os implementáveis, o LRU é o melhor. A "
            "diferença nasce da escolha da vítima: ao chegar a referência 5 (posição "
            "7), o FIFO expulsa a página 1, a mais antiga, mas ela é referenciada logo "
            "em seguida, provocando faltas em cascata (1, 2, 3, 4 sendo trocadas "
            "sucessivamente). O LRU também sofre nessa região, porém preserva as "
            "páginas recentemente usadas (1 e 2) e, assim, acerta mais referências "
            "(7 hits contra 5). O Optimal, ao enxergar o futuro, expulsa as páginas "
            "(4 e 3) cujo próximo uso está mais longe, chegando a 10 hits."),
          P("<b>Efeito do número de frames.</b> A varredura abaixo mostra que mais "
            "frames reduzem as faltas, e que a partir de 5 frames só restam as "
            f"{sweep['Optimal'][4]} faltas compulsórias (uma por página distinta). "
            "Para o FIFO com as 12 primeiras referências, o simulador reproduz a "
            "anomalia de Belady: 9 faltas com 3 frames e 10 com 4."),
          tbl([["Frames"] + list(sweep)] +
              [[k + 1] + [sweep[a][k] for a in sweep] for k in range(7)],
              [2.5 * cm, 3 * cm, 3 * cm, 3 * cm]),
          Spacer(1, 6), img("memoria_faults_hits.png", 10), img("memoria_frames.png", 10)]

# ---------------------------------------------- 5. concorrência / 6. segurança --
story += [
    P("5. Concorrência, mutex e semáforos", H1),
    P("Quando dois ou mais processos acessam o mesmo recurso compartilhado sem "
      "coordenação, o resultado depende da ordem de intercalação: é uma <b>condição "
      "de corrida</b>. O trecho de código que manipula o recurso é a <b>seção "
      "crítica</b>, que deve ser executada por um processo de cada vez (<b>exclusão "
      "mútua</b>). O <b>mutex</b> é uma trava binária (adquirir/liberar); o "
      "<b>semáforo</b> é um contador com operações atômicas <i>wait</i> e "
      "<i>signal</i>, e um semáforo binário equivale a um mutex."),
    P("No KernelLab, cada dispositivo possui uma <b>fila FIFO de solicitações</b> "
      "protegida por um mutex (classe FifoMutex): quem chega entra na fila e só "
      "executa quando o dispositivo está livre e é o primeiro da fila, o que garante "
      "exclusão mútua e atendimento por ordem de chegada (sem inanição na fila). "
      "O mesmo cenário foi executado com e sem o mutex, com quatro threads (P3, P5, "
      "P6 e P4) concorrendo pelo disco:"),
    tbl([["Execução", "Máx. acessos simultâneos", "Violações de exclusão mútua",
          "Ordem de atendimento"],
         ["Com mutex + fila FIFO", with_mutex.max_concurrent, with_mutex.violations,
          " -> ".join(e.pid for e in with_mutex.events if e.action.startswith("USA"))],
         ["Sem mutex", no_mutex.max_concurrent, no_mutex.violations,
          "intercalada / imprevisível"]],
        [4 * cm, 3.6 * cm, 4 * cm, 4.9 * cm]),
    P("Os valores da execução sem mutex dependem do escalonamento das threads pelo "
      "SO hospedeiro; o que é determinístico é que, com o mutex, o máximo de acessos "
      "simultâneos é sempre 1.", SMALL),
    P("O acesso <b>exclusivo</b> (sessão) permite que um processo reserve o "
      "dispositivo para várias operações seguidas; no cenário, o backup (P5) executa "
      "duas gravações consecutivas sem que P6 intercale uma leitura no meio."),
    P("6. Segurança no acesso aos dispositivos", H1),
    P("A proteção usa uma <b>matriz de controle de acesso</b>: linhas são "
      "processos (sujeitos), colunas são dispositivos (objetos) e cada célula "
      "lista as permissões (ler, gravar, executar, usar, exclusivo). Toda "
      "requisição é verificada <i>antes</i> de entrar na fila: se o processo não "
      "possui a permissão, o acesso é negado e ele não ocupa nem bloqueia o "
      "dispositivo. A matriz do projeto segue o <b>princípio do menor privilégio</b>: "
      "cada processo recebe apenas os dispositivos declarados no enunciado. Foram "
      "decisões de projeto (não vindas do enunciado) a distribuição das permissões "
      "específicas (por exemplo, exclusivo no disco para o backup, e no áudio e rede "
      "para o alarme), e o dispositivo 'log', aberto à gravação de todos os "
      "processos. No cenário, P4 (alarme) tenta usar o disco, que não consta em sua "
      "lista, e é negado."),
]
mrows = [["Proc"] + [f"{d}" for d in acl.devices]]
for pid in acl.processes:
    row = [pid]
    for d in acl.devices:
        abbr = {"read": "L", "write": "G", "execute": "X", "use": "U", "exclusive": "E"}
        row.append(" ".join(abbr[p] for p in acl.permissions if acl.allowed(pid, d, p))
                   or "-")
    mrows.append(row)
story += [tbl(mrows, [2 * cm, 3.6 * cm, 3.6 * cm, 3.6 * cm, 3.6 * cm]),
          P("L = ler, G = gravar, X = executar, U = usar, E = acesso exclusivo.", SMALL)]

# ------------------------------------------------ 7. relação teoria x decisões --
story += [
    P("7. Relação entre os conceitos e as decisões implementadas", H1),
    tbl([["Conceito", "Decisão no KernelLab", "Por quê (cenário MedControl)"],
         ["Escalonamento por prioridade", "Prioridade como política recomendada; "
          "preempção como variante", "O alarme (prioridade 0) não pode esperar um "
          "monitoramento terminar"],
         ["Efeito comboio / starvation", "Flags de atraso excessivo e risco de "
          "starvation por algoritmo", "Detectar quem é prejudicado (P4 no FCFS, P5 em "
          "SJF/Prioridade)"],
         ["Justiça", "Índice de Jain", "Quantificar o que o Round Robin ganha em "
          "equilíbrio e perde em espera"],
         ["Dados fora da lógica", "JSON de processos, quantum, frames e sequência "
          "configuráveis", "Reavaliar o servidor com cargas diferentes sem alterar "
          "código"],
         ["Memória virtual", "FIFO, LRU e Optimal com varredura de frames",
          "Medir quanto uma política melhor ou mais memória reduzem faltas"],
         ["Exclusão mútua", "Mutex com fila FIFO por dispositivo", "Impedir que "
          "backup, relatório e atualização gravem ao mesmo tempo no disco"],
         ["Proteção", "Matriz de acesso verificada antes da fila", "Impedir que "
          "processos não autorizados usem recursos críticos (áudio do alarme)"]],
        [4 * cm, 6 * cm, 6.5 * cm]),
]

# ------------------------------------------ 8. recomendação e limitações -------
story += [
    P("8. Recomendação final e limitações", H1),
    P("<b>Política recomendada:</b> escalonamento por prioridade com preempção, para "
      "a CPU; LRU (ou aproximação) para a substituição de páginas, por reduzir as "
      f"faltas de {M['FIFO'].faults} para {M['LRU'].faults} nesta sequência, "
      "enquanto o Optimal permanece só como referência; e acesso aos dispositivos "
      "por fila FIFO com mutex, mediado pela matriz de controle de acesso."),
    P("<b>Limitações que permanecem:</b>"),
    *bullets([
        "Risco de starvation do backup (P5): espera 24 unidades e é ultrapassado. A "
        "prioridade pura não resolve; um mecanismo de <i>envelhecimento</i> (aumentar "
        "gradualmente a prioridade de quem espera) seria a evolução natural, mas "
        "<b>não foi implementado</b>.",
        "A preempção só resolve o alarme porque ele é o processo mais prioritário; "
        "com vários alarmes simultâneos haveria disputa entre eles.",
        "O modelo ignora o custo (em tempo) da troca de contexto e as operações de "
        "E/S dos processos durante a execução na CPU: o bloqueio por dispositivo "
        "(Etapa 4) é simulado separadamente do escalonamento (Etapa 1).",
        "Memória: a sequência de páginas é única e global; o simulador não relaciona "
        "os MB de cada processo com a quantidade de páginas, nem simula "
        "pré-carregamento ou tabela de páginas por processo.",
        "O SJF supõe burst conhecido; em um servidor real ele precisaria ser "
        "estimado.",
        "A matriz de acesso é estática e foi definida pelo projeto; não há "
        "autenticação nem revogação em tempo de execução.",
        "Os resultados valem para o conjunto de seis processos do enunciado; outras "
        "cargas podem mudar o ranking (o simulador permite testar).",
    ]),
]

# ----------------------------------------------------------- referências ------
story += [
    P("9. Referências", H1),
    *bullets([
        "TANENBAUM, A. S.; BOS, H. <i>Sistemas Operacionais Modernos</i>. "
        "(livro-base indicado na disciplina).",
        "UNIVASF. <i>Organização e Arquitetura de Computadores II - Sistemas "
        "Multiprogramados</i>. https://www.docentes.univasf.edu.br/max.santana/material/"
        "OAC-II/sistemas_multiprogramados.pdf",
        "PUC-Rio. <i>INF 1316 / INF 1019: Sistemas Operacionais - Cap. 1</i>. "
        "https://www-di.inf.puc-rio.br/~endler/courses/inf1019/transp/aulas-teoricas/"
        "cap-1.pdf",
        "TECNOBLOG. <i>O que é um sistema operacional?</i> "
        "https://tecnoblog.net/responde/o-que-e-um-sistema-operacional/",
        "JAIN, R.; CHIU, D.; HAWE, W. <i>A Quantitative Measure of Fairness and "
        "Discrimination for Resource Allocation in Shared Computer Systems</i>. DEC "
        "Technical Report 301, 1984 (origem do índice de justiça usado).",
        "Unidades, videoaulas e textos-base da disciplina Sistemas Operacionais (AVA).",
    ]),
    Spacer(1, 12),
    P("10. Links da entrega", H1),
    P(f"<b>Repositório GitHub:</b> {REPO_URL}"),
    P(f"<b>Vídeo pitch:</b> {VIDEO_URL}"),
]


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(A4[0] / 2, 1.2 * cm,
                             f"KernelLab - Relatório técnico - página {doc.page}")
    canvas.restoreState()


out = ROOT / "docs" / "relatorio_tecnico.pdf"
SimpleDocTemplate(str(out), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                  topMargin=2 * cm, bottomMargin=2 * cm,
                  title="KernelLab - Relatório técnico").build(
    story, onFirstPage=footer, onLaterPages=footer)
print(f"Relatório gerado: {out}")
