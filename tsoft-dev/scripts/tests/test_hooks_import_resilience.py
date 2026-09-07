"""Tests de resiliencia de los hooks ante metrics_lib ausente.

Corren con: py -3 tsoft-dev/scripts/tests/test_hooks_import_resilience.py
"""

import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers_temporal import directorio_temporal

RAIZ_KIT = Path(__file__).resolve().parents[3]
DIR_HOOKS = RAIZ_KIT / ".codex" / "hooks"

NOMBRES_HOOKS = [
    "session_start.py",
    "post_tool_use.py",
    "user_prompt_submit.py",
    "subagent_start.py",
    "subagent_stop.py",
    "turn_stop.py",
    "session_end.py",
]


class TestHooksToleranImportRoto(unittest.TestCase):
    """Simula un kit incompleto: el hook existe pero tsoft-dev/scripts no."""

    def _correr_hook_aislado(self, nombre_hook, tmp_path):
        # Copia SOLO .codex/hooks/<hook>.py a un arbol vacio. parents[2] del
        # hook copiado resuelve a tmp_path, y tmp_path/tsoft-dev/scripts no
        # existe: "import metrics_lib" falla con ModuleNotFoundError, el
        # mismo sintoma que un kit mal desempaquetado o movido de lugar.
        destino_dir = tmp_path / ".codex" / "hooks"
        destino_dir.mkdir(parents=True, exist_ok=True)
        destino = destino_dir / nombre_hook
        shutil.copy(DIR_HOOKS / nombre_hook, destino)
        return subprocess.run(
            [sys.executable, str(destino)],
            input=b"{}",
            capture_output=True,
            timeout=15,
        )

    def test_los_7_hooks_no_mueren_con_metrics_lib_ausente(self):
        for nombre_hook in NOMBRES_HOOKS:
            with self.subTest(hook=nombre_hook):
                with directorio_temporal() as tmp:
                    resultado = self._correr_hook_aislado(nombre_hook, Path(tmp))
                    self.assertEqual(
                        resultado.returncode, 0,
                        f"{nombre_hook} deberia salir con 0 aunque metrics_lib "
                        f"no este disponible. stderr: "
                        f"{resultado.stderr.decode('utf-8', 'replace')}",
                    )
                    salida = resultado.stdout.decode("utf-8", "replace").strip()
                    self.assertTrue(salida, f"{nombre_hook} no imprimio nada en stdout")
                    cuerpo = json.loads(salida)
                    self.assertIn("systemMessage", cuerpo)
                    self.assertIn("metrics_lib", cuerpo["systemMessage"])


if __name__ == "__main__":
    unittest.main()
