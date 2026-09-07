#!/usr/bin/env bash
# TSOFT AI Dev Kit - Instalador Linux/macOS
#
# Verifica requisitos, comprueba la integridad del paquete y prepara las
# carpetas de trabajo. NO modifica hooks.json: sus rutas son relativas al
# proyecto y no hay nada que resolver por maquina.
#
# Este archivo TIENE que estar en LF. Con CRLF, el shebang queda como
# '/usr/bin/env bash\r' y bash falla con "bad interpreter". El .gitattributes
# del repo lo garantiza con '*.sh text eol=lf'.

set -euo pipefail

KIT_HOME="$(cd "$(dirname "$0")" && pwd)"
ERRORES=0

fallo() { printf 'ERROR: %s\n' "$1" >&2; ERRORES=$((ERRORES + 1)); }
ok()    { printf 'OK  %s\n' "$1"; }
aviso() { printf 'AVISO: %s\n' "$1"; }

printf 'TSOFT AI Dev Kit - Instalacion\n'
printf 'KIT_HOME: %s\n\n' "$KIT_HOME"

# ---------------------------------------------------------------------------
# 1. Python. Va PRIMERO.
#
#    Antes este chequeo estaba tercero, despues de dos pasos que ya necesitaban
#    python3. Sin python3 instalado, el 2>/dev/null de la validacion del JSON
#    se tragaba el error real y el usuario recibia "hooks.json quedo invalido",
#    que es falso y manda a revisar el archivo equivocado.
# ---------------------------------------------------------------------------
printf '1. Requisitos\n'

if ! command -v python3 >/dev/null 2>&1; then
    printf 'ERROR: no encontre python3.\n' >&2
    printf '       Debian/Ubuntu : sudo apt install python3\n' >&2
    printf '       macOS (brew)  : brew install python3\n' >&2
    exit 1
fi

# El kit necesita 3.9 como minimo: metrics_lib importa zoneinfo, que no existe
# en 3.8. Ahi degrada a la zona del sistema y los cortes semanales del reporte
# pueden caer en otro dia segun la maquina.
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'; then
    VERSION="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
    printf 'ERROR: Python %s es muy viejo. El kit necesita 3.9 o superior.\n' "$VERSION" >&2
    exit 1
fi
ok "$(python3 --version 2>&1)"

# ---------------------------------------------------------------------------
# 2. Integridad del paquete
#
#    Antes este paso reescribia hooks.json con sed para resolver __KIT_HOME__.
#    Ese placeholder ya no existe: hooks.json usa rutas relativas al proyecto,
#    asi que el sed era un no-op que igual reescribia el archivo. Lo unico util
#    que queda es comprobar que llego entero.
# ---------------------------------------------------------------------------
printf '\n2. Integridad del kit\n'

HOOKS="$KIT_HOME/.codex/hooks.json"

if [ ! -f "$HOOKS" ]; then
    printf 'ERROR: falta .codex/hooks.json. El paquete llego incompleto.\n' >&2
    printf '       Redescarga el kit; no intentes crearlo a mano.\n' >&2
    exit 1
fi

# Sin 2>/dev/null: si esto falla, el mensaje de Python es la informacion util.
if ! python3 -c 'import json,sys; json.load(open(sys.argv[1], encoding="utf-8"))' "$HOOKS"; then
    printf 'ERROR: hooks.json no es JSON valido. El paquete llego corrupto.\n' >&2
    printf '       Redescarga el kit.\n' >&2
    exit 1
fi
ok "hooks.json valido"

# BOM: si alguien lo edito en Windows con Set-Content -Encoding UTF8, el parser
# de Codex lo rechaza con "expected value at line 1 column 1".
if head -c 3 "$HOOKS" | od -An -tx1 | tr -d ' \n' | grep -qi '^efbbbf$'; then
    fallo "hooks.json tiene BOM. Codex lo va a rechazar al arrancar."
fi

if grep -q '__KIT_HOME__' "$HOOKS"; then
    fallo "hooks.json todavia tiene __KIT_HOME__. Ese paquete es de una version vieja."
fi

# Cada hook declarado tiene que existir. Si falta uno, Codex tira
# 'hook exited with code 1' en cada llamada a herramienta sin decir cual.
FALTANTES=""
CANTIDAD=0
for NOMBRE in $(grep -o '[a-z_]*\.py' "$HOOKS" | sort -u); do
    CANTIDAD=$((CANTIDAD + 1))
    if [ ! -f "$KIT_HOME/.codex/hooks/$NOMBRE" ]; then
        FALTANTES="$FALTANTES $NOMBRE"
    fi
done
if [ -n "$FALTANTES" ]; then
    fallo "hooks.json declara hooks que no estan en el paquete:$FALTANTES"
else
    ok "$CANTIDAD hooks presentes"
fi

# ---------------------------------------------------------------------------
# 3. Carpetas de trabajo
# ---------------------------------------------------------------------------
printf '\n3. Carpetas\n'

for CARPETA in "tsoft-dev/metrics/sesiones" "tsoft-dev/reportes/ejecuciones" "docs"; do
    if [ ! -d "$KIT_HOME/$CARPETA" ]; then
        mkdir -p "$KIT_HOME/$CARPETA"
        ok "creada: $CARPETA"
    fi
done

# ---------------------------------------------------------------------------
# 4. AGENTS.md
#
#    El kit trae una plantilla en plantillas/AGENTS.md, con la seccion
#    "Convencion de features" ya completa (de ella depende que la medicion
#    funcione). Si el proyecto ya tiene un AGENTS.md propio, no se pisa: son
#    las reglas del proyecto, no algo que el kit deba reemplazar.
# ---------------------------------------------------------------------------
printf '\n4. AGENTS.md\n'

AGENTS_DESTINO="$KIT_HOME/AGENTS.md"
AGENTS_PLANTILLA="$KIT_HOME/plantillas/AGENTS.md"

if [ -f "$AGENTS_DESTINO" ]; then
    ok "ya existe un AGENTS.md en la raiz, no se toca"
elif [ -f "$AGENTS_PLANTILLA" ]; then
    cp "$AGENTS_PLANTILLA" "$AGENTS_DESTINO"
    ok "AGENTS.md creado desde la plantilla del kit -- falta completarlo (paso 2 de los pasos manuales)"
else
    aviso "no encontre plantillas/AGENTS.md en el paquete. Crealo a mano."
fi

# ---------------------------------------------------------------------------
# 5. Proteccion de los datos de medicion
#
#    El kit se instala dentro del repo del cliente. metrics/ guarda los prompts
#    y comandos reales de cada sesion. Se avisa, no se escribe: el .gitignore
#    del repo es del cliente, no del kit.
# ---------------------------------------------------------------------------
printf '\n5. Datos de medicion\n'

if git -C "$KIT_HOME" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    # Caso mas grave, chequeado primero: si el archivo YA esta trackeado,
    # agregarlo a .gitignore o .git/info/exclude no hace nada -- Git lo sigue
    # versionando igual. Hace falta sacarlo del indice con "git rm --cached".
    # check-ignore --no-index (mas abajo) no detecta esto: solo evalua el
    # patron, no si el archivo ya esta en el indice.
    YA_TRACKEADAS=""
    for RUTA in "tsoft-dev/metrics" "tsoft-dev/reportes"; do
        if [ -n "$(git -C "$KIT_HOME" ls-files -- "$RUTA")" ]; then
            YA_TRACKEADAS="$YA_TRACKEADAS $RUTA"
        fi
    done
    if [ -n "$YA_TRACKEADAS" ]; then
        printf 'AVISO CRITICO: estas carpetas YA ESTAN TRACKEADAS en git:%s\n' "$YA_TRACKEADAS" >&2
        printf '       Agregarlas a .gitignore o .git/info/exclude NO alcanza: Git ya\n' >&2
        printf '       las viene versionando. Sacalas del indice (esto NO borra los\n' >&2
        printf '       archivos locales, solo deja de trackearlos):\n\n' >&2
        printf '         git rm -r --cached tsoft-dev/metrics tsoft-dev/reportes\n\n' >&2
    fi

    DESPROTEGIDAS=""
    for RUTA in "tsoft-dev/metrics/" "tsoft-dev/reportes/"; do
        # --no-index para que un archivo ya trackeado no enmascare la regla.
        if ! git -C "$KIT_HOME" check-ignore -q --no-index "$RUTA" 2>/dev/null; then
            DESPROTEGIDAS="$DESPROTEGIDAS $RUTA"
        fi
    done
    if [ -n "$DESPROTEGIDAS" ]; then
        aviso "estas carpetas NO estan en el .gitignore del repo:$DESPROTEGIDAS"
        printf '       Guardan los prompts y comandos reales de cada sesion.\n'
        printf '       Agregalas al .gitignore, o al .git/info/exclude si no\n'
        printf '       queres tocar el .gitignore del proyecto:\n\n'
        printf '         printf "tsoft-dev/metrics/\\ntsoft-dev/reportes/\\n" >> .git/info/exclude\n\n'
    elif [ -z "$YA_TRACKEADAS" ]; then
        ok "metrics/ y reportes/ estan fuera del control de versiones"
    fi
else
    aviso "esto no parece un repo git. Si lo vas a versionar, acordate de"
    printf '       excluir tsoft-dev/metrics/ y tsoft-dev/reportes/.\n'
fi

# ---------------------------------------------------------------------------
# Resultado
# ---------------------------------------------------------------------------
printf '\n'
if [ "$ERRORES" -gt 0 ]; then
    printf 'Instalacion incompleta: %s problema(s). Resolvelos antes de usar el kit.\n' "$ERRORES" >&2
    exit 1
fi

CONFIG_GLOBAL="$HOME/.codex/config.toml"

printf 'PASOS MANUALES REQUERIDOS:\n\n'
printf '1. CONFIAR EL PROYECTO (obligatorio)\n\n'
printf '   La forma facil, recomendada:\n'
printf '   Abri Codex en esta carpeta. Va a preguntar:\n'
printf '     "Do you trust the contents of this directory?"\n'
printf '   Responde "1. Yes, continue" y Codex lo registra solo.\n\n'
printf '   Si preferis hacerlo a mano, va en el config GLOBAL del usuario:\n'
printf '     %s\n\n' "$CONFIG_GLOBAL"
printf '   OJO: ese archivo NO es el mismo que\n'
printf '   %s/.codex/config.toml\n' "$KIT_HOME"
printf '   Son dos archivos distintos con el mismo nombre. Si pones el\n'
printf '   trust_level en el del proyecto, Codex falla al arrancar con\n'
printf '   "invalid type: string, expected a boolean".\n\n'
printf '   Va al final del archivo global, con la ruta entre comillas:\n'
printf "     [projects.'%s']\n" "$KIT_HOME"
printf '     trust_level = "trusted"\n\n'
printf '2. COMPLETAR EL AGENTS.md (obligatorio)\n'
printf '   Los agentes lo leen antes de trabajar. Sin eso trabajan a ciegas.\n'
printf '   Podes pedirle a Codex que lo genere:\n'
printf '     "Analiza la estructura de este repositorio y completa el AGENTS.md"\n\n'
printf '3. VERIFICAR QUE LA MEDICION ANDA\n'
printf '   python3 -m unittest discover -s tsoft-dev/scripts/tests\n'
printf '   Tiene que decir OK.\n\n'
printf '4. (Opcional, solo si trabajas por terminal) Confiar los hooks:\n'
printf '   Abri Codex y ejecuta /hooks\n'
printf '   En la extension de VS Code no hace falta: el reconciliador cubre\n'
printf '   las dos vias y es la fuente del reporte del equipo.\n\n'
printf 'Instalacion completa. Detalle en MANUAL-DEV.md\n'
exit 0
