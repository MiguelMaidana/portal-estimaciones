"""Tests de validar_estado.py. Corren con: py -3 tsoft-dev/scripts/tests/test_validar_estado.py"""

import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers_temporal import directorio_temporal
import validar_estado as ve


ESTADO_CON_PLANIFICADOR_COMPLETADO = """# Estado del flujo - una-feature
Ultima actualizacion: 2026-08-27

## Progreso

| Subagente | Estado | Aprobado por IA Maker | Fecha |
|-----------|--------|----------------------|-------|
| Explorador | ⏭ salteado | - | 2026-08-27 |
| Planificador | ✅ completado | Si | 2026-08-27 |
| Desarrollador | ⏸ pendiente | - | - |
| Documentador | ⏸ pendiente | - | - |
| QA | ⏸ pendiente | - | - |
"""

ESTADO_CON_DESARROLLADOR_COMPLETADO = """# Estado del flujo - una-feature
Ultima actualizacion: 2026-08-27

## Progreso

| Subagente | Estado | Aprobado por IA Maker | Fecha |
|-----------|--------|----------------------|-------|
| Explorador | ✅ completado | - | 2026-08-27 |
| Planificador | ✅ completado | Si | 2026-08-27 |
| Desarrollador | ✅ completado | - | 2026-08-27 |
| Documentador | ⏸ pendiente | - | - |
| QA | ⏸ pendiente | - | - |
"""

ESTADO_SIN_PENDIENTES_PERO_EN_CURSO = """# Estado del flujo - una-feature
Ultima actualizacion: 2026-08-27

## Resumen
Feature: una-feature
Estado general: en curso

## Progreso

| Subagente | Estado | Aprobado por IA Maker | Fecha |
|-----------|--------|----------------------|-------|
| Explorador | ✅ completado | Si | 2026-08-27 |
| Planificador | ✅ completado | Si | 2026-08-27 |
| Desarrollador | ✅ completado | Si | 2026-08-27 |
| Documentador | ✅ completado | Si | 2026-08-27 |
| QA | ✅ completado | Si | 2026-08-27 |
"""

ESTADO_SIN_PENDIENTES_Y_COMPLETADO = ESTADO_SIN_PENDIENTES_PERO_EN_CURSO.replace(
    "Estado general: en curso", "Estado general: completado"
)

ESTADO_SIN_PENDIENTES_Y_PAUSADO = ESTADO_SIN_PENDIENTES_PERO_EN_CURSO.replace(
    "Estado general: en curso", "Estado general: pausado"
)

ESTADO_CON_SALTEADOS_Y_COMPLETADO = """# Estado del flujo - una-feature
Ultima actualizacion: 2026-08-27

## Resumen
Feature: una-feature
Estado general: completado

## Progreso

| Subagente | Estado | Aprobado por IA Maker | Fecha |
|-----------|--------|----------------------|-------|
| Explorador | ⏭ salteado | - | 2026-08-27 |
| Planificador | ✅ completado | Si | 2026-08-27 |
| Desarrollador | ✅ completado | Si | 2026-08-27 |
| Documentador | ⏭ salteado | - | 2026-08-27 |
| QA | ✅ completado | Si | 2026-08-27 |
"""


class TestValidarEstado(unittest.TestCase):
    def test_detecta_artefacto_faltante_de_etapa_completada(self):
        with directorio_temporal() as tmp:
            feature_dir = Path(tmp)
            (feature_dir / "orquestador-estado.md").write_text(
                ESTADO_CON_PLANIFICADOR_COMPLETADO, encoding="utf-8"
            )
            # No se crea design.md a proposito.
            problemas = ve.validar_estado(feature_dir)

        self.assertEqual(len(problemas), 1)
        self.assertIn("Planificador", problemas[0])
        self.assertIn("design.md", problemas[0])

    def test_no_marca_problema_si_el_artefacto_existe(self):
        with directorio_temporal() as tmp:
            feature_dir = Path(tmp)
            (feature_dir / "orquestador-estado.md").write_text(
                ESTADO_CON_PLANIFICADOR_COMPLETADO, encoding="utf-8"
            )
            (feature_dir / "design.md").write_text("# Plan\n", encoding="utf-8")
            problemas = ve.validar_estado(feature_dir)

        self.assertEqual(problemas, [])

    def test_ignora_etapas_no_completadas(self):
        with directorio_temporal() as tmp:
            feature_dir = Path(tmp)
            (feature_dir / "orquestador-estado.md").write_text(
                ESTADO_CON_PLANIFICADOR_COMPLETADO, encoding="utf-8"
            )
            (feature_dir / "design.md").write_text("# Plan\n", encoding="utf-8")
            # Documentador esta "pendiente": no se crea feature-doc.md.
            problemas = ve.validar_estado(feature_dir)

        self.assertEqual(problemas, [])

    def test_desarrollador_exige_seccion_de_ejecucion_no_archivo_aparte(self):
        with directorio_temporal() as tmp:
            feature_dir = Path(tmp)
            (feature_dir / "orquestador-estado.md").write_text(
                ESTADO_CON_DESARROLLADOR_COMPLETADO, encoding="utf-8"
            )
            (feature_dir / "explorador-output.md").write_text("# Scope\n", encoding="utf-8")
            # design.md existe pero SIN la seccion "## Ejecución" que el
            # desarrollador tiene que agregar al terminar.
            (feature_dir / "design.md").write_text("# Plan\n", encoding="utf-8")
            problemas = ve.validar_estado(feature_dir)

        self.assertEqual(len(problemas), 1)
        self.assertIn("Desarrollador", problemas[0])

    def test_reporta_estado_md_ausente(self):
        with directorio_temporal() as tmp:
            feature_dir = Path(tmp)
            problemas = ve.validar_estado(feature_dir)

        self.assertEqual(len(problemas), 1)
        self.assertIn("orquestador-estado.md", problemas[0])

    def test_detecta_en_curso_sin_ninguna_etapa_pendiente(self):
        with directorio_temporal() as tmp:
            feature_dir = Path(tmp)
            (feature_dir / "orquestador-estado.md").write_text(
                ESTADO_SIN_PENDIENTES_PERO_EN_CURSO, encoding="utf-8"
            )
            (feature_dir / "explorador-output.md").write_text("# Scope\n", encoding="utf-8")
            (feature_dir / "design.md").write_text("# Plan\n\n## Ejecución\n", encoding="utf-8")
            (feature_dir / "feature-doc.md").write_text("# Doc\n", encoding="utf-8")
            (feature_dir / "qa.md").write_text("# QA\n", encoding="utf-8")
            problemas = ve.validar_estado(feature_dir)

        self.assertEqual(len(problemas), 1)
        self.assertIn("Estado general", problemas[0])
        self.assertIn("en curso", problemas[0])

    def test_no_marca_problema_si_completado_coincide_con_la_tabla(self):
        with directorio_temporal() as tmp:
            feature_dir = Path(tmp)
            (feature_dir / "orquestador-estado.md").write_text(
                ESTADO_SIN_PENDIENTES_Y_COMPLETADO, encoding="utf-8"
            )
            (feature_dir / "explorador-output.md").write_text("# Scope\n", encoding="utf-8")
            (feature_dir / "design.md").write_text("# Plan\n\n## Ejecución\n", encoding="utf-8")
            (feature_dir / "feature-doc.md").write_text("# Doc\n", encoding="utf-8")
            (feature_dir / "qa.md").write_text("# QA\n", encoding="utf-8")
            problemas = ve.validar_estado(feature_dir)

        self.assertEqual(problemas, [])

    def test_pausado_es_un_cierre_legitimo_sin_ninguna_etapa_pendiente(self):
        # Caso real (migracion en Claro, 2026-08-30): QA corrio y completo,
        # encontro un hallazgo de severidad Alta, y el IA Maker pauso a
        # proposito en vez de cerrar sucio. No es un bug de gobernanza.
        with directorio_temporal() as tmp:
            feature_dir = Path(tmp)
            (feature_dir / "orquestador-estado.md").write_text(
                ESTADO_SIN_PENDIENTES_Y_PAUSADO, encoding="utf-8"
            )
            (feature_dir / "explorador-output.md").write_text("# Scope\n", encoding="utf-8")
            (feature_dir / "design.md").write_text("# Plan\n\n## Ejecución\n", encoding="utf-8")
            (feature_dir / "feature-doc.md").write_text("# Doc\n", encoding="utf-8")
            (feature_dir / "qa.md").write_text("# QA\n", encoding="utf-8")
            problemas = ve.validar_estado(feature_dir)

        self.assertEqual(problemas, [])

    def test_etapas_salteadas_cuentan_como_cerradas_no_pendientes(self):
        with directorio_temporal() as tmp:
            feature_dir = Path(tmp)
            (feature_dir / "orquestador-estado.md").write_text(
                ESTADO_CON_SALTEADOS_Y_COMPLETADO, encoding="utf-8"
            )
            (feature_dir / "design.md").write_text("# Plan\n\n## Ejecución\n", encoding="utf-8")
            (feature_dir / "qa.md").write_text("# QA\n", encoding="utf-8")
            problemas = ve.validar_estado(feature_dir)

        self.assertEqual(problemas, [])

    def test_reporta_formato_inesperado_si_no_hay_tabla(self):
        with directorio_temporal() as tmp:
            feature_dir = Path(tmp)
            (feature_dir / "orquestador-estado.md").write_text(
                "# Estado del flujo - una-feature\n\nSin tabla de progreso.\n",
                encoding="utf-8",
            )
            problemas = ve.validar_estado(feature_dir)

        self.assertEqual(len(problemas), 1)
        self.assertIn("formato inesperado", problemas[0])


class _StdoutCodepageRestringido:
    """
    Simula una consola Windows con codepage legacy (cp1252): escribir un
    caracter fuera de ese codepage revienta con UnicodeEncodeError, igual
    que el crash real reproducido en un cliente (Claro, 2026-08-30) al
    imprimir el simbolo ⏸. `.buffer.write()` en cambio acepta bytes crudos
    sin chequeo, igual que el `sys.stdout.buffer` real.
    """

    def __init__(self):
        self.buffer = io.BytesIO()
        self.encoding = "cp1252"

    def write(self, texto):
        datos = texto.encode(self.encoding)  # revienta con UnicodeEncodeError si no entra en cp1252
        self.buffer.write(datos)
        return len(texto)

    def flush(self):
        pass


class TestImprimirSeguro(unittest.TestCase):
    def test_no_revienta_con_un_simbolo_fuera_de_cp1252(self):
        falso_stdout = _StdoutCodepageRestringido()
        original = sys.stdout
        sys.stdout = falso_stdout
        try:
            ve._imprimir_seguro("Ninguna etapa quedo pendiente (⏸) pero...")
        finally:
            sys.stdout = original

        salida = falso_stdout.buffer.getvalue().decode("cp1252", errors="replace")
        self.assertIn("Ninguna etapa quedo pendiente", salida)

    def test_texto_normal_se_imprime_igual_que_siempre(self):
        falso_stdout = _StdoutCodepageRestringido()
        original = sys.stdout
        sys.stdout = falso_stdout
        try:
            ve._imprimir_seguro("OK: todo coincide.")
        finally:
            sys.stdout = original

        salida = falso_stdout.buffer.getvalue().decode("cp1252")
        self.assertEqual(salida, "OK: todo coincide.\n")


if __name__ == "__main__":
    unittest.main()
