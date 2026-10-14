"""Controle de acesso e concorrência em dispositivos compartilhados.

* ``AccessControlMatrix``: matriz processo x dispositivo -> permissões
  (read, write, execute, use, exclusive), carregada de ``data/access_matrix.json``.
* ``FifoMutex``: mutex com fila FIFO de solicitações (exclusão mútua + ordem
  de chegada garantida, equivalente a um semáforo binário justo).
* ``SharedDevice``: dispositivo protegido pelo mutex; cada operação é
  autorizada pela matriz e registrada em um log de eventos.
* ``run_scenario``: executa threads concorrentes sobre um dispositivo, com ou
  sem mutex, e conta quantos acessos simultâneos indevidos ocorreram.
"""
from __future__ import annotations

import json
import threading
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Deque, Dict, Iterable, List, Optional, Set, Tuple

PERMISSIONS = ("read", "write", "execute", "use", "exclusive")


class AccessDenied(PermissionError):
    """O processo não possui a permissão exigida no dispositivo."""


# ---------------------------------------------------------- matriz de acesso --
class AccessControlMatrix:
    def __init__(self, matrix: Dict[str, Dict[str, Iterable[str]]],
                 devices: Iterable[str], permissions: Iterable[str] = PERMISSIONS):
        self.devices = list(devices)
        self.permissions = list(permissions)
        self._m: Dict[str, Dict[str, Set[str]]] = {
            pid: {dev: set(perms) for dev, perms in row.items()}
            for pid, row in matrix.items()
        }
        for pid, row in self._m.items():
            for dev, perms in row.items():
                if dev not in self.devices:
                    raise ValueError(f"{pid}: dispositivo desconhecido '{dev}'")
                bad = perms - set(self.permissions)
                if bad:
                    raise ValueError(f"{pid}/{dev}: permissão inválida {sorted(bad)}")

    @classmethod
    def load(cls, path) -> "AccessControlMatrix":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(data["matrix"], data["devices"],
                   data.get("permissions", PERMISSIONS))

    @property
    def processes(self) -> List[str]:
        return sorted(self._m)

    def allowed(self, pid: str, device: str, permission: str) -> bool:
        return permission in self._m.get(pid, {}).get(device, set())

    def check(self, pid: str, device: str, permission: str) -> None:
        if not self.allowed(pid, device, permission):
            raise AccessDenied(f"{pid} não tem permissão '{permission}' em '{device}'")

    def render(self) -> str:
        """Tabela textual: uma linha por processo/dispositivo, colunas = permissões."""
        abbr = {"read": "ler", "write": "gravar", "execute": "executar",
                "use": "usar", "exclusive": "exclusivo"}
        head = ["Proc", "Dispositivo"] + [abbr.get(p, p) for p in self.permissions]
        rows = [head]
        for pid in self.processes:
            for dev in self.devices:
                perms = self._m[pid].get(dev, set())
                rows.append([pid, dev] + ["X" if p in perms else "-"
                                          for p in self.permissions])
        widths = [max(len(r[i]) for r in rows) for i in range(len(head))]
        lines = []
        for k, r in enumerate(rows):
            lines.append("  ".join(c.ljust(widths[i]) if i < 2 else c.center(widths[i])
                                   for i, c in enumerate(r)))
            if k == 0:
                lines.append("  ".join("-" * w for w in widths))
        return "\n".join(lines)


# ------------------------------------------------------------------ mutex ----
class FifoMutex:
    """Mutex com fila FIFO de solicitantes (exclusão mútua + atendimento por ordem)."""

    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._queue: Deque[str] = deque()
        self._owner: Optional[str] = None

    def acquire(self, who: str) -> int:
        """Entra na fila e bloqueia até a vez. Retorna o tamanho da fila ao entrar."""
        with self._cond:
            self._queue.append(who)
            waiting_ahead = len(self._queue) - 1 + (1 if self._owner else 0)
            while self._owner is not None or self._queue[0] != who:
                self._cond.wait()
            self._queue.popleft()
            self._owner = who
            return waiting_ahead

    def release(self, who: str) -> None:
        with self._cond:
            if self._owner != who:
                raise RuntimeError(f"{who} tentou liberar um mutex que não possui")
            self._owner = None
            self._cond.notify_all()


# ------------------------------------------------------------ dispositivo ----
@dataclass
class Event:
    t: float
    pid: str
    action: str
    detail: str = ""

    def __str__(self) -> str:
        extra = f" {self.detail}" if self.detail else ""
        return f"[t={self.t:5.2f}s] {self.pid:<3} {self.action}{extra}"


class SharedDevice:
    """Dispositivo compartilhado: autorização + mutex FIFO + auditoria de uso."""

    def __init__(self, name: str, acl: AccessControlMatrix,
                 use_mutex: bool = True, clock_start: Optional[float] = None):
        self.name = name
        self.acl = acl
        self.use_mutex = use_mutex
        self.mutex = FifoMutex()
        self.events: List[Event] = []
        self.violations = 0            # acessos simultâneos indevidos observados
        self.max_concurrent = 0
        self._inside = 0
        self._guard = threading.Lock()  # protege apenas os contadores/log
        self._t0 = clock_start if clock_start is not None else time.monotonic()

    def _log(self, pid: str, action: str, detail: str = "") -> None:
        with self._guard:
            self.events.append(Event(time.monotonic() - self._t0, pid, action, detail))

    def _enter(self, pid: str, op: str, hold: float) -> None:
        with self._guard:
            self._inside += 1
            self.max_concurrent = max(self.max_concurrent, self._inside)
            if self._inside > 1:
                self.violations += 1
        self._log(pid, f"USA {self.name}", f"({op}, {hold:g}s)")
        time.sleep(hold)
        with self._guard:
            self._inside -= 1

    def access(self, pid: str, permission: str, hold: float) -> None:
        """Uma operação atômica no dispositivo (adquire e libera o mutex)."""
        self.acl.check(pid, self.name, "use")
        self.acl.check(pid, self.name, permission)
        self._log(pid, f"SOLICITA {self.name}", f"({permission})")
        if self.use_mutex:
            ahead = self.mutex.acquire(pid)
            if ahead:
                self._log(pid, "AGUARDOU", f"na fila ({ahead} à frente)")
            try:
                self._enter(pid, permission, hold)
            finally:
                self.mutex.release(pid)
        else:
            self._enter(pid, permission, hold)
        self._log(pid, f"LIBERA {self.name}")

    @contextmanager
    def exclusive_session(self, pid: str):
        """Mantém o dispositivo reservado para várias operações seguidas.

        Exige a permissão ``exclusive``; ninguém intercala operações enquanto
        a sessão estiver aberta.
        """
        self.acl.check(pid, self.name, "use")
        self.acl.check(pid, self.name, "exclusive")
        self._log(pid, f"SOLICITA {self.name}", "(acesso EXCLUSIVO)")
        ahead = self.mutex.acquire(pid) if self.use_mutex else 0
        if ahead:
            self._log(pid, "AGUARDOU", f"na fila ({ahead} à frente)")
        self._log(pid, f"ENTRA em sessão exclusiva de {self.name}")
        try:
            yield _Session(self, pid)
        finally:
            self._log(pid, f"SAI da sessão exclusiva de {self.name}")
            if self.use_mutex:
                self.mutex.release(pid)


class _Session:
    def __init__(self, device: SharedDevice, pid: str):
        self.device, self.pid = device, pid

    def operate(self, permission: str, hold: float) -> None:
        self.device.acl.check(self.pid, self.device.name, permission)
        self.device._enter(self.pid, permission, hold)


# ---------------------------------------------------------------- cenário ----
@dataclass
class Request:
    pid: str
    permission: str = "write"
    hold: float = 0.3          # tempo (s) usando o dispositivo
    start_delay: float = 0.0   # atraso até solicitar (s)
    exclusive_ops: int = 0     # >0: abre sessão exclusiva com N operações


@dataclass
class ScenarioResult:
    device: str
    use_mutex: bool
    events: List[Event]
    violations: int
    max_concurrent: int
    denied: List[str]


def run_scenario(acl: AccessControlMatrix, device_name: str,
                 requests: List[Request], use_mutex: bool = True) -> ScenarioResult:
    """Dispara uma thread por solicitação e relata violações de exclusão mútua."""
    dev = SharedDevice(device_name, acl, use_mutex=use_mutex)
    denied: List[str] = []
    denied_lock = threading.Lock()

    def worker(req: Request) -> None:
        time.sleep(req.start_delay)
        try:
            if req.exclusive_ops:
                with dev.exclusive_session(req.pid) as s:
                    for _ in range(req.exclusive_ops):
                        s.operate(req.permission, req.hold)
            else:
                dev.access(req.pid, req.permission, req.hold)
        except AccessDenied as exc:
            dev._log(req.pid, "NEGADO", f"-> {exc}")
            with denied_lock:
                denied.append(req.pid)

    threads = [threading.Thread(target=worker, args=(r,)) for r in requests]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return ScenarioResult(device_name, use_mutex, sorted(dev.events, key=lambda e: e.t),
                          dev.violations, dev.max_concurrent, denied)
