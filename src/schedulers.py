"""Algoritmos de escalonamento de CPU (uma única CPU).

Cada algoritmo recebe uma lista de ``Process`` (e parâmetros como o quantum) e
devolve um ``ScheduleResult`` com os segmentos de execução (Gantt). Nenhum dado
de processo está fixo na lógica: tudo vem de ``data/processes.json``.

Convenção: menor número de prioridade = maior prioridade.
"""
from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List


@dataclass(frozen=True)
class Process:
    pid: str
    name: str
    arrival: float
    burst: float
    priority: int
    memory_mb: int = 0
    devices: tuple = ()


@dataclass(frozen=True)
class Segment:
    """Intervalo [start, end) em que a CPU executou ``pid``."""
    pid: str
    start: float
    end: float


@dataclass
class ScheduleResult:
    algorithm: str
    segments: List[Segment] = field(default_factory=list)

    @property
    def order(self) -> List[str]:
        """Ordem de execução (pid de cada segmento, na sequência)."""
        return [s.pid for s in self.segments]

    @property
    def context_switches(self) -> int:
        """Vezes em que a CPU passou de um processo para outro diferente.

        O primeiro despacho (CPU vazia -> primeiro processo) não conta.
        """
        order = self.order
        return sum(1 for a, b in zip(order, order[1:]) if a != b)


# ----------------------------------------------------------------- entrada --
def load_processes(path) -> List[Process]:
    """Lê e valida a lista de processos de um arquivo JSON."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return parse_processes(data["processes"])


def parse_processes(raw: List[dict]) -> List[Process]:
    procs: List[Process] = []
    seen = set()
    for item in raw:
        p = Process(
            pid=str(item["pid"]),
            name=str(item.get("name", item["pid"])),
            arrival=item["arrival"],
            burst=item["burst"],
            priority=int(item["priority"]),
            memory_mb=int(item.get("memory_mb", 0)),
            devices=tuple(item.get("devices", [])),
        )
        if p.pid in seen:
            raise ValueError(f"PID duplicado: {p.pid}")
        if p.arrival < 0:
            raise ValueError(f"{p.pid}: chegada negativa")
        if p.burst <= 0:
            raise ValueError(f"{p.pid}: burst deve ser > 0")
        seen.add(p.pid)
        procs.append(p)
    if not procs:
        raise ValueError("Nenhum processo informado")
    return procs


# ---------------------------------------------------------------- utilitário --
def _append(segments: List[Segment], pid: str, start: float, end: float) -> None:
    """Acrescenta um segmento, fundindo-o com o anterior se for o mesmo processo."""
    if segments and segments[-1].pid == pid and segments[-1].end == start:
        segments[-1] = Segment(pid, segments[-1].start, end)
    else:
        segments.append(Segment(pid, start, end))


def _by_arrival(processes: List[Process]) -> List[Process]:
    # sorted é estável: empates de chegada mantêm a ordem de entrada.
    return sorted(processes, key=lambda p: p.arrival)


# ------------------------------------------------------------------- FCFS ----
def fcfs(processes: List[Process]) -> ScheduleResult:
    """First Come, First Served: não preemptivo, ordem de chegada."""
    segs: List[Segment] = []
    time = 0.0
    for p in _by_arrival(processes):
        time = max(time, p.arrival)
        _append(segs, p.pid, time, time + p.burst)
        time += p.burst
    return ScheduleResult("FCFS", segs)


# --------------------------------------------- SJF / Prioridade (não-preempt.) --
def _non_preemptive(processes: List[Process], key: Callable[[Process], tuple],
                    name: str) -> ScheduleResult:
    pending = _by_arrival(processes)
    segs: List[Segment] = []
    time = 0.0
    while pending:
        ready = [p for p in pending if p.arrival <= time]
        if not ready:                       # CPU ociosa até a próxima chegada
            time = pending[0].arrival
            continue
        # desempate: chegada mais cedo, depois ordem de entrada (min é estável)
        chosen = min(ready, key=lambda p: key(p) + (p.arrival,))
        pending.remove(chosen)
        _append(segs, chosen.pid, time, time + chosen.burst)
        time += chosen.burst
    return ScheduleResult(name, segs)


def sjf(processes: List[Process]) -> ScheduleResult:
    """Shortest Job First (não preemptivo): menor burst entre os prontos."""
    return _non_preemptive(processes, lambda p: (p.burst,), "SJF")


# ------------------------------------------------------------- Prioridade ----
def priority(processes: List[Process], preemptive: bool = False) -> ScheduleResult:
    """Escalonamento por prioridade (menor número = maior prioridade).

    ``preemptive=False`` (padrão): processo em execução vai até o fim.
    ``preemptive=True``: uma chegada de maior prioridade interrompe a CPU.
    """
    if not preemptive:
        return _non_preemptive(processes, lambda p: (p.priority,), "Prioridade")

    remaining: Dict[str, float] = {p.pid: p.burst for p in processes}
    arrivals = sorted({p.arrival for p in processes})
    segs: List[Segment] = []
    time = 0.0
    while any(r > 0 for r in remaining.values()):
        ready = [p for p in processes if p.arrival <= time and remaining[p.pid] > 0]
        if not ready:
            time = min(a for a in arrivals if a > time)
            continue
        chosen = min(ready, key=lambda p: (p.priority, p.arrival))
        future = [a for a in arrivals if a > time]
        run = remaining[chosen.pid]
        if future:                          # reavalia na próxima chegada
            run = min(run, future[0] - time)
        _append(segs, chosen.pid, time, time + run)
        remaining[chosen.pid] -= run
        time += run
    return ScheduleResult("Prioridade (preemptiva)", segs)


# ------------------------------------------------------------ Round Robin ----
def round_robin(processes: List[Process], quantum: float = 3) -> ScheduleResult:
    """Round Robin com quantum configurável.

    Regra de desempate: se uma chegada coincide com o fim do quantum, o novo
    processo entra na fila *antes* do processo que foi preemptado.
    """
    if quantum <= 0:
        raise ValueError("quantum deve ser > 0")
    remaining = {p.pid: p.burst for p in processes}
    pending = deque(_by_arrival(processes))
    queue: deque = deque()
    segs: List[Segment] = []
    time = 0.0

    def admit() -> None:
        while pending and pending[0].arrival <= time:
            queue.append(pending.popleft())

    while pending or queue:
        admit()
        if not queue:
            time = pending[0].arrival
            continue
        p = queue.popleft()
        run = min(quantum, remaining[p.pid])
        _append(segs, p.pid, time, time + run)
        time += run
        remaining[p.pid] -= run
        admit()
        if remaining[p.pid] > 0:
            queue.append(p)
    return ScheduleResult(f"Round Robin (q={quantum:g})", segs)


# ----------------------------------------------------------------- fachada ---
def run_all(processes: List[Process], quantum: float = 3,
            include_preemptive_priority: bool = True) -> List[ScheduleResult]:
    """Executa os quatro algoritmos obrigatórios (+ variante preemptiva opcional)."""
    results = [fcfs(processes), sjf(processes),
               round_robin(processes, quantum), priority(processes)]
    if include_preemptive_priority:
        results.append(priority(processes, preemptive=True))
    return results
