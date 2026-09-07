"""Tests del reporte del camino de hooks. Correr con: py tsoft-dev/scripts/tests/test_reporte.py"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers_temporal import directorio_temporal
import metrics_lib as ml
import reporte as rep


def linea(session_id, total, usd=1.0, inicio="2026-08-01T10:00:00Z",
          fin=None, feature="una-feature", duracion_h=1.0,
          duracion_confiable=True):
    """Una linea de ledger. El total es ACUMULADO de la sesion hasta ese Stop."""
    return {
        "evento": "ejecucion",
        "session_id": session_id,
        "feature": feature,
        "inicio": inicio,
        "fin": fin or inicio,
        "modelo": "gpt-5.4",
        "tokens": {"input": total, "cache": 0, "output": 0, "total": total},
        "costo": {"usd": usd, "local": 0, "moneda": "ARS"},
        "duracion_h": duracion_h,
        "duracion_confiable": duracion_confiable,
        "clasificacion": {
            "tipo_tarea": "evolutivo-frontend",
            "complejidad": "media",
            "origen": "declarado",
            "origen_tipo": "declarado",
            "origen_complejidad": "declarado",
            "tipo_reconocido": True,
        },
        "evidencia": {"archivos_tocados": [], "comandos": [], "subagentes": [], "ediciones": 0},
    }


PRECIOS = {
    "precios_usd_por_millon": {
        "gpt-5.4": {"input": 2.50, "cache": 0.25, "output": 15.00},
        "_default": {"input": 0, "cache": 0, "output": 0},
    },
    "moneda_local": "ARS",
    "usd_a_moneda_local": 1550,
}


def kit_temporal(tmp, lineas):
    """Arma una raiz de kit con un ledger y devuelve la ruta."""
    raiz = Path(tmp)
    (raiz / "tsoft-dev" / "config").mkdir(parents=True)
    (raiz / "tsoft-dev" / "metrics").mkdir(parents=True)
    (raiz / "tsoft-dev" / "config" / "celula.json").write_text(
        json.dumps(PRECIOS), encoding="utf-8"
    )
    (raiz / "tsoft-dev" / "metrics" / "ledger.jsonl").write_text(
        "\n".join(json.dumps(x) for x in lineas), encoding="utf-8"
    )
    return raiz


class TestUltimasEjecuciones(unittest.TestCase):
    """
    El ledger guarda una foto ACUMULADA por cada Stop, no un delta. Una sesion
    con 3 cierres tiene 3 lineas y la ultima ya contiene todo lo anterior.
    """

    def test_se_queda_con_la_ultima_linea_de_cada_sesion(self):
        ledger = [
            linea("sesion-A", 100),
            linea("sesion-A", 300),
            linea("sesion-A", 500),
            linea("sesion-B", 200),
        ]
        ultimas = ml.ultimas_ejecuciones(ledger)
        totales = sorted(r["tokens"]["total"] for r in ultimas)
        self.assertEqual(totales, [200, 500])

    def test_ignora_los_eventos_que_no_son_ejecucion(self):
        ledger = [linea("sesion-A", 100), {"evento": "otra-cosa", "session_id": "x"}]
        self.assertEqual(len(ml.ultimas_ejecuciones(ledger)), 1)

    def test_ledger_vacio_no_rompe(self):
        self.assertEqual(ml.ultimas_ejecuciones([]), [])


class TestConsolidado(unittest.TestCase):
    def test_no_suma_las_fotos_acumuladas_de_una_misma_sesion(self):
        # Sumar las 4 lineas daria 1100 tokens; lo correcto es 500 + 200 = 700.
        ledger = [
            linea("sesion-A", 100, usd=1.0),
            linea("sesion-A", 300, usd=3.0),
            linea("sesion-A", 500, usd=5.0),
            linea("sesion-B", 200, usd=2.0),
        ]
        with directorio_temporal() as tmp:
            raiz = kit_temporal(tmp, ledger)
            destino = rep.generar_consolidado(raiz=raiz)
            texto = destino.read_text(encoding="utf-8")

        self.assertIn("700", texto)          # 500 + 200
        self.assertNotIn("1,100", texto)     # la suma ingenua
        self.assertIn("| Ejecuciones | 2 |", texto)   # 2 sesiones, no 4 lineas

    def test_avisa_cuando_una_sesion_no_tiene_duracion_confiable(self):
        ledger = [linea("sesion-1", 100, duracion_confiable=False)]
        with directorio_temporal() as tmp:
            raiz = kit_temporal(tmp, ledger)
            texto = rep.generar_consolidado(raiz=raiz).read_text(encoding="utf-8")

        self.assertIn("ATENCION", texto)

    def test_recalcula_el_costo_en_vez_de_confiar_en_el_guardado(self):
        # Las lineas viejas del ledger se escribieron con la formula rota, que
        # cobraba el cache dos veces. Reusar ese numero arrastra el error.
        ledger = [linea("sesion-A", 1_000_000, usd=99.99)]
        ledger[0]["tokens"] = {
            "input": 1_000_000, "cache": 0, "output": 0, "total": 1_000_000,
        }
        with directorio_temporal() as tmp:
            raiz = kit_temporal(tmp, ledger)
            texto = rep.generar_consolidado(raiz=raiz).read_text(encoding="utf-8")

        self.assertIn("$2.5000", texto)      # 1M de input a 2.50 por millon
        self.assertNotIn("99.99", texto)     # el valor viejo guardado

    def test_el_filtro_desde_sigue_funcionando(self):
        ledger = [
            linea("vieja", 100, inicio="2026-07-01T10:00:00Z"),
            linea("nueva", 300, inicio="2026-08-10T10:00:00Z"),
        ]
        with directorio_temporal() as tmp:
            raiz = kit_temporal(tmp, ledger)
            texto = rep.generar_consolidado(desde="2026-08-01", raiz=raiz).read_text(encoding="utf-8")

        self.assertIn("| Ejecuciones | 1 |", texto)
        self.assertIn("300", texto)


if __name__ == "__main__":
    unittest.main()
