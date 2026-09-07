# TSOFT AI Dev Kit - Instalador Windows
#
# Verifica requisitos, comprueba la integridad del paquete y prepara las
# carpetas de trabajo. NO modifica hooks.json: sus rutas son relativas al
# proyecto y no hay nada que resolver por maquina.
#
# Todo el archivo esta en ASCII a proposito. PowerShell 5.1 lee los .ps1 sin
# BOM como ANSI, asi que cualquier acento se muestra corrupto; y ponerle BOM
# rompe otras cosas. Sin caracteres especiales, el problema no existe.

$ErrorActionPreference = "Stop"
$KIT_HOME = $PSScriptRoot

$errores = 0

function Fallo([string]$mensaje) {
    Write-Host "ERROR: $mensaje" -ForegroundColor Red
    $script:errores++
}

function Ok([string]$mensaje) {
    Write-Host "OK  $mensaje" -ForegroundColor Green
}

function Invoke-Nativo {
    # Aisla el comando externo: con $ErrorActionPreference = 'Stop', lo que un
    # .exe escriba en stderr se convierte en error terminante en PowerShell 5.1.
    param([string]$Exe, [string[]]$Argumentos = @())
    $previo = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $bruto = & $Exe @Argumentos 2>&1
        $codigo = $LASTEXITCODE
    } catch {
        return New-Object psobject -Property @{ Codigo = 127; Texto = "$($_.Exception.Message)" }
    } finally {
        $ErrorActionPreference = $previo
    }
    $lineas = @()
    foreach ($item in $bruto) { $lineas += [string]$item }
    return New-Object psobject -Property @{
        Codigo = $codigo
        Texto  = ($lineas -join [Environment]::NewLine)
    }
}

Write-Host "TSOFT AI Dev Kit - Instalacion" -ForegroundColor Cyan
Write-Host "KIT_HOME: $KIT_HOME"
Write-Host ""

# ---------------------------------------------------------------------------
# 1. Python. Va PRIMERO: todo lo que sigue lo necesita, y si falta, cualquier
#    otro error que aparezca antes manda a debuggear al lugar equivocado.
# ---------------------------------------------------------------------------
Write-Host "1. Requisitos" -ForegroundColor White

$r = Invoke-Nativo 'py' @('-3', '--version')
if ($r.Codigo -ne 0) {
    Write-Host "ERROR: no encontre Python 3." -ForegroundColor Red
    Write-Host "       Instalalo desde https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "       Marca 'Add python.exe to PATH' durante la instalacion." -ForegroundColor Red
    Write-Host "       Detalle: $($r.Texto)" -ForegroundColor DarkGray
    exit 1
}

# El kit necesita 3.9 como minimo: metrics_lib importa zoneinfo, que no existe
# en 3.8. Ahi degrada a la zona del sistema y los cortes semanales del reporte
# pueden caer en otro dia segun la maquina.
$r = Invoke-Nativo 'py' @('-3', '-c', 'import sys; print(sys.version_info[0]); print(sys.version_info[1])')
if ($r.Codigo -ne 0) {
    Fallo "no pude leer la version de Python: $($r.Texto)"
} else {
    $partes = $r.Texto -split "`r?`n" | Where-Object { $_ -match '^\d+$' }
    if ($partes.Count -ge 2) {
        $mayor = [int]$partes[0]
        $menor = [int]$partes[1]
        if ($mayor -lt 3 -or ($mayor -eq 3 -and $menor -lt 9)) {
            Write-Host "ERROR: Python $mayor.$menor es muy viejo. El kit necesita 3.9 o superior." -ForegroundColor Red
            exit 1
        }
        Ok "Python $mayor.$menor"
    } else {
        Fallo "no pude interpretar la version de Python"
    }
}

# tar viene con Windows 10 1803+. Solo hace falta para empaquetar, no para usar.
$r = Invoke-Nativo 'tar' @('--version')
if ($r.Codigo -ne 0) {
    Write-Host "AVISO: no encontre tar.exe. No afecta el uso del kit," -ForegroundColor Yellow
    Write-Host "       solo el empaquetado con empaquetar.ps1." -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# 2. Integridad del paquete
#    Antes este paso reescribia hooks.json para resolver __KIT_HOME__. Ese
#    placeholder ya no existe: hooks.json usa rutas relativas al proyecto. Lo
#    unico util que queda es comprobar que el archivo llego entero.
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "2. Integridad del kit" -ForegroundColor White

$hooksPath = Join-Path $KIT_HOME ".codex\hooks.json"

if (-not (Test-Path -LiteralPath $hooksPath)) {
    Write-Host "ERROR: falta .codex\hooks.json. El paquete llego incompleto." -ForegroundColor Red
    Write-Host "       Redescarga el kit; no intentes crearlo a mano." -ForegroundColor Red
    exit 1
}

# BOM: PowerShell 5.1 lo agrega si alguien uso Set-Content -Encoding UTF8, y el
# parser JSON de Codex lo rechaza con "expected value at line 1 column 1".
$bytes = [System.IO.File]::ReadAllBytes($hooksPath)
if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
    Fallo "hooks.json tiene BOM. Codex lo va a rechazar al arrancar."
}

$hooks = $null
try {
    $hooks = Get-Content -LiteralPath $hooksPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Ok "hooks.json valido"
} catch {
    Write-Host "ERROR: hooks.json no es JSON valido." -ForegroundColor Red
    Write-Host "       $_" -ForegroundColor Red
    Write-Host "       El paquete llego corrupto. Redescarga el kit." -ForegroundColor Red
    exit 1
}

# Cada hook que declara hooks.json tiene que existir en disco. Si falta uno,
# Codex tira 'hook exited with code 1' en cada llamada a herramienta y el
# mensaje no dice cual es el archivo ausente.
$texto = Get-Content -LiteralPath $hooksPath -Raw -Encoding UTF8
$declarados = @()
foreach ($m in [regex]::Matches($texto, '([a-z_]+\.py)')) {
    if ($declarados -notcontains $m.Groups[1].Value) { $declarados += $m.Groups[1].Value }
}
$faltantes = @()
foreach ($nombre in $declarados) {
    if (-not (Test-Path -LiteralPath (Join-Path $KIT_HOME ".codex\hooks\$nombre"))) {
        $faltantes += $nombre
    }
}
if ($faltantes.Count -gt 0) {
    Fallo "hooks.json declara hooks que no estan en el paquete: $($faltantes -join ', ')"
} else {
    Ok "$($declarados.Count) hooks presentes"
}

if ($texto.Contains('__KIT_HOME__')) {
    Fallo "hooks.json todavia tiene __KIT_HOME__. Ese paquete es de una version vieja."
}

# ---------------------------------------------------------------------------
# 3. Carpetas de trabajo
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "3. Carpetas" -ForegroundColor White

$carpetas = @(
    "tsoft-dev\metrics\sesiones",
    "tsoft-dev\reportes\ejecuciones",
    "docs"
)
foreach ($c in $carpetas) {
    $ruta = Join-Path $KIT_HOME $c
    if (-not (Test-Path -LiteralPath $ruta)) {
        New-Item -ItemType Directory -Path $ruta -Force | Out-Null
        Ok "creada: $c"
    }
}

# ---------------------------------------------------------------------------
# 4. AGENTS.md
#    El kit trae una plantilla en plantillas\AGENTS.md, con la seccion
#    "Convencion de features" ya completa (de ella depende que la medicion
#    funcione). Si el proyecto ya tiene un AGENTS.md propio, no se pisa:
#    son las reglas del proyecto, no algo que el kit deba reemplazar.
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "4. AGENTS.md" -ForegroundColor White

$agentsDestino   = Join-Path $KIT_HOME "AGENTS.md"
$agentsPlantilla = Join-Path $KIT_HOME "plantillas\AGENTS.md"

if (Test-Path -LiteralPath $agentsDestino) {
    Ok "ya existe un AGENTS.md en la raiz, no se toca"
} elseif (Test-Path -LiteralPath $agentsPlantilla) {
    Copy-Item -LiteralPath $agentsPlantilla -Destination $agentsDestino
    Ok "AGENTS.md creado desde la plantilla del kit -- falta completarlo (paso 2 de los pasos manuales)"
} else {
    Write-Host "AVISO: no encontre plantillas\AGENTS.md en el paquete. Crealo a mano." -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# 5. Proteccion de los datos de medicion
#    El kit se instala dentro del repo del cliente. metrics/ guarda los prompts
#    y comandos reales de cada sesion. Se avisa, no se escribe: el .gitignore
#    del repo es del cliente, no del kit.
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "5. Datos de medicion" -ForegroundColor White

$r = Invoke-Nativo 'git' @('rev-parse', '--is-inside-work-tree')
if ($r.Codigo -eq 0) {
    # Caso mas grave, chequeado primero: si el archivo YA esta trackeado,
    # agregarlo a .gitignore o .git\info\exclude no hace nada -- Git lo sigue
    # versionando igual. Hace falta sacarlo del indice con "git rm --cached".
    # check-ignore --no-index (mas abajo) no detecta esto: solo evalua el
    # patron, no si el archivo ya esta en el indice.
    $yaTrackeadas = @()
    foreach ($ruta in @('tsoft-dev/metrics', 'tsoft-dev/reportes')) {
        $chk = Invoke-Nativo 'git' @('ls-files', '--', $ruta)
        if ($chk.Codigo -eq 0 -and $chk.Texto.Trim()) { $yaTrackeadas += $ruta }
    }
    if ($yaTrackeadas.Count -gt 0) {
        Write-Host "AVISO CRITICO: estas carpetas YA ESTAN TRACKEADAS en git:" -ForegroundColor Red
        foreach ($t in $yaTrackeadas) { Write-Host "         $t" -ForegroundColor Red }
        Write-Host "       Agregarlas a .gitignore o .git\info\exclude NO alcanza: Git ya" -ForegroundColor Red
        Write-Host "       las viene versionando. Sacalas del indice (esto NO borra los" -ForegroundColor Red
        Write-Host "       archivos locales, solo deja de trackearlos):" -ForegroundColor Red
        Write-Host ""
        Write-Host "         git rm -r --cached tsoft-dev/metrics tsoft-dev/reportes" -ForegroundColor Cyan
        Write-Host ""
    }

    $desprotegidas = @()
    foreach ($ruta in @('tsoft-dev/metrics/', 'tsoft-dev/reportes/')) {
        # --no-index para que un archivo ya trackeado no enmascare la regla.
        $chk = Invoke-Nativo 'git' @('check-ignore', '-q', '--no-index', $ruta)
        if ($chk.Codigo -ne 0) { $desprotegidas += $ruta }
    }
    if ($desprotegidas.Count -gt 0) {
        Write-Host "AVISO: estas carpetas NO estan en el .gitignore del repo:" -ForegroundColor Yellow
        foreach ($d in $desprotegidas) { Write-Host "         $d" -ForegroundColor Yellow }
        Write-Host "       Guardan los prompts y comandos reales de cada sesion." -ForegroundColor Yellow
        Write-Host "       Agregalas al .gitignore, o al .git\info\exclude si no" -ForegroundColor Yellow
        Write-Host "       queres tocar el .gitignore del proyecto:" -ForegroundColor Yellow
        Write-Host ""
        Write-Host '         Add-Content .git\info\exclude "tsoft-dev/metrics/"' -ForegroundColor Cyan
        Write-Host '         Add-Content .git\info\exclude "tsoft-dev/reportes/"' -ForegroundColor Cyan
    } elseif ($yaTrackeadas.Count -eq 0) {
        Ok "metrics/ y reportes/ estan fuera del control de versiones"
    }
} else {
    Write-Host "AVISO: esto no parece un repo git. Si lo vas a versionar," -ForegroundColor Yellow
    Write-Host "       acordate de excluir tsoft-dev/metrics/ y tsoft-dev/reportes/." -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# Resultado
# ---------------------------------------------------------------------------
Write-Host ""
if ($errores -gt 0) {
    Write-Host "Instalacion incompleta: $errores problema(s). Resolvelos antes de usar el kit." -ForegroundColor Red
    exit 1
}

$configGlobal = Join-Path $env:USERPROFILE ".codex\config.toml"

Write-Host "PASOS MANUALES REQUERIDOS:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. CONFIAR EL PROYECTO (obligatorio)" -ForegroundColor White
Write-Host ""
Write-Host "   La forma facil, recomendada:" -ForegroundColor Green
Write-Host "   Abri Codex en esta carpeta. Va a preguntar:"
Write-Host '     "Do you trust the contents of this directory?"'
Write-Host '   Responde "1. Yes, continue" y Codex lo registra solo.'
Write-Host ""
Write-Host "   Si preferis hacerlo a mano, va en el config GLOBAL del usuario:"
Write-Host "     $configGlobal" -ForegroundColor Cyan
Write-Host ""
Write-Host "   OJO: ese archivo NO es el mismo que" -ForegroundColor Yellow
Write-Host "   $KIT_HOME\.codex\config.toml" -ForegroundColor Yellow
Write-Host "   Son dos archivos distintos con el mismo nombre. Si pones el" -ForegroundColor Yellow
Write-Host "   trust_level en el del proyecto, Codex falla al arrancar con" -ForegroundColor Yellow
Write-Host '   "invalid type: string, expected a boolean".' -ForegroundColor Yellow
Write-Host ""
Write-Host "   Va al final del archivo global, con la ruta entre comillas:"
Write-Host ('     [projects.''{0}'']' -f $KIT_HOME)
Write-Host '     trust_level = "trusted"'
Write-Host ""
Write-Host "2. COMPLETAR EL AGENTS.md (obligatorio)" -ForegroundColor White
Write-Host "   Los agentes lo leen antes de trabajar. Sin eso trabajan a ciegas."
Write-Host "   Podes pedirle a Codex que lo genere:"
Write-Host '     "Analiza la estructura de este repositorio y completa el AGENTS.md"'
Write-Host ""
Write-Host "3. VERIFICAR QUE LA MEDICION ANDA" -ForegroundColor White
Write-Host "   py -3 -m unittest discover -s tsoft-dev\scripts\tests"
Write-Host "   Tiene que decir OK."
Write-Host ""
Write-Host "4. (Opcional, solo si trabajas por terminal) Confiar los hooks:" -ForegroundColor White
Write-Host "   Abri Codex y ejecuta /hooks"
Write-Host "   En la extension de VS Code no hace falta: el reconciliador cubre"
Write-Host "   las dos vias y es la fuente del reporte del equipo."
Write-Host ""
Write-Host "Instalacion completa. Detalle en MANUAL-DEV.md" -ForegroundColor Cyan
exit 0
