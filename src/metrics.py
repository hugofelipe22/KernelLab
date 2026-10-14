"""Métricas de escalonamento, justiça e detecção de atraso excessivo/starvation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from schedulers import Process, ScheduleResult


@dataclass
class ProcessMetrics:
    pid: str
    arrival: float
    burst: float
    priority: int
    start: float           # primeiro instante na CPU
    completion: float
    waiting: float         # retorno - burst
    turnaround: float      # término - chegada
    response: float        # primeiro uso da CPU - chegada
    overtaken_by: int      # processos que chegaram depois mas começaram antes
    excessive_delay: bool  # espera >= fator * burst
    starvation_risk: bool = False  # ultrapassado por chegada posterior e espera >= fator * média


@dataclass
class AlgorithmSummary:
    algorithm: str
    per_process: List[ProcessMetrics]
    avg_waiting: float
    avg_turnaround: float
    avg_response: float
    context_switches: int
    fairness: float        # índice de Jain sobre burst/retorno (1 = mais justo)
    max_waiting: float
    delayed_pids: List[str]    # atraso excessivo
    starving_pids: List[str]   # risco de starvation

    def get(self, pid: str) -> ProcessMetrics:
        return next(m for m in self.per_process if m.pid == pid)


def jain_index(values: List[float]) -> float:
    """Índice de justiça de Jain: (Σx)² / (n·Σx²); vai de 1/n (injusto) a 1 (justo)."""
    total = sum(values)
    squares = sum(v * v for v in values)
    return (total * total) / (len(values) * squares) if squares else 1.0


def compute_metrics(result: ScheduleResult, processes: List[Process],
                    delay_factor: float = 2.0,
                    starvation_factor: float = 2.0) -> AlgorithmSummary:
    """Calcula as métricas de um resultado de escalonamento.

    * retorno (turnaround) = término - chegada
    * espera               = retorno - burst
    * resposta             = primeira execução - chegada
    * atraso excessivo     : espera >= ``delay_factor`` x o próprio burst
    * risco de starvation  : foi ultrapassado por algum processo que chegou
      depois dele E espera >= ``starvation_factor`` x a espera média do
      algoritmo (um processo adiado repetidamente em favor de outros)
    * justiça              : Jain sobre x_i = burst_i / retorno_i (fração do
      tempo no sistema em que o processo de fato recebeu CPU).
    """
    first_start: Dict[str, float] = {}
    completion: Dict[str, float] = {}
    for seg in result.segments:
        first_start.setdefault(seg.pid, seg.start)
        completion[seg.pid] = seg.end

    rows: List[ProcessMetrics] = []
    for p in processes:
        turnaround = completion[p.pid] - p.arrival
        waiting = turnaround - p.burst
        overtaken = sum(1 for q in processes
                        if q.arrival > p.arrival
                        and first_start[q.pid] < first_start[p.pid])
        rows.append(ProcessMetrics(
            pid=p.pid, arrival=p.arrival, burst=p.burst, priority=p.priority,
            start=first_start[p.pid], completion=completion[p.pid],
            waiting=waiting, turnaround=turnaround,
            response=first_start[p.pid] - p.arrival,
            overtaken_by=overtaken,
            excessive_delay=waiting >= delay_factor * p.burst,
        ))

    n = len(rows)
    avg_wait = sum(r.waiting for r in rows) / n
    for r in rows:
        r.starvation_risk = (r.overtaken_by > 0
                             and r.waiting >= starvation_factor * avg_wait)
    return AlgorithmSummary(
        algorithm=result.algorithm,
        per_process=rows,
        avg_waiting=avg_wait,
        avg_turnaround=sum(r.turnaround for r in rows) / n,
        avg_response=sum(r.response for r in rows) / n,
        context_switches=result.context_switches,
        fairness=jain_index([r.burst / r.turnaround for r in rows]),
        max_waiting=max(r.waiting for r in rows),
        delayed_pids=[r.pid for r in rows if r.excessive_delay],
        starving_pids=[r.pid for r in rows if r.starvation_risk],
    )


def _best(summaries, key, reverse=False):
    """Todos os algoritmos empatados no melhor valor de ``key`` (min ou max)."""
    values = [round(key(s), 9) if isinstance(key(s), float) else key(s) for s in summaries]
    target = max(values) if reverse else min(values)
    return [s for s, v in zip(summaries, values) if v == target]


def _names(group) -> str:
    return " e ".join(s.algorithm for s in group)


def compare(summaries: List[AlgorithmSummary], alarm_pid: str) -> Dict[str, str]:
    """Responde, a partir dos números, às perguntas da Etapa 2 (empates listados)."""
    def starv_key(s):
        ratios = [s.get(pid).waiting / s.avg_waiting for pid in s.starving_pids]
        return (len(s.starving_pids), round(max(ratios, default=0.0), 6))

    wait = _best(summaries, lambda s: s.avg_waiting)
    resp = _best(summaries, lambda s: s.avg_response)
    alarm = _best(summaries, lambda s: s.get(alarm_pid).turnaround)
    starv = _best(summaries, starv_key, reverse=True)
    fair = _best(summaries, lambda s: s.fairness, reverse=True)
    a = alarm[0].get(alarm_pid)
    return {
        "menor_espera_media": f"{_names(wait)} ({wait[0].avg_waiting:.2f})",
        "melhor_resposta_media": f"{_names(resp)} ({resp[0].avg_response:.2f})",
        "alarme_mais_eficiente": (f"{_names(alarm)} "
                                  f"(espera {a.waiting:g}, retorno {a.turnaround:g})"),
        "maior_risco_starvation": (
            f"{_names(starv)} (em risco: "
            f"{', '.join(starv[0].starving_pids) or '-'})"),
        "mais_justo": f"{_names(fair)} (Jain {fair[0].fairness:.3f})",
    }
