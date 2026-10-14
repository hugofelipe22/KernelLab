"""Gera um vídeo MUDO de demonstração do KernelLab (para narrar depois).

Executa de verdade os comandos do simulador, captura a saída real e a anima em
uma janela de terminal (digitação, rolagem, destaque das partes importantes).
Também exibe os gráficos PNG e cartões de abertura/recomendação.

Gera duas versões em docs/video/:
  kernellab_demo_legendado.mp4      (com legenda explicativa na base)
  kernellab_demo_sem_legendas.mp4   (só terminal/gráficos, para narrar livremente)

Uso (precisa de imageio, imageio-ffmpeg, pillow, numpy; fora do requirements.txt):
  pip install imageio imageio-ffmpeg pillow numpy
  python docs/video/gerar_video.py
Os comandos do simulador rodam com o Python do .venv do projeto.
"""
import os
import subprocess
import sys
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PY = ROOT / ".venv" / "Scripts" / "python.exe"
if not PY.exists():
    PY = Path(sys.executable)
W, H, FPS = 1920, 1080, 10
FONTS = Path(r"C:\Windows\Fonts")

MONO = ImageFont.truetype(str(FONTS / "consola.ttf"), 18)
UI = ImageFont.truetype(str(FONTS / "segoeui.ttf"), 30)
UI_B = ImageFont.truetype(str(FONTS / "segoeuib.ttf"), 30)
H1 = ImageFont.truetype(str(FONTS / "segoeuib.ttf"), 72)
H2 = ImageFont.truetype(str(FONTS / "segoeuib.ttf"), 46)
BODY = ImageFont.truetype(str(FONTS / "segoeui.ttf"), 38)

CHAR_W = MONO.getlength("M")
LINE_H = 24
TITLE_H, CAP_H = 44, 70
ROWS = (H - TITLE_H - CAP_H - 16) // LINE_H
PROMPT = r"(.venv) PS C:\Users\Camila\Projetos\KernelLab> "

BG, FG = (12, 12, 12), (204, 204, 204)
C_PROMPT, C_HEAD, C_WARN, C_BAD, C_GOOD, C_REC = (
    (249, 241, 165), (97, 214, 214), (255, 185, 90), (255, 110, 110),
    (110, 220, 130), (160, 255, 160))


def line_color(text: str):
    if text.startswith(PROMPT):
        return C_PROMPT
    if text.startswith("===") or text.startswith("---") or text.startswith("ETAPA"):
        return C_HEAD
    if "NEGADO" in text:
        return C_BAD
    if "FALTA" in text and "|" in text:
        return C_WARN
    if "violações" in text or "SEM mutex" in text:
        return C_WARN
    if text.strip().startswith("->") or "Recomendação" in text or "passed" in text:
        return C_REC
    if "hit" in text and "|" in text:
        return C_GOOD
    return FG


# --------------------------------------------------------------- desenho -----
def base_terminal(lines, top, typed=None, caption=None):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, TITLE_H], fill=(32, 32, 32))
    d.text((18, 6), "Windows PowerShell  -  KernelLab", font=UI, fill=(220, 220, 220))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        x = W - 120 + i * 36
        d.ellipse([x, 12, x + 20, 32], fill=c)
    visible = list(lines[top:top + ROWS])
    if typed is not None:
        visible = visible[-(ROWS - 1):] + [(typed + "_", C_PROMPT)] \
            if len(visible) >= ROWS else visible + [(typed + "_", C_PROMPT)]
    y = TITLE_H + 12
    for text, color in visible:
        d.text((24, y), text, font=MONO, fill=color)
        y += LINE_H
    if caption:
        d.rectangle([0, H - CAP_H, W, H], fill=(20, 60, 110))
        d.text((24, H - CAP_H + 16), caption, font=UI, fill=(255, 255, 255))
    return img


def card(title, bullets, caption=None, subtitle=None):
    img = Image.new("RGB", (W, H), (16, 24, 38))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 24, H], fill=(0, 114, 178))
    y = 110
    d.text((100, y), title, font=H1, fill=(255, 255, 255))
    y += 110
    if subtitle:
        d.text((100, y), subtitle, font=H2, fill=(120, 190, 240))
        y += 90
    y += 20
    for b in bullets:
        d.text((100, y), "•", font=BODY, fill=(230, 159, 0))
        d.text((150, y), b, font=BODY, fill=(235, 235, 235))
        y += 72
    if caption:
        d.rectangle([0, H - CAP_H, W, H], fill=(20, 60, 110))
        d.text((24, H - CAP_H + 16), caption, font=UI, fill=(255, 255, 255))
    return img


def picture(path: Path, caption=None):
    img = Image.new("RGB", (W, H), (255, 255, 255))
    pic = Image.open(path).convert("RGB")
    box_h = H - CAP_H - 40
    scale = min((W - 80) / pic.width, box_h / pic.height)
    pic = pic.resize((int(pic.width * scale), int(pic.height * scale)), Image.LANCZOS)
    img.paste(pic, ((W - pic.width) // 2, 20 + (box_h - pic.height) // 2))
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - CAP_H, W, H], fill=(20, 60, 110))
    d.text((24, H - CAP_H + 16), caption or f"docs/img/{path.name}", font=UI,
           fill=(255, 255, 255))
    return img


# ---------------------------------------------------------------- saída ------
class Out:
    def __init__(self, path: Path):
        self.w = imageio.get_writer(str(path), fps=FPS, codec="libx264", quality=8,
                                    pixelformat="yuv420p", macro_block_size=None)
        self.frames = 0

    def hold(self, img, seconds):
        arr = np.asarray(img)
        for _ in range(max(1, round(seconds * FPS))):
            self.w.append_data(arr)
            self.frames += 1

    def close(self):
        self.w.close()


def run(args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env,
                       shell=isinstance(args, str))
    return (r.stdout + r.stderr).rstrip("\n").split("\n")


# ------------------------------------------------------------- terminal ------
def terminal(out: Out, commands, captions_on: bool):
    history = []          # (texto, cor)
    top = 0

    def cap(text):
        return text if captions_on else None

    for c in commands:
        shown = PROMPT + c["show"]
        # digitação
        for k in range(0, len(c["show"]) + 1, 3):
            out.hold(base_terminal(history, top, PROMPT + c["show"][:k], cap(c["caption"])),
                     1 / FPS)
        out.hold(base_terminal(history, top, shown, cap(c["caption"])), 0.4)
        history.append((shown, C_PROMPT))
        start = len(history)
        output = run(c["run"])
        # revelação rápida
        for i in range(0, len(output), 10):
            history.extend((t, line_color(t)) for t in output[i:i + 10])
            top = max(0, len(history) - ROWS)
            out.hold(base_terminal(history, top, None, cap(c["caption"])), 1 / FPS)
        history.append(("", FG))
        top = max(0, len(history) - ROWS)
        out.hold(base_terminal(history, top, None, cap(c["caption"])), 0.5)

        views = c.get("views", [])
        if not views:
            out.hold(base_terminal(history, top, None, cap(c["caption"])), c["hold"])
            continue
        scroll_s = 0.8
        spare = max(1.0, c["hold"] - scroll_s * len(views))
        total_w = sum(v[1] for v in views)
        for marker, weight, vcap in views:
            idx = next((i for i in range(start, len(history))
                        if marker in history[i][0]), start)
            target = min(max(0, idx - 1), max(0, len(history) - ROWS))
            frames = int(scroll_s * FPS)
            for f in range(1, frames + 1):
                t = top + (target - top) * (f / frames)
                out.hold(base_terminal(history, int(round(t)), None, cap(vcap)), 1 / FPS)
            top = target
            out.hold(base_terminal(history, top, None, cap(vcap)), spare * weight / total_w)
    return history


# ----------------------------------------------------------------- vídeo -----
def build(path: Path, captions_on: bool):
    out = Out(path)
    marks = []

    def mark(name):
        t = out.frames / FPS
        marks.append(f"{int(t // 60)}:{int(t % 60):02d}  {name}")

    cap = (lambda t: t) if captions_on else (lambda t: None)

    mark("Problema da MedControl")
    out.hold(card(
        "KernelLab", [
            "Atraso no processamento de alarmes e aumento do tempo de resposta",
            "Disputa pela CPU e processos de baixa prioridade esperando demais",
            "Elevado número de faltas de página",
            "Concorrência e acesso não autorizado a dispositivos",
        ], cap("O problema da MedControl: um servidor, uma CPU e vários processos competindo"),
        subtitle="Simulador de CPU, memória e dispositivos - cenário MedControl"), 25)

    mark("Estrutura do projeto e opções")
    terminal(out, [
        {"show": "dir src /b", "run": "dir src /b", "hold": 3,
         "caption": "Estrutura: escalonadores, memória, dispositivos, métricas e gráficos"},
        {"show": "python src/main.py --help", "run": [str(PY), "src/main.py", "--help"],
         "hold": 12,
         "caption": "Quantum, frames, sequência de páginas e processos são configuráveis"},
    ], captions_on)

    mark("Escalonamento de CPU (Gantt e comparação)")
    terminal(out, [{
        "show": "python src/main.py --only cpu --compact --no-charts",
        "run": [str(PY), "src/main.py", "--only", "cpu", "--compact", "--no-charts"],
        "hold": 62, "caption": "Escalonamento da CPU",
        "views": [
            ("--- FCFS ---", 3, "FCFS: por ordem de chegada; o alarme (P4) só roda no instante 21"),
            ("--- Round Robin", 3, "Round Robin (quantum 3): fatias iguais; o alarme roda no instante 9"),
            ("--- Prioridade ---", 2, "Prioridade: o alarme passa na frente, mas espera o P1 terminar"),
            ("--- Prioridade (preemptiva)", 3, "Variante extra com preempção: o alarme entra na CPU ao chegar (espera 0)"),
            ("ETAPA 2 - COMPARA", 4, "Comparação: espera, retorno, resposta, trocas de contexto e justiça"),
            ("Entre os 4 algoritmos", 4, "Respostas: menor espera, melhor resposta, alarme, starvation e justiça"),
        ]}], captions_on)
    mark("Gráfico de tempos médios")
    out.hold(picture(ROOT / "docs" / "img" / "tempos_medios.png",
                     cap("Gráfico: comparação dos tempos médios por algoritmo") or
                     "docs/img/tempos_medios.png"), 8)

    mark("Memória: FIFO, LRU, Optimal")
    terminal(out, [{
        "show": "python src/main.py --only memory --no-charts",
        "run": [str(PY), "src/main.py", "--only", "memory", "--no-charts"],
        "hold": 29, "caption": "Substituição de páginas com 4 frames",
        "views": [
            ("--- FIFO ---", 3, "FIFO: 5 hits e 12 faltas (70,6%)"),
            ("--- LRU ---", 3, "LRU: 7 hits e 10 faltas (58,8%)"),
            ("--- Optimal ---", 2, "Optimal (só referência): 10 hits e 7 faltas (41,2%)"),
            ("Algoritmo | Hits", 3, "Comparação: LRU é o melhor algoritmo implementável"),
            ("Faltas x quantidade", 2, "Efeito da quantidade de frames (configurável)"),
        ]}], captions_on)

    mark("Dispositivos: matriz e mutex")
    terminal(out, [{
        "show": "python src/main.py --only devices",
        "run": [str(PY), "src/main.py", "--only", "devices"],
        "hold": 29, "caption": "Controle de acesso a dispositivos",
        "views": [
            ("Matriz de controle", 3, "Matriz de controle de acesso: cada processo só usa o que lhe cabe"),
            ("--- Disco concorrente: COM", 4, "Com mutex e fila FIFO: um por vez, 0 violações; P4 é negado"),
            ("--- Disco concorrente: SEM", 4, "Sem mutex: acessos se sobrepõem (violações de exclusão mútua)"),
        ]}], captions_on)

    mark("Testes automatizados")
    terminal(out, [{
        "show": "python -m pytest -q",
        "run": [str(PY), "-m", "pytest", "-q"], "hold": 5,
        "caption": "37 testes automatizados dos algoritmos"}], captions_on)
    mark("Recomendação final")
    out.hold(card(
        "Recomendação", [
            "CPU: prioridade com preempção (alarme sem espera; menor espera média)",
            "Memória: LRU (10 faltas contra 12 do FIFO)",
            "Dispositivos: fila FIFO com mutex + matriz de acesso",
            "Limitação: backup (P5) pode esperar demais - melhoria: aging",
        ], cap("Recomendação final e limitações")), 20)
    out.close()
    return out.frames / FPS, marks


if __name__ == "__main__":
    for name, caps in (("kernellab_demo_legendado.mp4", True),
                       ("kernellab_demo_sem_legendas.mp4", False)):
        dur, marks = build(OUT / name, caps)
        print(f"{name}: {dur:.1f} s")
    print("\n".join(marks))
