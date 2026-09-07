"""
validar_estado.py - Verifica que los artefactos de las etapas marcadas
completas en orquestador-estado.md existan de verdad en disco.

Convierte una regla declarativa (la tabla de Progreso dice ✅) en una
verificacion ejecutable. Pensado para correr en el cierre de una feature,
antes de darla por terminada.

Uso:
  py tsoft-dev/scripts/validar_estado.py <nombre-de-la-feature>
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics_lib as ml

# Cada fila de la tabla de Progreso: "| Subagente | Estado | ... | ... |"
RE_FILA_PROGRESO = re.compile(
    r"^\|\s*(Explorador|Planificador|Desarrollador|Documentador|QA)\s*\|\s*([^|]+?)\s*\|",
    re.MULTILINE,
)

# "Estado general: en curso" / "completado" / "pausado" (seccion Resumen).
RE_ESTADO_GENERAL = re.compile(r"Estado general:\s*(.+)")

# Un archivo propio por etapa. Desarrollador es distinto: no crea un
# archivo aparte, agrega una seccion a design.md (el mismo artefacto del
# Planificador) -- por eso no esta en este mapa, se valida aparte.
ARTEFACTO_POR_SUBAGENTE = {
    "Explorador": "explorador-output.md",
    "Planificador": "design.md",
    "Documentador": "feature-doc.md",
    "QA": "qa.md",
}


def leer_progreso(texto_estado: str) -> list[tuple[str, str]]:
    """Devuelve [(subagente, estado_texto), ...] de la tabla de Progreso."""
    return RE_FILA_PROGRESO.findall(texto_estado)


def leer_estado_general(texto_estado: str) -> str | None:
    """Devuelve el valor de 'Estado general: X', o None si no aparece."""
    match = RE_ESTADO_GENERAL.search(texto_estado)
    return match.group(1).strip() if match else None


def validar_estado(feature_dir: Path) -> list[str]:
    """
    Cruza la tabla de Progreso de orquestador-estado.md contra los
    artefactos reales en disco. Devuelve la lista de problemas -- vacia
    si todo lo marcado como completado tiene su artefacto.
    """
    estado_md = feature_dir / "orquestador-estado.md"
    if not estado_md.exists():
        return [f"No existe {estado_md}"]

    texto = estado_md.read_text(encoding="utf-8")
    progreso = leer_progreso(texto)

    if not progreso:
        return [
            f"{estado_md} existe pero no encontre la tabla de Progreso "
            "(formato inesperado)"
        ]

    problemas = []
    for subagente, estado in progreso:
        if "✅" not in estado:
            continue

        if subagente == "Desarrollador":
            design = feature_dir / "design.md"
            if not design.exists():
                problemas.append(
                    f"Desarrollador marcado completado pero no existe {design}"
                )
            elif "## Ejecución" not in design.read_text(encoding="utf-8"):
                problemas.append(
                    f"Desarrollador marcado completado pero {design} no tiene "
                    "la seccion '## Ejecución'"
                )
            continue

        archivo = ARTEFACTO_POR_SUBAGENTE.get(subagente)
        if archivo and not (feature_dir / archivo).exists():
            problemas.append(
                f"{subagente} marcado completado pero no existe "
                f"{feature_dir / archivo}"
            )

    # Regla obligatoria de orquestador/SKILL.md: si ninguna etapa quedo en
    # pendiente (ni una sola ⏸), el flujo ya corrio completo y "Estado
    # general" tiene que reflejarlo con "completado" o "pausado" -- los dos
    # son cierres legitimos (SKILL.md los define como los tres valores
    # validos, junto con "en curso"). "pausado" es el que elige el IA Maker
    # cuando un subagente (tipicamente QA) SI corrio y completo, pero dejo
    # un hallazgo real que bloquea cerrar la feature todavia -- confirmado
    # con un caso real (migracion en Claro, 2026-08-30): QA completo,
    # encontro un bug de severidad Alta, y el IA Maker pauso a proposito en
    # vez de cerrar sucio. Dejarlo en "en curso" (o cualquier otro valor)
    # es el bug real que esta regla tiene que seguir agarrando: hace que
    # una feature terminada sea indistinguible de una abandonada.
    sin_pendientes = bool(progreso) and all("⏸" not in estado for _, estado in progreso)
    estado_general = leer_estado_general(texto)
    if sin_pendientes and estado_general and estado_general.lower() not in ("completado", "pausado"):
        problemas.append(
            "Ninguna etapa quedo pendiente (⏸) pero 'Estado general' dice "
            f"'{estado_general}', ni 'completado' ni 'pausado' (regla "
            "obligatoria de orquestador/SKILL.md)"
        )

    return problemas


def _imprimir_seguro(texto: str) -> None:
    """
    Como print(), pero no revienta en consolas Windows con codepage legacy
    (cp1252 y similares) si el texto trae un caracter que ese codepage no
    sabe representar -- reproducido en un cliente real (Claro, 2026-08-30):
    validar_estado.py funciona perfecto cuando no encuentra nada y crashea
    justo al reportar un problema real, porque el mensaje trae el simbolo
    ⏸. El riesgo no es solo ese simbolo: cualquier ruta con acentos (rutas
    de este mismo equipo las tienen) puede disparar el mismo crash.

    Si la escritura directa falla, se reintenta escribiendo bytes crudos
    contra el stream subyacente con errores tolerados -- se pierde el
    caracter exacto (queda como \\uXXXX), pero el mensaje llega completo en
    vez de perderse entero.
    """
    try:
        print(texto)
        return
    except UnicodeEncodeError:
        pass

    buffer = getattr(sys.stdout, "buffer", None)
    codificacion = getattr(sys.stdout, "encoding", None) or "ascii"
    datos = texto.encode(codificacion, errors="backslashreplace") + b"\n"
    if buffer is not None:
        buffer.write(datos)
    else:
        sys.stdout.write(datos.decode(codificacion, errors="replace"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Valida que los artefactos de las etapas marcadas completas existan en disco."
    )
    parser.add_argument("feature", help="Nombre de la carpeta en tsoft-dev/[feature]/")
    args = parser.parse_args()

    raiz = ml.raiz_kit()
    feature_dir = raiz / "tsoft-dev" / args.feature
    problemas = validar_estado(feature_dir)

    if not problemas:
        _imprimir_seguro(f"OK: los artefactos de {args.feature} coinciden con el estado declarado.")
        return 0

    _imprimir_seguro(f"ERROR: {len(problemas)} inconsistencia(s) en {args.feature}:")
    for problema in problemas:
        _imprimir_seguro(f"  - {problema}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
