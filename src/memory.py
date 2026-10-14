"""Substituição de páginas: FIFO, LRU e Optimal (Belady/MIN).

Os frames são exibidos em posições fixas (slots): quando uma página é
substituída, a nova ocupa o mesmo slot da vítima. ``None`` = frame vazio.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence


@dataclass
class Step:
    ref: int
    frames: List[Optional[int]]   # estado dos frames APÓS a referência
    fault: bool
    victim: Optional[int] = None  # página removida (None se havia frame livre/hit)


@dataclass
class MemoryResult:
    algorithm: str
    n_frames: int
    steps: List[Step] = field(default_factory=list)

    @property
    def faults(self) -> int:
        return sum(s.fault for s in self.steps)

    @property
    def hits(self) -> int:
        return len(self.steps) - self.faults

    @property
    def fault_rate(self) -> float:
        return self.faults / len(self.steps) if self.steps else 0.0


def _validate(refs: Sequence[int], n_frames: int) -> None:
    if n_frames < 1:
        raise ValueError("A quantidade de frames deve ser >= 1")
    if not refs:
        raise ValueError("A sequência de referências está vazia")


def _simulate(name: str, refs: Sequence[int], n_frames: int,
              choose_victim: Callable[[List[Optional[int]], int, Dict[int, int]], int]
              ) -> MemoryResult:
    """Laço comum; ``choose_victim`` devolve o índice do slot a substituir.

    ``choose_victim(frames, i, meta)`` recebe os frames (todos ocupados), o
    índice i da referência atual e ``meta`` (página -> instante relevante:
    carga para FIFO, último uso para LRU).
    """
    _validate(refs, n_frames)
    frames: List[Optional[int]] = [None] * n_frames
    meta: Dict[int, int] = {}
    result = MemoryResult(name, n_frames)
    for i, page in enumerate(refs):
        if page in frames:
            if name == "LRU":
                meta[page] = i                  # só o LRU atualiza no hit
            result.steps.append(Step(page, frames[:], False))
            continue
        victim = None
        if None in frames:
            slot = frames.index(None)
        else:
            slot = choose_victim(frames, i, meta)
            victim = frames[slot]
            meta.pop(victim, None)
        frames[slot] = page
        meta[page] = i
        result.steps.append(Step(page, frames[:], True, victim))
    return result


def fifo(refs: Sequence[int], n_frames: int) -> MemoryResult:
    """Substitui a página que está há mais tempo na memória (menor instante de carga)."""
    return _simulate("FIFO", refs, n_frames,
                     lambda frames, i, meta: min(range(len(frames)),
                                                 key=lambda s: meta[frames[s]]))


def lru(refs: Sequence[int], n_frames: int) -> MemoryResult:
    """Substitui a página menos recentemente usada (menor instante de último uso)."""
    return _simulate("LRU", refs, n_frames,
                     lambda frames, i, meta: min(range(len(frames)),
                                                 key=lambda s: meta[frames[s]]))


def optimal(refs: Sequence[int], n_frames: int) -> MemoryResult:
    """Substitui a página cujo próximo uso é o mais distante (ou nunca ocorre).

    Requer conhecer o futuro: serve apenas como limite inferior de comparação.
    Empate (várias páginas nunca mais usadas): vence o menor slot.
    """
    def choose(frames, i, meta):
        def next_use(slot: int) -> float:
            page = frames[slot]
            for j in range(i + 1, len(refs)):
                if refs[j] == page:
                    return j
            return float("inf")
        return max(range(len(frames)), key=lambda s: (next_use(s), -s))
    return _simulate("Optimal", refs, n_frames, choose)


ALGORITHMS = {"FIFO": fifo, "LRU": lru, "Optimal": optimal}


def run_all(refs: Sequence[int], n_frames: int) -> List[MemoryResult]:
    return [fn(refs, n_frames) for fn in ALGORITHMS.values()]


def sweep(refs: Sequence[int], max_frames: int) -> Dict[str, List[int]]:
    """Faltas de página de cada algoritmo para 1..max_frames frames."""
    return {name: [fn(refs, n).faults for n in range(1, max_frames + 1)]
            for name, fn in ALGORITHMS.items()}
