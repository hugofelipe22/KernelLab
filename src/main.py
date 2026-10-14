"""KernelLab - simulador de CPU, memória e dispositivos (interface de terminal).

Uso rápido:  python src/main.py            (executa tudo com os dados padrão)
             python src/main.py --help     (todas as opções)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

import devices
import memory
import metrics
import schedulers

ROOT = Path(__file__).resolve().parent.parent
LINE = "=" * 78


# ----------------------------------------------------------------- saída -----
def table(headers: List[str], rows: List[List[str]]) -> str:
    cols = list(zip(headers, *rows))
    widths = [max(len(str(c)) for c in col) for col in cols]
    fmt = lambda r: " | ".join(str(c).ljust(w) for c, w in zip(r, widths))
    sep = "-+-".join("-" * w for w in widths)
    return "\n".join([fmt(headers), sep] + [fmt(r) for r in rows])


def title(text: str) -> None:
    print(f"\n{LINE}\n{text}\n{LINE}")


def num(x: float) -> str:
    return f"{x:g}"


def gantt_text(result: schedulers.ScheduleResult, processes) -> str:
    """Linha do tempo: uma linha por processo, '#' = executando em cada unidade."""
    end = int(max(s.end for s in result.segments))
    lines = []
    for p in processes:
        cells = ["."] * end
        for s in result.segments:
            if s.pid == p.pid:
                for t in range(int(s.start), int(s.end)):
                    cells[t] = "#"
        lines.append(f"  {p.pid} {''.join(cells)}")
    ticks = [" "] * (end + 3)
    for t in range(0, end + 1, 5):
        for k, ch in enumerate(str(t)):
            ticks[t + k] = ch
    lines.append("     " + "".join(ticks) + f"  (tempo; total = {end})")
    seq = " -> ".join(f"{s.pid}[{num(s.start)}-{num(s.end)}]" for s in result.segments)
    lines.append(f"  Sequência: {seq}")
    return "\n".join(lines)


# ------------------------------------------------------------------ CPU ------
def run_cpu(args, processes, cfg):
    title("ETAPA 1 - ESCALONAMENTO DA CPU")
    print(table(["PID", "Função", "Chegada", "Burst", "Prior.", "Mem (MB)", "Dispositivo"],
                [[p.pid, p.name, num(p.arrival), num(p.burst), p.priority,
                  p.memory_mb, ", ".join(p.devices)] for p in processes]))
    print("(menor número de prioridade = maior prioridade)")

    results = schedulers.run_all(processes, args.quantum,
                                 include_preemptive_priority=not args.no_extra)
    summaries = [metrics.compute_metrics(r, processes, cfg["excessive_delay_factor"],
                                         cfg.get("starvation_factor", 2.0))
                 for r in results]

    for res, s in zip(results, summaries):
        extra = "  [variante extra, não obrigatória]" if "preemptiva" in res.algorithm else ""
        print(f"\n--- {res.algorithm}{extra} ---")
        print("Ordem de execução:", " -> ".join(res.order))
        print("Diagrama de Gantt:")
        print(gantt_text(res, processes))
        rows = [[m.pid, num(m.arrival), num(m.burst), num(m.completion), num(m.waiting),
                 num(m.turnaround), num(m.response), m.overtaken_by,
                 "SIM" if m.excessive_delay else "-",
                 "SIM" if m.starvation_risk else "-"] for m in s.per_process]
        rows.append(["MÉDIA", "", "", "", f"{s.avg_waiting:.2f}", f"{s.avg_turnaround:.2f}",
                     f"{s.avg_response:.2f}", "", "", ""])
        if not args.compact:
            print(table(["PID", "Cheg", "Burst", "Término", "Espera", "Retorno", "Resposta",
                         "Ultrapassado", "Atraso exc.", "Starvation"], rows))
        else:
            print(f"Médias -> espera {s.avg_waiting:.2f} | retorno {s.avg_turnaround:.2f}"
                  f" | resposta {s.avg_response:.2f}")
        print(f"Trocas de contexto: {s.context_switches} | "
              f"Justiça (Jain): {s.fairness:.3f}")
        print("Atraso excessivo (espera >= "
              f"{cfg['excessive_delay_factor']:g}x burst): "
              f"{', '.join(s.delayed_pids) or 'nenhum'} | "
              f"Risco de starvation: {', '.join(s.starving_pids) or 'nenhum'}")

    title("ETAPA 2 - COMPARAÇÃO DOS ESCALONADORES")
    print(table(["Algoritmo", "Espera", "Retorno", "Resposta", "Trocas", "Jain",
                 "Espera alarme", "Maior espera", "Atraso exc.", "Starvation"],
                [[s.algorithm, f"{s.avg_waiting:.2f}", f"{s.avg_turnaround:.2f}",
                  f"{s.avg_response:.2f}", s.context_switches, f"{s.fairness:.3f}",
                  num(s.get(cfg["alarm_pid"]).waiting), num(s.max_waiting),
                  ",".join(s.delayed_pids) or "-", ",".join(s.starving_pids) or "-"]
                 for s in summaries]))
    required = [s for s in summaries if "preemptiva" not in s.algorithm]
    for label, group in (("Entre os 4 algoritmos obrigatórios", required),
                         ("Incluindo a variante preemptiva", summaries)):
        if group is summaries and args.no_extra:
            continue
        ans = metrics.compare(group, cfg["alarm_pid"])
        print(f"\n{label}:")
        print(f"  Menor tempo médio de espera ........ {ans['menor_espera_media']}")
        print(f"  Melhor tempo médio de resposta ..... {ans['melhor_resposta_media']}")
        print(f"  Alarme tratado com mais eficiência . {ans['alarme_mais_eficiente']}")
        print(f"  Maior risco de starvation .......... {ans['maior_risco_starvation']}")
        print(f"  CPU distribuída de forma mais justa  {ans['mais_justo']}")

    rec = recommend(summaries, cfg["alarm_pid"])
    print("\nRecomendação para a MedControl (critério: 1º menor espera do alarme, "
          "2º menos processos em risco de starvation, 3º menor espera média, "
          "4º maior justiça):")
    print(f"  -> {rec.algorithm}  | alarme espera {num(rec.get(cfg['alarm_pid']).waiting)}"
          f" | espera média {rec.avg_waiting:.2f} | em risco de starvation: "
          f"{', '.join(rec.starving_pids) or 'nenhum'}")
    return results, summaries


def recommend(summaries, alarm_pid) -> metrics.AlgorithmSummary:
    """Escolha por criticidade primeiro; desempenho e justiça como desempate."""
    return min(summaries, key=lambda s: (s.get(alarm_pid).waiting, len(s.starving_pids),
                                         round(s.avg_waiting, 9), -s.fairness))


# ---------------------------------------------------------------- memória ----
def run_memory(args, cfg):
    title("ETAPA 3 - GERENCIAMENTO DE MEMÓRIA (SUBSTITUIÇÃO DE PÁGINAS)")
    refs, n = args.refs, args.frames
    print(f"Frames: {n} | Referências ({len(refs)}): {', '.join(map(str, refs))}")
    results = memory.run_all(refs, n)
    for r in results:
        print(f"\n--- {r.algorithm} ---")
        header = ["Ref"] + [f"F{i + 1}" for i in range(n)] + ["Resultado", "Removida"]
        rows = [[st.ref] + [("-" if f is None else f) for f in st.frames]
                + ["FALTA" if st.fault else "hit",
                   "" if st.victim is None else st.victim] for st in r.steps]
        print(table(header, rows))
        print(f"Hits: {r.hits} | Faults: {r.faults} | Taxa de faltas: "
              f"{r.fault_rate:.1%} ({r.faults}/{len(r.steps)})")
    print()
    print(table(["Algoritmo", "Hits", "Faults", "Taxa de faltas"],
                [[r.algorithm, r.hits, r.faults, f"{r.fault_rate:.1%}"] for r in results]))
    by = {r.algorithm: r for r in results}
    ref_faults = by["Optimal"].faults
    real = [r for r in results if r.algorithm != "Optimal"]
    top = min(r.faults for r in real)
    names = " e ".join(r.algorithm for r in real if r.faults == top)
    print(f"\nMelhor resultado absoluto: Optimal ({ref_faults} faltas) - referência "
          "teórica (precisa conhecer o futuro).")
    print(f"Melhor algoritmo implementável: {names} ({top} faltas"
          + (", empate" if " e " in names else "") + ").")
    print(f"Diferença: FIFO descarta a página mais antiga na memória, mesmo que seja "
          f"reutilizada logo ({by['FIFO'].faults} faltas); LRU usa o passado recente "
          f"como previsão do futuro ({by['LRU'].faults}); Optimal escolhe a página "
          f"cujo próximo uso é mais distante ({by['Optimal'].faults}).")
    sweep = memory.sweep(refs, max(args.max_frames, n))
    print("\nFaltas x quantidade de frames:")
    print(table(["Frames"] + list(sweep),
                [[k + 1] + [sweep[a][k] for a in sweep]
                 for k in range(len(next(iter(sweep.values()))))]))
    return results, sweep


# ------------------------------------------------------------ dispositivos ---
def run_devices(args):
    title("ETAPA 4 - CONTROLE DE DISPOSITIVOS")
    acl = devices.AccessControlMatrix.load(args.access_matrix)
    print("Matriz de controle de acesso (X = permitido):\n")
    print(acl.render())

    reqs = [
        devices.Request("P3", "write", 0.25, 0.00),                    # relatório
        devices.Request("P5", "write", 0.25, 0.05, exclusive_ops=2),   # backup exclusivo
        devices.Request("P6", "read", 0.25, 0.10),                     # atualização
        devices.Request("P4", "write", 0.25, 0.15),                    # sem permissão
    ]
    for use_mutex in (True, False):
        label = "COM mutex (fila FIFO)" if use_mutex else "SEM mutex (sem controle)"
        print(f"\n--- Disco concorrente: {label} ---")
        res = devices.run_scenario(acl, "disco", reqs, use_mutex)
        for ev in res.events:
            print("  " + str(ev))
        print(f"  Máx. acessos simultâneos: {res.max_concurrent} | "
              f"violações de exclusão mútua: {res.violations} | "
              f"negados: {', '.join(res.denied) or 'nenhum'}")
    return acl


# ------------------------------------------------------------------ main -----
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="KernelLab - simulador de gerenciamento de CPU, memória e dispositivos")
    ap.add_argument("--processes", default=ROOT / "data" / "processes.json",
                    help="JSON com os processos")
    ap.add_argument("--config", default=ROOT / "data" / "config.json",
                    help="JSON com quantum, frames e sequência de páginas")
    ap.add_argument("--access-matrix", default=ROOT / "data" / "access_matrix.json",
                    help="JSON com a matriz de controle de acesso")
    ap.add_argument("--quantum", type=float, help="quantum do Round Robin (sobrepõe config)")
    ap.add_argument("--frames", type=int, help="quantidade de frames (sobrepõe config)")
    ap.add_argument("--refs", help="sequência de páginas, ex.: 1,2,3,4,1,2 (sobrepõe config)")
    ap.add_argument("--max-frames", type=int, default=7,
                    help="limite da varredura de frames (padrão 7)")
    ap.add_argument("--only", choices=["cpu", "memory", "devices", "all"], default="all",
                    help="executa apenas uma etapa")
    ap.add_argument("--no-extra", action="store_true",
                    help="omite a variante extra Prioridade preemptiva")
    ap.add_argument("--compact", action="store_true",
                    help="CPU: omite a tabela por processo (mostra só Gantt e médias)")
    ap.add_argument("--no-charts", action="store_true", help="não gera gráficos PNG")
    ap.add_argument("--out", default=ROOT / "docs" / "img",
                    help="pasta de saída dos gráficos")
    return ap


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    try:
        cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
        cfg.setdefault("excessive_delay_factor", 2.0)
        cfg.setdefault("alarm_pid", "P4")
        args.quantum = args.quantum if args.quantum is not None else cfg["quantum"]
        args.frames = args.frames if args.frames is not None else cfg["frames"]
        args.refs = ([int(x) for x in args.refs.split(",")] if args.refs
                     else cfg["reference_string"])
        processes = schedulers.load_processes(args.processes)
    except (OSError, KeyError, ValueError) as exc:
        print(f"Erro nos dados de entrada: {exc}", file=sys.stderr)
        return 2

    results = summaries = mem = sweep = None
    try:
        if args.only in ("cpu", "all"):
            results, summaries = run_cpu(args, processes, cfg)
        if args.only in ("memory", "all"):
            mem, sweep = run_memory(args, cfg)
        if args.only in ("devices", "all"):
            run_devices(args)
    except (ValueError, KeyError) as exc:
        print(f"Erro na simulação: {exc}", file=sys.stderr)
        return 2

    if not args.no_charts and results and mem:
        import charts
        out = Path(args.out)
        paths = charts.all_charts(results, summaries, processes, mem, sweep, out)
        title("ETAPA 5 - GRÁFICOS GERADOS")
        for p in paths:
            print("  " + str(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
