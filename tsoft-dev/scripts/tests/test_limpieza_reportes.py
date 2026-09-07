"""Tests de limpieza: codigo huerfano que no deberia existir ni estar
documentado. Corren con: py -3 tsoft-dev/scripts/tests/test_limpieza_reportes.py
"""

import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]


class TestReporteHtmlEliminado(unittest.TestCase):
    def test_el_script_huerfano_ya_no_existe(self):
        # Nada lo invocaba: generar-reportes.ps1 solo llama reconciliador.py
        # y reporte_features.py --html. 812 lineas sin un solo caller ni test.
        self.assertFalse(
            (RAIZ / "tsoft-dev" / "scripts" / "reporte_html.py").exists()
        )

    def test_el_skill_ya_no_promete_reporte_html_py(self):
        texto = (RAIZ / ".codex" / "skills" / "reporte-ejecucion" / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("reporte_html.py", texto)


if __name__ == "__main__":
    unittest.main()
