"""
Reemplazo de tempfile.TemporaryDirectory() tolerante a un problema real
encontrado en una maquina Windows corporativa (migracion en Claro,
2026-08-28): la suite corto con PermissionError [WinError 5] y
FileNotFoundError [WinError 3] al crear o limpiar carpetas temporales,
incluso redirigiendo TEMP/TMP a una carpeta propia del workspace. De los
251 tests, 95 fallaron por esto -- no por logica rota, sino por el
filesystem temporal.

La causa mas probable no es un permiso denegado real sino un bloqueo
transitorio (antivirus/EDR escaneando archivos recien escritos, tipico en
entornos corporativos) que se resuelve solo si se reintenta un momento
despues. Reintentar creacion y limpieza con backoff corto cubre eso sin
inventar una excepcion nueva para el resto del codigo.

Uso: reemplaza "with tempfile.TemporaryDirectory() as tmp:" por
"with directorio_temporal() as tmp:" -- misma forma, mismo valor (un str
con la ruta), en todos los tests que lo necesiten.
"""

from __future__ import annotations

import contextlib
import shutil
import tempfile
import time

REINTENTOS = 5
ESPERA_BASE_SEG = 0.2

ERRORES_TOLERADOS = (PermissionError, FileNotFoundError)


@contextlib.contextmanager
def directorio_temporal():
    ruta = None
    ultimo_error = None

    for intento in range(REINTENTOS):
        try:
            ruta = tempfile.mkdtemp()
            break
        except ERRORES_TOLERADOS as exc:
            ultimo_error = exc
            time.sleep(ESPERA_BASE_SEG * (intento + 1))

    if ruta is None:
        raise ultimo_error

    try:
        yield ruta
    finally:
        _borrar_con_reintentos(ruta)


def _borrar_con_reintentos(ruta: str) -> None:
    for intento in range(REINTENTOS):
        try:
            shutil.rmtree(ruta)
            return
        except ERRORES_TOLERADOS:
            time.sleep(ESPERA_BASE_SEG * (intento + 1))

    # Un directorio huerfano en TEMP es un problema mucho menor que tirar
    # la suite entera: Windows lo limpia solo con el tiempo. ignore_errors
    # cubre el intento final por si el bloqueo nunca se libera.
    shutil.rmtree(ruta, ignore_errors=True)
