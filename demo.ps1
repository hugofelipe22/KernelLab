# KernelLab - demonstracao passo a passo para gravar o video.
# Cada ENTER avanca uma "tela". Nada rola sozinho: voce controla o ritmo da fala.
#
# Como usar (na pasta do projeto):
#   .\demo.ps1
# Se o PowerShell bloquear scripts, rode antes (vale so para essa janela):
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

param([switch]$SemImagem)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$root = $PSScriptRoot
Set-Location $root
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

function Espera($msg) {
    Write-Host ""
    Write-Host $msg -ForegroundColor DarkGray
    [void](Read-Host)
}

# Executa um comando do simulador e mostra a saida dividida em telas.
function Secao($rotulo, $mostrado, $argumentos) {
    Clear-Host
    Write-Host "[$rotulo]" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "PS> $mostrado" -ForegroundColor Yellow
    Espera "ENTER para executar"

    $linhas = & $py @argumentos 2>&1 | ForEach-Object { "$_" }
    $linhas = $linhas | Where-Object { $_ -notmatch '^=+$' }

    $blocos = New-Object System.Collections.ArrayList
    $atual = New-Object System.Collections.ArrayList
    foreach ($l in $linhas) {
        if ($atual.Count -eq 0 -and $l.Trim() -eq '') { continue }
        if ($l -match '^(--- |ETAPA |Algoritmo \| Hits|Faltas x)' -and $atual.Count -gt 0) {
            [void]$blocos.Add($atual)
            $atual = New-Object System.Collections.ArrayList
        }
        [void]$atual.Add($l)
    }
    if ($atual.Count -gt 0) { [void]$blocos.Add($atual) }

    $i = 0
    foreach ($b in $blocos) {
        $i++
        Clear-Host
        foreach ($l in $b) { Write-Host $l }
        Espera "[$i/$($blocos.Count)] ENTER para continuar"
    }
}

# ---- 0. Abertura -------------------------------------------------------------
Clear-Host
Write-Host "KernelLab - Simulador de CPU, memoria e dispositivos" -ForegroundColor Cyan
Write-Host "Cenario: MedControl Systems"
Espera "ENTER para comecar"

# ---- 1. Estrutura ------------------------------------------------------------
Clear-Host
Write-Host "PS> dir src /b" -ForegroundColor Yellow
cmd /c "dir src /b" | Where-Object { $_ -ne "__pycache__" }
Write-Host ""
Write-Host "PS> dir data /b" -ForegroundColor Yellow
cmd /c "dir data /b"
Espera "ENTER para continuar"

# ---- 2. CPU ------------------------------------------------------------------
Secao "ESCALONAMENTO DA CPU" "python src/main.py --only cpu --compact --no-charts" `
    @("src/main.py", "--only", "cpu", "--compact", "--no-charts")

if (-not $SemImagem) {
    Clear-Host
    Write-Host "Abrindo o grafico de tempos medios..." -ForegroundColor Yellow
    Start-Process (Join-Path $root "docs\img\tempos_medios.png")
    Espera "ENTER depois de mostrar o grafico (feche a janela da imagem)"
}

# ---- 3. Memoria --------------------------------------------------------------
Secao "MEMORIA - FIFO, LRU, OPTIMAL" "python src/main.py --only memory --no-charts" `
    @("src/main.py", "--only", "memory", "--no-charts")

# ---- 4. Dispositivos ---------------------------------------------------------
Secao "DISPOSITIVOS - ACESSO E MUTEX" "python src/main.py --only devices" `
    @("src/main.py", "--only", "devices")

# ---- 5. Testes ---------------------------------------------------------------
Clear-Host
Write-Host "[TESTES AUTOMATIZADOS]" -ForegroundColor Cyan
Write-Host ""
Write-Host "PS> python -m pytest -q" -ForegroundColor Yellow
Espera "ENTER para executar"
& $py -m pytest -q
Espera "ENTER para finalizar"

Clear-Host
Write-Host "Fim da demonstracao. Obrigado!" -ForegroundColor Green
