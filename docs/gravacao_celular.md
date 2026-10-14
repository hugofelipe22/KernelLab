# Guia de gravação com o celular — do zero ao link do vídeo

Meta: vídeo de **até 4 minutos** mostrando o simulador **rodando** (exigência do
enunciado). O script `demo.ps1` avança a demonstração uma tela por vez a cada ENTER,
então você controla o ritmo e não precisa rolar a tela nem digitar nada na hora.

---

## Parte 1 — Preparar o computador (10 min, antes de gravar)

1. Abra o **Windows PowerShell** (tecla Windows, digite `PowerShell`). Se preferir,
   use o terminal do VS Code, mas o PowerShell separado fica mais limpo.
2. Entre na pasta e libere scripts nessa janela:
   ```powershell
   cd C:\Users\Camila\Projetos\KernelLab
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   ```
3. Confirme que está tudo certo (uma vez):
   ```powershell
   .venv\Scripts\python.exe -m pytest -q
   ```
   Esperado: `37 passed`.
4. **Aumente a fonte** para o celular enxergar: clique com o botão direito na barra
   de título > Propriedades > Fonte > tamanho **24 a 28**, ou segure `Ctrl` e role a
   roda do mouse (Windows Terminal). Maximize a janela.
5. **Fundo escuro** e brilho do monitor no máximo (evita reflexo e moiré na câmera).
6. Feche tudo que não for usar e **ative "Não perturbe"** no Windows (`Win + N`,
   ou Configurações > Sistema > Assistência de foco) e no celular.
7. Ensaie rodando o script uma vez inteiro:
   ```powershell
   .\demo.ps1
   ```
   Aperte ENTER para avançar. São cerca de 25 toques. O gráfico abre numa janela do
   Windows (Fotos); feche-a com `Alt + F4` e volte ao PowerShell.

> Para treinar sem abrir o gráfico: `.\demo.ps1 -SemImagem`

---

## Parte 2 — Preparar o celular

1. Coloque o celular **na horizontal** (paisagem), apoiado em um livro/suporte, de
   frente para a tela e **fixo** (nada de segurar na mão).
2. Câmera em **1080p, 30 fps**. Limpe a lente.
3. Enquadre a tela inteira com um pouco de margem. Se o texto estiver pequeno,
   aumente a fonte do terminal, não aproxime demais.
4. Ambiente com pouca luz batendo no monitor (sem reflexo de janela/lâmpada).
5. Faça um teste de 10 segundos, assista e confira: texto legível? áudio da sua voz
   claro? Só então grave de verdade.
6. Fale perto do celular, em ambiente silencioso.

---

## Parte 3 — Roteiro por tela (grave direto; ENTER avança)

Tempo total alvo: **3 min 40 s**. As falas são sugestão; use as suas palavras.

| # | Tela do `demo.ps1` | Tempo | O que falar |
|---|---|---|---|
| 1 | Abertura "KernelLab" | 0:00 · 15 s | "Oi, eu sou **[seu nome]**. A MedControl monitora equipamentos médicos em um servidor com uma só CPU, onde rodam monitoramento, alarme, telemetria, relatórios e backup. Os problemas são alarmes atrasados, muitas faltas de página e disputa por dispositivos. Para estudar isso, criei o **KernelLab**, um simulador de CPU, memória e dispositivos." |
| 2 | Estrutura (`dir src`, `dir data`) | 0:15 · 10 s | "O projeto tem um módulo para escalonadores, um para memória, um para dispositivos e um para métricas. Os dados dos processos ficam em JSON, então posso mudar processos e quantum sem mexer no código." |
| 3 | Tela do comando CPU → ENTER | 0:25 | (aperte ENTER para executar) |
| 4 | Etapa 1 + tabela de processos | 0:25 · 10 s | "Estes são os seis processos: o P4, alarme crítico, tem prioridade zero, a mais alta; o P5, backup, tem a mais baixa." |
| 5 | FCFS | 0:35 · 12 s | "No **FCFS**, por ordem de chegada, o alarme só roda no instante 21 e espera 18 unidades, atrás de relatório e telemetria." |
| 6 | SJF | 0:47 · 8 s | "O **SJF** executa o menor job primeiro: a espera média cai para 10,67 e o alarme espera 5." |
| 7 | Round Robin | 0:55 · 12 s | "O **Round Robin**, com quantum 3, dá fatias iguais: o alarme roda no instante 9. É o mais justo, mas teve 13 trocas de contexto e a maior espera média." |
| 8 | Prioridade | 1:07 · 8 s | "Na **Prioridade**, o alarme passa na frente, mas precisa esperar o P1 terminar, porque não há preempção." |
| 9 | Prioridade preemptiva | 1:15 · 10 s | "Como variante extra, com **preempção**, o alarme entra na CPU assim que chega: espera zero." |
| 10 | Etapa 2: comparação | 1:25 · 20 s | "Comparando: menor espera média, SJF e Prioridade; melhor resposta e justiça, Round Robin; alarme mais rápido, a prioridade preemptiva; maior risco de starvation, o backup P5, que espera 24." |
| 11 | Gráfico (abre a imagem) | 1:45 · 8 s | "Aqui o gráfico comparando espera, retorno e resposta médios." Depois feche a imagem (`Alt + F4`). |
| 12 | Memória: título | 1:53 · 6 s | "Na memória, quatro frames e a sequência de páginas do enunciado." |
| 13 | FIFO | 1:59 · 8 s | "No **FIFO**, são 5 hits e 12 faltas, 70,6%. Ele expulsa a página mais antiga mesmo que ela volte logo." |
| 14 | LRU | 2:07 · 8 s | "No **LRU**, 7 hits e 10 faltas, 58,8%: ele usa o passado recente para prever o futuro." |
| 15 | Optimal | 2:15 · 6 s | "O **Optimal** é só referência, porque precisa conhecer o futuro: 10 hits e 7 faltas." |
| 16 | Comparação de memória | 2:21 · 10 s | "O melhor algoritmo implementável é o LRU. A diferença vem de quem cada um escolhe expulsar." |
| 17 | Faltas x frames | 2:31 · 6 s | "E o número de frames é configurável: com 5 ou mais, só restam as 5 faltas obrigatórias." |
| 18 | Dispositivos: matriz | 2:37 · 12 s | "Esta é a **matriz de controle de acesso**: cada processo só tem permissão nos dispositivos que usa; só o backup e o alarme pedem acesso exclusivo." |
| 19 | Com mutex | 2:49 · 12 s | "**Com mutex e fila FIFO**, os processos entram um de cada vez: máximo de um acesso simultâneo, zero violações. O P4 tenta usar o disco sem permissão e é negado." |
| 20 | Sem mutex | 3:01 · 10 s | "**Sem mutex**, os acessos se sobrepõem e aparecem violações de exclusão mútua." |
| 21 | Testes (ENTER, executa) | 3:11 · 8 s | "E há 37 testes automatizados dos algoritmos, todos passando." |
| 22 | Tela final "Fim" | 3:19 · 20 s | "Minha recomendação: **prioridade com preempção**, porque o alarme é atendido sem espera e a espera média é a menor; **LRU** na memória, com 10 faltas contra 12 do FIFO; e fila com **mutex** e matriz de acesso nos dispositivos. A limitação é que o backup pode esperar demais, e a melhoria seria usar *aging*. O código e o relatório estão no GitHub. Obrigado!" |

Dicas de fala:
- Espere 1 segundo na tela antes de começar a falar; deixe a imagem "assentar".
- Se errar, **continue** — ou grave a partir da tela seguinte e junte depois.
- Se passar de 4 minutos, encurte as telas 4, 8 e 17.

---

## Parte 4 — Depois de gravar

1. Passe o vídeo do celular para o computador (cabo USB, Google Fotos, WhatsApp Web,
   etc.) ou envie direto do celular para o YouTube.
2. Se precisar cortar: Clipchamp (Windows 11) ou o editor de Fotos do celular.
3. **YouTube**: studio.youtube.com > **Criar** > **Enviar vídeo** > escolha o arquivo
   > título "KernelLab - Simulador de SO (MedControl)" > "Não, não é conteúdo
   para crianças" > em **Visibilidade** escolha **Não listado** > Publicar > copie o
   link.
4. Abra o link em uma **janela anônima** para confirmar que funciona sem login.

---

## Parte 5 — Fechar a entrega

1. **Colocar o link do vídeo** em dois lugares:
   - `README.md`, no topo: troque `[PREENCHER: link do vídeo]`.
   - `docs\gerar_relatorio.py`: edite `VIDEO_URL`, `REPO_URL` e `AUTOR` (topo do
     arquivo) e rode:
     ```powershell
     .venv\Scripts\python.exe docs\gerar_relatorio.py
     ```
2. **Subir para o GitHub** (crie antes um repositório **público** vazio, sem README):
   ```powershell
   git add .
   git commit -m "KernelLab: simulador de CPU, memoria e dispositivos"
   git branch -M main
   git remote add origin https://github.com/SEU_USUARIO/KernelLab.git
   git push -u origin main
   ```
3. **Teste do avaliador**: clone em outra pasta e rode do zero:
   ```powershell
   cd $HOME\Desktop
   git clone https://github.com/SEU_USUARIO/KernelLab.git teste
   cd teste
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   python -m pytest -q
   python src/main.py
   ```
4. **Entregue os três itens**: relatório em PDF (`docs\relatorio_tecnico.pdf`), link
   do GitHub e link do vídeo.

---

## Se algo der errado

| Problema | O que fazer |
|---|---|
| `demo.ps1 não pode ser carregado` | Rode `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` e tente de novo |
| Letras estranhas/acentos quebrados | Use o Windows Terminal ou o terminal do VS Code; fonte Consolas |
| Texto pequeno demais no celular | Aumente a fonte do terminal para 28+ |
| Tela não cabe uma "tela" do script | Diminua um pouco a fonte; cada tela tem no máximo ~30 linhas |
| Gráfico não abre | Abra manualmente `docs\img\tempos_medios.png` |
| Passou de 4 minutos | Corte as telas 8 e 17 e fale mais rápido nas 5 a 7 |
