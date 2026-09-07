<#
.SYNOPSIS
    Empaqueta el TSOFT AI Dev Kit en un ZIP distribuible, verificado.

.DESCRIPTION
    El kit vive dentro del repo de un proyecto real. Este script extrae SOLO los
    archivos del kit, desde git (no desde el working tree), y verifica la
    integridad del paquete antes de comprimir.

    Por que desde git y no desde la carpeta:
      Armar el ZIP copiando carpetas mete lo que haya en tu maquina en ese
      momento -- archivos no versionados, datos de medicion con prompts reales,
      copias corruptas. Con `git archive` el paquete es, por construccion,
      identico a lo que esta commiteado.

    Las verificaciones frenan el empaquetado si detectan:
      - CRLF en archivos que Python o bash tienen que leer
      - BOM al inicio de cualquier archivo
      - Mojibake (UTF-8 doblemente codificado)
      - Frontmatter de SKILL.md que no arranca con "---" + LF
      - El placeholder __KIT_HOME__ huerfano
      - Datos de medicion o codigo del cliente dentro del paquete
      - Tests en rojo

.PARAMETER Version
    Etiqueta de version para el nombre del ZIP. Por defecto, la fecha de hoy.

.PARAMETER Salida
    Carpeta donde dejar el ZIP. Por defecto, la raiz del repo.

.PARAMETER SoloVerificar
    Arma el staging y corre las verificaciones, pero no comprime. Util para
    chequear si el repo esta listo para publicar sin generar nada.

.PARAMETER SaltearTests
    No corre la suite de tests. Usalo solo si ya la corriste vos.

.PARAMETER IncluirAgentsMd
    Incluye AGENTS.md en el paquete. APAGADO por defecto: el AGENTS.md de un
    repo real contiene reglas y rutas del proyecto del cliente. Prendelo solo
    si el AGENTS.md de este repo es la plantilla generica del kit.

.EXAMPLE
    .\empaquetar.ps1
    .\empaquetar.ps1 -SoloVerificar
    .\empaquetar.ps1 -Version "1.4.0" -Salida "C:\temp"
#>

[CmdletBinding()]
param(
    [string]$Version,
    [string]$Salida,
    [switch]$SoloVerificar,
    [switch]$SaltearTests,
    [switch]$IncluirAgentsMd
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem

# ---------------------------------------------------------------------------
# Que archivos forman el kit. Allowlist, no blocklist: el repo tiene codigo del
# cliente y una blocklist se olvida de algo tarde o temprano.
# ---------------------------------------------------------------------------
$RutasKit = @(
    '.codex',
    'tsoft-dev/scripts',
    'tsoft-dev/config',
    'plantillas',
    'MANUAL-DEV.md',
    'instalar.ps1',
    'instalar.sh',
    'generar-reportes.ps1',
    'empaquetar.ps1'
)

# Rutas que NUNCA pueden aparecer en el paquete.
$RutasProhibidas = @(
    'tsoft-dev/metrics',
    'tsoft-dev/reportes',
    'node_modules',
    'src',
    'public',
    'dist',
    'gas',
    '.claude',
    '.superpowers',
    '.mcp.json',
    'MEDICION-CONSUMO-IA.md',
    'PENDIENTES-KIT.md'
)

# Extensiones que Python o bash leen y por lo tanto exigen LF.
$ExigenLF = @('.sh', '.py', '.md', '.json', '.toml', '.jsonl')

$errores = New-Object System.Collections.ArrayList
$avisos  = New-Object System.Collections.ArrayList

function Add-Error([string]$msg) { [void]$errores.Add($msg) }
function Add-Aviso([string]$msg) { [void]$avisos.Add($msg) }

function Invoke-Nativo {
    <#
        Ejecuta un comando externo sin que su stderr mate el script.

        En PowerShell 5.1, con $ErrorActionPreference = 'Stop', cualquier cosa
        que un .exe escriba en stderr se convierte en error terminante -- y el
        redireccionamiento 2>$null no lo evita. git escribe en stderr de forma
        rutinaria (por ejemplo, "pathspec did not match" en ls-files), asi que
        cada llamada nativa tiene que aislarse.
    #>
    param(
        [Parameter(Mandatory = $true)][string]$Exe,
        [string[]]$Argumentos = @()
    )
    $previo = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $bruto = & $Exe @Argumentos 2>&1
        $codigo = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previo
    }
    $lineas = @()
    foreach ($item in $bruto) { $lineas += [string]$item }
    return New-Object psobject -Property @{
        Codigo = $codigo
        Salida = $lineas
        Texto  = ($lineas -join [Environment]::NewLine)
    }
}

function Write-Paso([string]$texto) {
    Write-Host ''
    Write-Host "== $texto" -ForegroundColor Cyan
}

# ---------------------------------------------------------------------------
# 0. Contexto
# ---------------------------------------------------------------------------
Write-Paso 'Contexto'

$r = Invoke-Nativo 'git' @('rev-parse', '--show-toplevel')
if ($r.Codigo -ne 0 -or $r.Salida.Count -eq 0) {
    throw 'No estoy dentro de un repositorio git. Corre este script desde el repo del proyecto.'
}
$repo = ($r.Salida[0]).Trim() -replace '/', '\'
Set-Location -LiteralPath $repo

if (-not $Version) { $Version = (Get-Date -Format 'yyyy-MM-dd') }
if (-not $Salida)  { $Salida  = $repo }

$r = Invoke-Nativo 'git' @('rev-parse', '--short', 'HEAD')
if ($r.Codigo -ne 0) { throw "No pude leer el commit actual: $($r.Texto)" }
$commit = ($r.Salida[0]).Trim()
Write-Host "Repo    : $repo"
Write-Host "Commit  : $commit"
Write-Host "Version : $Version"

# ---------------------------------------------------------------------------
# 1. Pre-vuelo: el repo tiene que estar en condiciones de publicar
# ---------------------------------------------------------------------------
Write-Paso 'Pre-vuelo'

# 1a. Cambios sin commitear EN LOS ARCHIVOS DEL KIT. El resto del repo no importa.
$r = Invoke-Nativo 'git' (@('status', '--porcelain', '--') + $RutasKit)
$sucios = @($r.Salida | Where-Object { $_.Trim() -ne '' })
if ($sucios.Count -gt 0) {
    Add-Aviso 'Hay cambios sin commitear en archivos del kit. El ZIP sale del ultimo commit, NO de tu working tree:'
    foreach ($linea in $sucios) { Add-Aviso "    $linea" }
}

# 1b. hooks.json tiene que estar versionado. Si no, git archive lo excluye y el
#     kit se distribuye sin hooks -- o peor, con la copia local de quien empaqueta.
$r = Invoke-Nativo 'git' @('ls-files', '--error-unmatch', '.codex/hooks.json')
if ($r.Codigo -ne 0) {
    Add-Error @'
.codex/hooks.json NO esta versionado.

  git archive solo empaqueta archivos commiteados, asi que el kit saldria SIN
  hooks.json y la medicion no arrancaria en la maquina destino.

  Arreglo (una vez):
    1. Saca la linea ".codex/hooks.json" del .gitignore
    2. git add .codex/hooks.json
    3. git commit -m "versionar hooks.json (rutas relativas, ya no hay placeholder)"

  Estaba gitignoreado porque el diseno original resolvia rutas absolutas por
  maquina. Las rutas ya son relativas: no hay nada que resolver, y no
  versionarlo es lo que permitio que el archivo distribuido divergiera del repo.
'@
}

# 1c. Tests
if ($SaltearTests) {
    Add-Aviso 'Tests salteados por -SaltearTests.'
} else {
    Write-Host 'Corriendo la suite de tests...'
    $r = Invoke-Nativo 'py' @('-3', '-m', 'unittest', 'discover', '-s', 'tsoft-dev/scripts/tests', '-q')
    if ($r.Codigo -ne 0) {
        Add-Error "La suite de tests fallo. No se empaqueta con tests en rojo.`n$($r.Texto)"
    } else {
        $resumen = ($r.Salida | Where-Object { $_ -match 'Ran \d+ test' })
        if ($resumen) { Write-Host "  $resumen" -ForegroundColor Green } else { Write-Host '  OK' -ForegroundColor Green }
    }
}

# ---------------------------------------------------------------------------
# 2. Staging desde git
# ---------------------------------------------------------------------------
Write-Paso 'Extrayendo desde git'

$staging = Join-Path $env:TEMP "tsoft-kit-staging-$([System.Guid]::NewGuid().ToString('N').Substring(0,8))"
$nombreKit = "Kit-Agentes-Dev-$Version"
# El contenido va dentro de una carpeta propia: descomprimir el ZIP no debe
# desparramar .codex/ y tsoft-dev/ en la carpeta donde este parado el usuario.
$kitDir = Join-Path $staging $nombreKit
New-Item -ItemType Directory -Path $kitDir -Force | Out-Null
# $env:TEMP puede venir en formato corto 8.3 (MIGUEL~1.MAI) mientras que
# Get-ChildItem devuelve la ruta larga. Si no se normaliza, el Substring que
# calcula las rutas relativas corta en el lugar equivocado.
$kitDir = (Get-Item -LiteralPath $kitDir).FullName
$staging = (Get-Item -LiteralPath $staging).FullName

$tar = Join-Path $env:TEMP "tsoft-kit-$commit.tar"
try {
    # Solo las rutas del kit que existen en HEAD, para que git archive no falle
    # por un pathspec que todavia no se creo.
    $rutasPresentes = @()
    foreach ($ruta in $RutasKit) {
        $r = Invoke-Nativo 'git' @('cat-file', '-e', "HEAD:$ruta")
        if ($r.Codigo -eq 0) { $rutasPresentes += $ruta }
        else { Add-Aviso "No esta en HEAD, se omite del paquete: $ruta" }
    }
    if ($IncluirAgentsMd) {
        $r = Invoke-Nativo 'git' @('cat-file', '-e', 'HEAD:AGENTS.md')
        if ($r.Codigo -eq 0) { $rutasPresentes += 'AGENTS.md' }
        else { Add-Aviso 'AGENTS.md no esta en HEAD; se pidio incluirlo pero no existe.' }
    } else {
        Add-Aviso 'AGENTS.md NO incluido. Es especifico del proyecto. Usa -IncluirAgentsMd si el de este repo es la plantilla generica.'
    }

    if ($rutasPresentes.Count -eq 0) { throw 'Ninguna ruta del kit existe en HEAD.' }

    $r = Invoke-Nativo 'git' (@('archive', '--format=tar', '-o', $tar, 'HEAD', '--') + $rutasPresentes)
    if ($r.Codigo -ne 0) { throw "git archive fallo (codigo $($r.Codigo)): $($r.Texto)" }

    $r = Invoke-Nativo 'tar' @('-xf', $tar, '-C', $kitDir)
    if ($r.Codigo -ne 0) {
        throw "No se pudo extraer el tar (codigo $($r.Codigo)): $($r.Texto)`nNecesitas tar.exe (viene con Windows 10 1803+)."
    }
} finally {
    if (Test-Path -LiteralPath $tar) { Remove-Item -LiteralPath $tar -Force }
}

$archivos = Get-ChildItem -LiteralPath $kitDir -Recurse -File
Write-Host "$($archivos.Count) archivos extraidos."

# ---------------------------------------------------------------------------
# 3. Verificaciones de integridad
# ---------------------------------------------------------------------------
Write-Paso 'Verificando integridad'

function Rel([string]$full) { return $full.Substring($kitDir.Length).TrimStart('\', '/') }

# 3a. Nada del cliente ni datos de medicion
foreach ($prohibida in $RutasProhibidas) {
    $p = Join-Path $kitDir ($prohibida -replace '/', '\')
    if (Test-Path -LiteralPath $p) {
        Add-Error "El paquete incluye una ruta prohibida: $prohibida"
    }
}

# 3b. CRLF, BOM, mojibake
# El mojibake es UTF-8 leido como Latin-1 y re-codificado. Estas firmas son las
# que aparecen cuando pasa: em-dash, BOM y vocales acentuadas mal convertidas.
$firmasMojibake = @(
    @{ Nombre = 'em-dash doble';  Bytes = [byte[]](0xC3, 0xA2, 0xE2, 0x82, 0xAC) },
    @{ Nombre = 'BOM doble';      Bytes = [byte[]](0xC3, 0xAF, 0xC2, 0xBB, 0xC2, 0xBF) },
    @{ Nombre = 'acento doble';   Bytes = [byte[]](0xC3, 0x83, 0xC2)             }
)

function Contiene-Bytes([byte[]]$heno, [byte[]]$aguja) {
    if ($aguja.Length -eq 0 -or $heno.Length -lt $aguja.Length) { return $false }
    $ultimo = $heno.Length - $aguja.Length
    for ($i = 0; $i -le $ultimo; $i++) {
        $ok = $true
        for ($j = 0; $j -lt $aguja.Length; $j++) {
            if ($heno[$i + $j] -ne $aguja[$j]) { $ok = $false; break }
        }
        if ($ok) { return $true }
    }
    return $false
}

foreach ($archivo in $archivos) {
    $rel = Rel $archivo.FullName
    $bytes = [System.IO.File]::ReadAllBytes($archivo.FullName)
    if ($bytes.Length -eq 0) { continue }

    # BOM
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        Add-Error "BOM al inicio: $rel  (los scripts Python del kit rechazan esa linea)"
    }

    # CRLF donde no va
    if ($ExigenLF -contains $archivo.Extension.ToLower()) {
        if (Contiene-Bytes $bytes ([byte[]](0x0D, 0x0A))) {
            Add-Error "CRLF: $rel  (arreglalo en .gitattributes, no a mano: el checkout te lo revierte)"
        }
    }

    # Mojibake, solo en archivos de texto del kit
    if ($ExigenLF -contains $archivo.Extension.ToLower()) {
        foreach ($firma in $firmasMojibake) {
            if (Contiene-Bytes $bytes $firma.Bytes) {
                Add-Error "Mojibake ($($firma.Nombre)): $rel"
                break
            }
        }
    }

    # Placeholder huerfano. Solo importa en hooks.json: es el unico archivo que
    # el instalador viejo resolvia. En el resto del kit (instalar.ps1,
    # instalar.sh, este mismo script) el texto "__KIT_HOME__" aparece a
    # proposito, en comentarios y en el codigo que rechaza paquetes viejos.
    if ($rel -eq '.codex/hooks.json' -or $rel -eq '.codex\hooks.json') {
        $texto = [System.Text.Encoding]::UTF8.GetString($bytes)
        if ($texto.Contains('__KIT_HOME__')) {
            Add-Error "Contiene __KIT_HOME__: $rel  (hooks.json usa rutas relativas; el placeholder ya no se resuelve)"
        }
    }
}

# 3c. Frontmatter de las skills: tiene que arrancar con "---" + LF
foreach ($skill in (Get-ChildItem -LiteralPath $kitDir -Recurse -Filter 'SKILL.md' -File)) {
    $rel = Rel $skill.FullName
    $b = [System.IO.File]::ReadAllBytes($skill.FullName)
    if ($b.Length -lt 4 -or $b[0] -ne 45 -or $b[1] -ne 45 -or $b[2] -ne 45 -or $b[3] -ne 10) {
        $vistos = if ($b.Length -ge 4) { ($b[0..3] -join ',') } else { '(archivo muy corto)' }
        Add-Error "Frontmatter invalido: $rel  esperaba 45,45,45,10 y encontre $vistos"
    }
}

# 3d. hooks.json tiene que parsear
$hooks = Join-Path $kitDir '.codex\hooks.json'
if (Test-Path -LiteralPath $hooks) {
    try {
        $null = (Get-Content -LiteralPath $hooks -Raw -Encoding UTF8) | ConvertFrom-Json
        Write-Host '  hooks.json parsea OK' -ForegroundColor Green
    } catch {
        Add-Error "hooks.json no parsea como JSON: $($_.Exception.Message)"
    }

    # Las rutas que declara tienen que existir en el paquete
    $texto = Get-Content -LiteralPath $hooks -Raw -Encoding UTF8
    foreach ($m in [regex]::Matches($texto, '([a-z_]+\.py)')) {
        $py = Join-Path $kitDir (Join-Path '.codex\hooks' $m.Groups[1].Value)
        if (-not (Test-Path -LiteralPath $py)) {
            Add-Error "hooks.json referencia un hook que no esta en el paquete: $($m.Groups[1].Value)"
        }
    }
} else {
    Add-Error 'hooks.json no esta en el paquete. Sin el, la medicion no arranca.'
}

# 3e. Los 7 hooks tienen que compilar.
# Se usa ast.parse y no py_compile: py_compile deja un __pycache__ dentro del
# staging y ese directorio terminaria dentro del ZIP.
$hooksDir = Join-Path $kitDir '.codex\hooks'
if (Test-Path -LiteralPath $hooksDir) {
    $pys = Get-ChildItem -LiteralPath $hooksDir -Filter '*.py' -File
    Write-Host "  $($pys.Count) hooks encontrados"
    # py_compile en vez de -c "import ast...": PowerShell 5.1 se come las
    # comillas dobles al pasar el argumento al ejecutable nativo y el snippet
    # llega roto. PYTHONPYCACHEPREFIX manda los .pyc a otro lado para que no
    # quede un __pycache__ dentro del paquete.
    $cachePyc = Join-Path $env:TEMP 'tsoft-kit-pyc'
    $cachePrevio = $env:PYTHONPYCACHEPREFIX
    $env:PYTHONPYCACHEPREFIX = $cachePyc
    try {
        foreach ($py in $pys) {
            $r = Invoke-Nativo 'py' @('-3', '-m', 'py_compile', $py.FullName)
            if ($r.Codigo -ne 0) {
                Add-Error "El hook no compila: $(Rel $py.FullName) -- $($r.Texto)"
            }
        }
    } finally {
        $env:PYTHONPYCACHEPREFIX = $cachePrevio
        if (Test-Path -LiteralPath $cachePyc) {
            Remove-Item -LiteralPath $cachePyc -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    if ($pys.Count -lt 7) {
        Add-Aviso "Solo $($pys.Count) hooks en el paquete. El kit define 7."
    }
}

# 3f. Aviso de tamano: un salto grande suele ser algo que se colo
$mb = [math]::Round((($archivos | Measure-Object -Property Length -Sum).Sum / 1MB), 2)
Write-Host "  Tamano del contenido: $mb MB"
if ($mb -gt 5) { Add-Aviso "El paquete pesa $mb MB. Revisa que no se haya colado algo que no es del kit." }

# ---------------------------------------------------------------------------
# 4. Veredicto
# ---------------------------------------------------------------------------
Write-Paso 'Resultado'

foreach ($aviso in $avisos) { Write-Host "AVISO  $aviso" -ForegroundColor Yellow }

if ($errores.Count -gt 0) {
    Write-Host ''
    foreach ($e in $errores) { Write-Host "ERROR  $e" -ForegroundColor Red }
    Write-Host ''
    Write-Host "$($errores.Count) error(es). No se genero el ZIP." -ForegroundColor Red
    Write-Host "Staging para inspeccionar: $kitDir"
    exit 1
}

Write-Host 'Todas las verificaciones pasaron.' -ForegroundColor Green

if ($SoloVerificar) {
    Write-Host ''
    Write-Host 'Modo -SoloVerificar: no se genero el ZIP.'
    Remove-Item -LiteralPath $staging -Recurse -Force
    exit 0
}

# ---------------------------------------------------------------------------
# 5. Manifiesto y ZIP
# ---------------------------------------------------------------------------
Write-Paso 'Generando el ZIP'

$manifiesto = @(
    'TSOFT AI Dev Kit',
    "Version : $Version",
    "Commit  : $commit",
    "Armado  : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
    '',
    'Este paquete se genero con empaquetar.ps1 desde git archive, no copiando',
    'carpetas. Su contenido es identico al commit indicado arriba.',
    '',
    'Verificado: sin CRLF en archivos que lee Python, sin BOM, sin mojibake,',
    'frontmatter de skills valido, hooks compilan, tests en verde.',
    '',
    'Instalacion:  ver MANUAL-DEV.md'
) -join "`n"

[System.IO.File]::WriteAllText(
    (Join-Path $kitDir 'VERSION.txt'),
    $manifiesto,
    (New-Object System.Text.UTF8Encoding($false))
)

$nombreZip = "$nombreKit.zip"
$rutaZip = Join-Path $Salida $nombreZip
if (Test-Path -LiteralPath $rutaZip) { Remove-Item -LiteralPath $rutaZip -Force }

[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $staging,
    $rutaZip,
    [System.IO.Compression.CompressionLevel]::Optimal,
    $false
)

Remove-Item -LiteralPath $staging -Recurse -Force

$tam = [math]::Round(((Get-Item -LiteralPath $rutaZip).Length / 1KB), 0)
Write-Host ''
Write-Host "Listo: $rutaZip  ($tam KB)" -ForegroundColor Green
exit 0
