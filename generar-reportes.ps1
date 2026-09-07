# Atajo del TSOFT AI Dev Kit: procesa el consumo y genera el reporte.
#
# Hace los dos pasos, en orden. El reconciliador es el que lee los rollouts de
# Codex y arma features.jsonl; sin el, el reporte se genera sobre datos viejos
# o sobre nada. Antes este script salteaba ese paso.
#
#   .\generar-reportes.ps1                    -> semanal (ultimos 7 dias)
#   .\generar-reportes.ps1 diario
#   .\generar-reportes.ps1 semanal 2026-08-10 -> semana que cierra esa fecha
#   .\generar-reportes.ps1 acumulado          -> todo lo registrado

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('semanal', 'diario', 'acumulado')]
    [string]$Modo = 'semanal',

    [Parameter(Position = 1)]
    [string]$Fecha
)

$ErrorActionPreference = 'Stop'

# Se valida antes de hacer trabajo: el reconciliador tarda, y fallar despues de
# haberlo corrido es tiempo tirado.
if ($Fecha -and $Modo -eq 'acumulado') {
    throw 'El modo acumulado no lleva fecha: incluye todo lo registrado.'
}

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$reconciliador = Join-Path $repoRoot 'tsoft-dev\scripts\reconciliador.py'
$reporte = Join-Path $repoRoot 'tsoft-dev\scripts\reporte_features.py'

foreach ($script in @($reconciliador, $reporte)) {
    if (-not (Test-Path -LiteralPath $script)) {
        throw "No se encontro el script en: $script"
    }
}

Write-Host 'Procesando el consumo desde los rollouts de Codex...' -ForegroundColor Cyan
& py $reconciliador
if ($LASTEXITCODE -ne 0) {
    throw "El reconciliador fallo con codigo $LASTEXITCODE"
}

$argumentos = @($reporte, '--html')
switch ($Modo) {
    'semanal'   { $argumentos += '--semana' }
    'diario'    { $argumentos += '--diario' }
    'acumulado' { }   # sin filtro: todo lo registrado
}
if ($Fecha) {
    $argumentos += @('--fecha', $Fecha)
}

Write-Host ''
Write-Host "Generando reporte $Modo..." -ForegroundColor Cyan
& py @argumentos
if ($LASTEXITCODE -ne 0) {
    throw "La generacion del reporte fallo con codigo $LASTEXITCODE"
}

$html = Join-Path $repoRoot 'tsoft-dev\reportes\features.html'
if (Test-Path -LiteralPath $html) {
    Write-Host ''
    Write-Host "Reporte visual: $html" -ForegroundColor Green
}
