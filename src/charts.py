"""Geração dos gráficos (PNG) com matplotlib. Paleta Okabe-Ito (segura para daltonismo)."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")  # sem janela: apenas grava arquivos
import matplotlib.pyplot as plt  # noqa: E402

from memory import MemoryResult  # noqa: E402
from metrics import AlgorithmSummary  # noqa: E402
from schedulers import Process, ScheduleResult  # noqa: E402

PALETTE = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00", "#56B4E9"]
PROC_COLORS = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9",
               "#999999", "#F0E442"]


def _save(fig, out_dir: Path, name: str) -> Path:
    path = out_dir / name
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def gantt(results: List[ScheduleResult], processes: List[Process],
          out_dir: Path) -> Path:
    colors = {p.pid: PROC_COLORS[i % len(PROC_COLORS)] for i, p in enumerate(processes)}
    fig, axes = plt.subplots(len(results), 1, sharex=True,
                             figsize=(11, 1.5 * len(results) + 0.8))
    if len(results) == 1:
        axes = [axes]
    for ax, res in zip(axes, results):
        for seg in res.segments:
            ax.broken_barh([(seg.start, seg.end - seg.start)], (0, 1),
                           facecolors=colors[seg.pid], edgecolor="white")
            ax.text((seg.start + seg.end) / 2, 0.5, seg.pid, ha="center",
                    va="center", color="white", fontsize=9, fontweight="bold")
        ax.set_yticks([])
        ax.set_ylabel(res.algorithm, rotation=0, ha="right", va="center", fontsize=9)
        ax.set_xlim(0, max(s.end for s in res.segments))
        ax.spines[["top", "right", "left"]].set_visible(False)
    axes[-1].set_xlabel("Tempo (unidades)")
    fig.suptitle("Diagramas de Gantt", fontweight="bold")
    return _save(fig, out_dir, "gantt.png")


def _grouped(ax, labels, series: Dict[str, List[float]], colors=None):
    n = len(series)
    width = 0.8 / n
    for k, (name, vals) in enumerate(series.items()):
        xs = [i + (k - (n - 1) / 2) * width for i in range(len(labels))]
        bars = ax.bar(xs, vals, width, label=name,
                      color=(colors or PALETTE)[k % len(PALETTE)])
        ax.bar_label(bars, fmt="%.1f", fontsize=7, padding=1)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.spines[["top", "right"]].set_visible(False)


def tempos_medios(summaries: List[AlgorithmSummary], out_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(9, 4.5))
    labels = ["Espera média", "Retorno médio", "Resposta média"]
    series = {s.algorithm: [s.avg_waiting, s.avg_turnaround, s.avg_response]
              for s in summaries}
    _grouped(ax, labels, series)
    ax.set_ylabel("Unidades de tempo")
    ax.set_title("Comparação dos tempos médios (menor é melhor)")
    ax.legend(fontsize=8)
    return _save(fig, out_dir, "tempos_medios.png")


def trocas_contexto(summaries: List[AlgorithmSummary], out_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar([s.algorithm for s in summaries],
                  [s.context_switches for s in summaries],
                  color=PALETTE[:len(summaries)])
    ax.bar_label(bars)
    ax.set_ylabel("Trocas de contexto")
    ax.set_title("Trocas de contexto por algoritmo")
    ax.spines[["top", "right"]].set_visible(False)
    plt.setp(ax.get_xticklabels(), fontsize=8)
    return _save(fig, out_dir, "trocas_contexto.png")


def espera_por_processo(summaries: List[AlgorithmSummary], out_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 4.5))
    pids = [m.pid for m in summaries[0].per_process]
    series = {s.algorithm: [s.get(pid).waiting for pid in pids] for s in summaries}
    _grouped(ax, pids, series)
    ax.set_ylabel("Tempo de espera")
    ax.set_title("Espera por processo (P4 = alarme crítico; P5 = backup)")
    ax.legend(fontsize=8)
    return _save(fig, out_dir, "espera_por_processo.png")


def justica(summaries: List[AlgorithmSummary], out_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar([s.algorithm for s in summaries], [s.fairness for s in summaries],
                  color=PALETTE[:len(summaries)])
    ax.bar_label(bars, fmt="%.3f")
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("Índice de Jain (1 = mais justo)")
    ax.set_title("Justiça na distribuição da CPU")
    ax.spines[["top", "right"]].set_visible(False)
    plt.setp(ax.get_xticklabels(), fontsize=8)
    return _save(fig, out_dir, "justica.png")


def memoria(results: List[MemoryResult], out_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7, 4))
    names = [r.algorithm for r in results]
    faults = [r.faults for r in results]
    hits = [r.hits for r in results]
    b1 = ax.bar(names, faults, color="#D55E00", label="Page faults")
    b2 = ax.bar(names, hits, bottom=faults, color="#009E73", label="Page hits")
    ax.bar_label(b1, label_type="center", color="white", fontweight="bold")
    ax.bar_label(b2, label_type="center", color="white", fontweight="bold")
    ax.set_ylabel("Referências")
    ax.set_title(f"Page faults x hits ({results[0].n_frames} frames)")
    ax.legend()
    ax.spines[["top", "right"]].set_visible(False)
    return _save(fig, out_dir, "memoria_faults_hits.png")


def memoria_frames(sweep: Dict[str, List[int]], out_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7, 4))
    for k, (name, vals) in enumerate(sweep.items()):
        ax.plot(range(1, len(vals) + 1), vals, marker="o", label=name, color=PALETTE[k])
    ax.set_xlabel("Quantidade de frames")
    ax.set_ylabel("Page faults")
    ax.set_title("Page faults x quantidade de frames")
    ax.legend()
    ax.spines[["top", "right"]].set_visible(False)
    return _save(fig, out_dir, "memoria_frames.png")


def all_charts(results: List[ScheduleResult], summaries: List[AlgorithmSummary],
               processes: List[Process], mem: List[MemoryResult],
               sweep: Dict[str, List[int]], out_dir: Path) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    return [gantt(results, processes, out_dir),
            tempos_medios(summaries, out_dir),
            trocas_contexto(summaries, out_dir),
            espera_por_processo(summaries, out_dir),
            justica(summaries, out_dir),
            memoria(mem, out_dir),
            memoria_frames(sweep, out_dir)]
