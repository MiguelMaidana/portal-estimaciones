"""Tests del reporte por feature. Correr con: py tsoft-dev/scripts/tests/test_reporte_features.py"""

import json
import sys
import unittest
from argparse import Namespace
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers_temporal import directorio_temporal
import reporte_features as rf


def registro(
    feature,
    total,
    activo,
    turnos=1,
    usd=1.0,
    tarifado=True,
    estado="en curso",
    modelos_multiples=False,
    etapa="orquestador",
    tipo_tarea="evolutivo-frontend",
    complejidad="baja",
    origen_tipo="inferido",
    origen_complejidad="inferido",
    inicio=None,
    fin=None,
):
    return {
        "feature": feature,
        "estado": estado,
        "developer": "dev@tsoft.com",
        "origen": "codex_vscode",
        "tiempo_activo_h": activo,
        "tiempo_pared_h": activo,
        "turnos": turnos,
        "tokens": {"total": total, "input": total, "cache": 0, "output": 0},
        "costo": {"usd": usd, "local": 0, "moneda": "ARS", "tarifado": tarifado},
        "modelos_multiples": modelos_multiples,
        "etapa": etapa,
        "tipo_tarea": tipo_tarea,
        "complejidad": complejidad,
        "origen_tipo": origen_tipo,
        "origen_complejidad": origen_complejidad,
        "inicio": inicio,
        "fin": fin,
    }


class TestAgregacion(unittest.TestCase):
    def test_suma_los_tramos_de_una_misma_feature(self):
        filas = rf.agregar_por_feature([
            registro("feature-a", 1000, 0.5, turnos=3),
            registro("feature-a", 500, 0.25, turnos=2),
        ])
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["tokens_total"], 1500)
        self.assertAlmostEqual(filas[0]["tiempo_activo_h"], 0.75, places=4)
        self.assertEqual(filas[0]["turnos"], 5)
        self.assertEqual(filas[0]["conversaciones"], 2)

    def test_ordena_por_tokens_descendente(self):
        filas = rf.agregar_por_feature([
            registro("chica", 100, 0.1),
            registro("grande", 9000, 0.1),
        ])
        self.assertEqual(filas[0]["feature"], "grande")

    def test_no_duplica_tiempo_cuando_el_tramo_del_orquestador_contiene_al_del_subagente(self):
        # Caso real: el Orquestador queda bloqueado en wait_agent mientras
        # corre el Explorador. Su propio tramo de reloj (10:00-10:50, 0.833h)
        # YA incluye el tramo del Explorador (10:05-10:10, 0.083h) -- sumarlos
        # tal cual daria 0.917h para una feature que en la practica tardo
        # 0.833h de punta a punta.
        filas = rf.agregar_por_feature([
            registro(
                "actualizar-ui", 1000, 0.833, etapa="orquestador",
                inicio="2026-08-30T13:00:00Z", fin="2026-08-30T13:50:00Z",
            ),
            registro(
                "actualizar-ui", 500, 0.083, etapa="explorador",
                inicio="2026-08-30T13:05:00Z", fin="2026-08-30T13:10:00Z",
            ),
        ])
        self.assertEqual(len(filas), 1)
        self.assertAlmostEqual(filas[0]["tiempo_activo_h"], 0.8333, places=3)

    def test_suma_solo_la_parte_no_solapada_en_un_solapamiento_parcial(self):
        # Dos tramos que se pisan a medias (no uno contenido en el otro):
        # 10:00-10:30 (0.5h) y 10:20-10:40 (0.333h). El real de pared es
        # 10:00-10:40 = 0.667h, no la suma cruda (0.833h).
        filas = rf.agregar_por_feature([
            registro(
                "feature-a", 1000, 0.5,
                inicio="2026-08-30T13:00:00Z", fin="2026-08-30T13:30:00Z",
            ),
            registro(
                "feature-a", 500, 0.333,
                inicio="2026-08-30T13:20:00Z", fin="2026-08-30T13:40:00Z",
            ),
        ])
        self.assertAlmostEqual(filas[0]["tiempo_activo_h"], 0.6667, places=3)

    def test_tramos_genuinamente_disjuntos_se_siguen_sumando(self):
        # Si la feature se trabajo en dos ventanas de tiempo que no se tocan
        # (ej. dos dias distintos), el tiempo real es la suma de ambas -- no
        # hay nada que fusionar.
        filas = rf.agregar_por_feature([
            registro(
                "feature-a", 1000, 0.5,
                inicio="2026-08-30T13:00:00Z", fin="2026-08-30T13:30:00Z",
            ),
            registro(
                "feature-a", 500, 0.25,
                inicio="2026-08-31T13:00:00Z", fin="2026-08-31T13:15:00Z",
            ),
        ])
        self.assertAlmostEqual(filas[0]["tiempo_activo_h"], 0.75, places=4)

    def test_marca_las_features_con_consumo_sin_tarifar(self):
        filas = rf.agregar_por_feature([
            registro("feature-a", 1000, 0.5, usd=0, tarifado=False),
        ])
        self.assertFalse(filas[0]["todo_tarifado"])

    def test_lista_vacia_no_rompe(self):
        self.assertEqual(rf.agregar_por_feature([]), [])

    def test_marca_modelos_multiples_si_algun_tramo_lo_tiene(self):
        filas = rf.agregar_por_feature([
            registro("feature-a", 1000, 0.5, modelos_multiples=True),
        ])
        self.assertTrue(filas[0]["modelos_multiples"])

    def test_sin_modelos_multiples_por_defecto(self):
        filas = rf.agregar_por_feature([
            registro("feature-a", 1000, 0.5),
        ])
        self.assertFalse(filas[0]["modelos_multiples"])

    def test_resume_complejidad_declarada_vs_inferida(self):
        filas = rf.agregar_por_feature([
            registro("feature-a", 1000, 0.5, origen_complejidad="declarado"),
            registro("feature-a", 500, 0.2, origen_complejidad="inferido"),
        ])
        self.assertEqual(filas[0]["marcador_complejidad"], "mixta")

    def test_una_feature_totalmente_inferida_queda_marcada(self):
        filas = rf.agregar_por_feature([
            registro("feature-a", 1000, 0.5, origen_complejidad="inferido"),
        ])
        self.assertEqual(filas[0]["marcador_complejidad"], "con inferidas")


class TestAgregacionPorEtapa(unittest.TestCase):
    def test_suma_tokens_por_etapa(self):
        filas = rf.agregar_por_etapa([
            registro("feature-a", 1000, 0.5, turnos=3, etapa="desarrollador"),
            registro("feature-a", 500, 0.25, turnos=2, etapa="desarrollador"),
            registro("feature-a", 200, 0.1, turnos=1, etapa="planificador"),
        ])
        por_etapa = {fila["etapa"]: fila for fila in filas}
        self.assertEqual(por_etapa["desarrollador"]["tokens_total"], 1500)
        self.assertEqual(por_etapa["desarrollador"]["turnos"], 5)
        self.assertEqual(por_etapa["desarrollador"]["conversaciones"], 2)
        self.assertEqual(por_etapa["planificador"]["tokens_total"], 200)

    def test_ordena_por_tokens_descendente(self):
        filas = rf.agregar_por_etapa([
            registro("f", 100, 0.1, etapa="qa"),
            registro("f", 9000, 0.1, etapa="desarrollador"),
        ])
        self.assertEqual(filas[0]["etapa"], "desarrollador")


class TestEtiquetaVisible(unittest.TestCase):
    def test_sin_feature_se_muestra_como_consumo_general_de_sesion(self):
        self.assertEqual(rf.etiqueta_visible(rf.ml.SIN_FEATURE), "Consumo general de sesión")

    def test_una_feature_real_no_se_toca(self):
        self.assertEqual(rf.etiqueta_visible("mi-feature"), "mi-feature")

    def test_valor_vacio_da_guion(self):
        self.assertEqual(rf.etiqueta_visible(None), "-")
        self.assertEqual(rf.etiqueta_visible(""), "-")


class TestMarkdown(unittest.TestCase):
    def test_genera_el_archivo(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            metrics = proyecto / "tsoft-dev" / "metrics"
            metrics.mkdir(parents=True)
            (metrics / "features.jsonl").write_text(
                json.dumps(registro("feature-a", 1000, 0.5)) + "\n",
                encoding="utf-8",
            )
            destino = rf.generar_markdown(proyecto)
            self.assertTrue(destino.exists())
            self.assertIn("feature-a", destino.read_text(encoding="utf-8"))

    def test_sin_feature_no_infla_el_kpi_pero_si_suma_al_total(self):
        # Caso real: 2 features de negocio + consumo suelto sin atribuir.
        # El KPI "Features" tiene que dar 2, no 3 -- pero los tokens de las
        # 3 filas tienen que seguir sumando al total (nada se esconde).
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            metrics = proyecto / "tsoft-dev" / "metrics"
            metrics.mkdir(parents=True)
            lineas_jsonl = [
                json.dumps(registro("feature-a", 1000, 0.5)),
                json.dumps(registro("feature-b", 500, 0.2)),
                json.dumps(registro(rf.ml.SIN_FEATURE, 200, 0.1)),
            ]
            (metrics / "features.jsonl").write_text("\n".join(lineas_jsonl) + "\n", encoding="utf-8")

            texto = rf.generar_markdown(proyecto).read_text(encoding="utf-8")

            self.assertIn("| Features | 2 |", texto)
            self.assertIn("| Tokens totales | 1,700 |", texto)
            self.assertIn("Consumo general de sesión", texto)
            self.assertNotIn("| sin-feature ", texto)

    def test_avisa_modelos_mixtos_en_una_linea_distinta_del_sin_tarifar(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            metrics = proyecto / "tsoft-dev" / "metrics"
            metrics.mkdir(parents=True)
            lineas_jsonl = [
                json.dumps(
                    registro(
                        "feature-mixta",
                        1000,
                        0.5,
                        modelos_multiples=True,
                        origen_tipo="declarado",
                        origen_complejidad="declarado",
                    )
                ),
                json.dumps(
                    registro(
                        "feature-sin-precio",
                        500,
                        0.1,
                        usd=0,
                        tarifado=False,
                        origen_tipo="declarado",
                        origen_complejidad="declarado",
                    )
                ),
            ]
            (metrics / "features.jsonl").write_text("\n".join(lineas_jsonl) + "\n", encoding="utf-8")

            destino = rf.generar_markdown(proyecto)
            texto = destino.read_text(encoding="utf-8")

            self.assertIn("feature-mixta", texto)
            self.assertIn("feature-sin-precio", texto)

            avisos = [linea for linea in texto.splitlines() if linea.startswith("> Aviso")]
            self.assertEqual(len(avisos), 2)

            aviso_mixtos = next(linea for linea in avisos if "feature-mixta" in linea)
            aviso_sin_tarifar = next(linea for linea in avisos if "feature-sin-precio" in linea)
            self.assertNotEqual(aviso_mixtos, aviso_sin_tarifar)
            self.assertNotIn("feature-sin-precio", aviso_mixtos)
            self.assertNotIn("feature-mixta", aviso_sin_tarifar)

    def test_incluye_seccion_de_consumo_por_etapa(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            metrics = proyecto / "tsoft-dev" / "metrics"
            metrics.mkdir(parents=True)
            (metrics / "features.jsonl").write_text(
                json.dumps(registro("feature-a", 1000, 0.5, etapa="desarrollador")) + "\n",
                encoding="utf-8",
            )
            texto = rf.generar_markdown(proyecto).read_text(encoding="utf-8")
        self.assertIn("## Consumo por etapa", texto)
        self.assertIn("desarrollador", texto)

    def test_muestra_aviso_y_columnas_cuando_hay_complejidad_inferida(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            escribir_features(proyecto, [
                registro_fechado(
                    "feature-mixta",
                    1000,
                    "2026-08-14T15:00:00Z",
                ),
                registro_fechado(
                    "feature-mixta",
                    500,
                    "2026-08-14T16:00:00Z",
                    session_id="s2",
                ) | {
                    "origen_complejidad": "declarado",
                    "origen_tipo": "declarado",
                    "tipo_tarea": "documentacion",
                    "complejidad": "media",
                },
            ])
            texto = rf.generar_markdown(proyecto).read_text(encoding="utf-8")

        self.assertIn("Complejidad (origen)", texto)
        self.assertIn("## Detalle por conversacion", texto)
        self.assertIn("Origen complejidad", texto)
        self.assertIn("mixta", texto)
        self.assertIn("tienen complejidad inferida", texto)
        self.assertIn("| Feature | Etapa | Inicio |", texto)

    def test_consumo_por_etapa_muestra_fila_vacia_sin_registros(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            metrics = proyecto / "tsoft-dev" / "metrics"
            metrics.mkdir(parents=True)
            (metrics / "features.jsonl").write_text("", encoding="utf-8")
            texto = rf.generar_markdown(proyecto).read_text(encoding="utf-8")
        seccion = texto.split("## Consumo por etapa")[1].split("## Detalle")[0]
        self.assertIn("Sin registros en el periodo", seccion)


def registro_fechado(feature, total, fin, session_id="s1"):
    """Registro con fecha, que es lo que el filtro de periodo mira."""
    datos = registro(feature, total, 0.1)
    datos["session_id"] = session_id
    datos["inicio"] = fin
    datos["fin"] = fin
    return datos


def escribir_features(proyecto: Path, registros: list) -> None:
    metrics = proyecto / "tsoft-dev" / "metrics"
    metrics.mkdir(parents=True, exist_ok=True)
    (metrics / "features.jsonl").write_text(
        "\n".join(json.dumps(item) for item in registros) + "\n", encoding="utf-8"
    )


class TestFiltroDePeriodo(unittest.TestCase):
    """
    El reconciliador reprocesa todos los rollouts en cada corrida, asi que el
    acumulado crece para siempre. El corte semanal tiene que poder pedirse.
    """

    def test_el_periodo_deja_afuera_lo_de_otra_semana(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            escribir_features(proyecto, [
                registro_fechado("de-esta-semana", 1000, "2026-08-14T15:00:00Z"),
                registro_fechado("de-hace-un-mes", 9000, "2026-07-10T15:00:00Z"),
            ])
            destino = rf.generar_markdown(
                proyecto, desde=date(2026, 8, 11), hasta=date(2026, 8, 17),
                etiqueta_periodo="Semanal 2026-08-11 a 2026-08-17",
            )
            texto = destino.read_text(encoding="utf-8")
        self.assertIn("de-esta-semana", texto)
        self.assertNotIn("de-hace-un-mes", texto)

    def test_sin_filtro_sigue_mostrando_todo(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            escribir_features(proyecto, [
                registro_fechado("de-esta-semana", 1000, "2026-08-14T15:00:00Z"),
                registro_fechado("de-hace-un-mes", 9000, "2026-07-10T15:00:00Z"),
            ])
            texto = rf.generar_markdown(proyecto).read_text(encoding="utf-8")
        self.assertIn("de-esta-semana", texto)
        self.assertIn("de-hace-un-mes", texto)
        self.assertIn("Acumulado historico", texto)

    def test_el_encabezado_declara_el_periodo(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            escribir_features(proyecto, [registro_fechado("f", 100, "2026-08-14T15:00:00Z")])
            texto = rf.generar_markdown(
                proyecto, desde=date(2026, 8, 11), hasta=date(2026, 8, 17),
                etiqueta_periodo="Semanal 2026-08-11 a 2026-08-17",
            ).read_text(encoding="utf-8")
        self.assertIn("Periodo: Semanal 2026-08-11 a 2026-08-17", texto)

    def test_un_periodo_vacio_no_rompe(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            escribir_features(proyecto, [registro_fechado("f", 100, "2026-07-10T15:00:00Z")])
            texto = rf.generar_markdown(
                proyecto, desde=date(2026, 8, 11), hasta=date(2026, 8, 17),
                etiqueta_periodo="Semanal",
            ).read_text(encoding="utf-8")
        self.assertIn("Sin registros en el periodo", texto)

    def test_avisa_si_una_feature_quedo_partida_entre_periodos(self):
        # Arranco la semana pasada y cerro esta: el numero semanal es una parte
        # de lo que costo, y leerlo como total subestima la feature.
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            escribir_features(proyecto, [
                registro_fechado("larga", 5000, "2026-08-05T15:00:00Z", session_id="s1"),
                registro_fechado("larga", 3000, "2026-08-14T15:00:00Z", session_id="s2"),
                registro_fechado("corta", 200, "2026-08-14T16:00:00Z", session_id="s3"),
            ])
            texto = rf.generar_markdown(
                proyecto, desde=date(2026, 8, 11), hasta=date(2026, 8, 17),
                etiqueta_periodo="Semanal",
            ).read_text(encoding="utf-8")

        aviso = next(l for l in texto.splitlines() if l.startswith("> Aviso") and "fuera" in l)
        self.assertIn("larga", aviso)
        self.assertNotIn("corta", aviso)

    def test_una_feature_entera_dentro_del_periodo_no_se_avisa(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            escribir_features(proyecto, [
                registro_fechado("corta", 200, "2026-08-14T16:00:00Z", session_id="s1"),
            ])
            texto = rf.generar_markdown(
                proyecto, desde=date(2026, 8, 11), hasta=date(2026, 8, 17),
                etiqueta_periodo="Semanal",
            ).read_text(encoding="utf-8")
        self.assertNotIn("fuera** del", texto)


def flags(**cambios):
    base = {"semana": False, "diario": False, "fecha": None, "desde": None, "hasta": None}
    base.update(cambios)
    return Namespace(**base)


class TestResolverPeriodo(unittest.TestCase):
    def test_sin_flags_no_filtra(self):
        self.assertEqual(rf.resolver_periodo(flags()), (None, None, None))

    def test_semana_son_siete_dias_contando_el_de_cierre(self):
        desde, hasta, _ = rf.resolver_periodo(flags(semana=True, fecha="2026-08-17"))
        self.assertEqual((desde, hasta), (date(2026, 8, 11), date(2026, 8, 17)))

    def test_diario_es_un_solo_dia(self):
        desde, hasta, _ = rf.resolver_periodo(flags(diario=True, fecha="2026-08-17"))
        self.assertEqual((desde, hasta), (date(2026, 8, 17), date(2026, 8, 17)))

    def test_rango_explicito(self):
        desde, hasta, etiqueta = rf.resolver_periodo(
            flags(desde="2026-08-01", hasta="2026-08-15")
        )
        self.assertEqual((desde, hasta), (date(2026, 8, 1), date(2026, 8, 15)))
        self.assertIn("2026-08-01", etiqueta)

    def test_desde_sin_hasta_es_error(self):
        with self.assertRaises(SystemExit):
            rf.resolver_periodo(flags(desde="2026-08-01"))

    def test_rango_invertido_es_error(self):
        with self.assertRaises(SystemExit):
            rf.resolver_periodo(flags(desde="2026-08-15", hasta="2026-08-01"))


class TestHtml(unittest.TestCase):
    """
    El HTML se genera con el estilo embutido en plantilla_html.py. No puede
    depender de TEMPLATE_DESARROLLO.html, que vive solo en el repo donde se
    diseno el kit y nunca viaja al repo del dev.
    """

    def _generar(self, proyecto, **kw):
        return rf.generar_html(proyecto, **kw).read_text(encoding="utf-8")

    def test_genera_el_html_al_lado_del_markdown(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            escribir_features(proyecto, [registro_fechado("pruebacolor", 1000, "2026-08-14T15:00:00Z")])
            destino = rf.generar_html(proyecto)
        self.assertEqual(destino.name, "features.html")
        self.assertEqual(destino.parent.name, "reportes")

    def test_sin_feature_no_infla_el_kpi_de_features_en_html(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            escribir_features(proyecto, [
                registro("feature-a", 1000, 0.5),
                registro("feature-b", 500, 0.2),
                registro(rf.ml.SIN_FEATURE, 200, 0.1),
            ])
            texto = self._generar(proyecto)

        self.assertIn("Consumo general de sesión", texto)
        self.assertNotIn('>sin-feature<', texto)
        self.assertIn('<div class="num">2</div><div class="label">Features</div>', texto)

    def test_el_estilo_va_inline_y_no_necesita_archivos_externos(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            escribir_features(proyecto, [registro_fechado("f", 1000, "2026-08-14T15:00:00Z")])
            texto = self._generar(proyecto)
        self.assertIn("<style>", texto)
        self.assertIn("--red:#E30613", texto)
        # Ni el template de diseno ni una hoja de estilos aparte.
        self.assertNotIn("TEMPLATE_DESARROLLO", texto)
        self.assertNotIn('rel="stylesheet" href="estilos', texto)

    def test_las_fuentes_tienen_fallback_del_sistema(self):
        # Un dev generando el reporte sin internet tiene que ver algo legible.
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            escribir_features(proyecto, [registro_fechado("f", 1000, "2026-08-14T15:00:00Z")])
            texto = self._generar(proyecto)
        self.assertIn("system-ui", texto)
        self.assertIn("monospace", texto)

    def test_usa_el_css_del_proyecto_si_existe(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            escribir_features(proyecto, [registro_fechado("f", 1000, "2026-08-14T15:00:00Z")])
            propio = proyecto / "tsoft-dev" / "config"
            propio.mkdir(parents=True)
            (propio / "estilos-reporte.css").write_text("body{ color:magenta; }", encoding="utf-8")
            texto = self._generar(proyecto)
        self.assertIn("magenta", texto)
        self.assertNotIn("--red:#E30613", texto)

    def test_un_css_propio_vacio_cae_al_default(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            escribir_features(proyecto, [registro_fechado("f", 1000, "2026-08-14T15:00:00Z")])
            propio = proyecto / "tsoft-dev" / "config"
            propio.mkdir(parents=True)
            (propio / "estilos-reporte.css").write_text("   \n", encoding="utf-8")
            texto = self._generar(proyecto)
        self.assertIn("--red:#E30613", texto)

    def test_el_html_declara_el_periodo(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            escribir_features(proyecto, [registro_fechado("f", 1000, "2026-08-14T15:00:00Z")])
            texto = self._generar(
                proyecto, desde=date(2026, 8, 11), hasta=date(2026, 8, 17),
                etiqueta_periodo="Semanal 2026-08-11 a 2026-08-17",
            )
        self.assertIn("Semanal 2026-08-11 a 2026-08-17", texto)

    def test_el_html_y_el_markdown_dan_el_mismo_total(self):
        # Los dos salen de calcular(): no pueden divergir.
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            escribir_features(proyecto, [
                registro_fechado("a", 1_234_567, "2026-08-14T15:00:00Z", session_id="s1"),
                registro_fechado("b", 7_654_321, "2026-08-15T15:00:00Z", session_id="s2"),
            ])
            md = rf.generar_markdown(proyecto).read_text(encoding="utf-8")
            texto = self._generar(proyecto)
        self.assertIn("8,888,888", md)      # formato Markdown
        self.assertIn("8.888.888", texto)   # formato local del HTML

    def test_escapa_lo_que_viene_del_rollout(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            escribir_features(proyecto, [
                registro_fechado("<script>alert(1)</script>", 100, "2026-08-14T15:00:00Z"),
            ])
            texto = self._generar(proyecto)
        self.assertNotIn("<script>alert(1)</script>", texto)
        self.assertIn("&lt;script&gt;", texto)

    def test_un_periodo_vacio_genera_html_valido(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            escribir_features(proyecto, [registro_fechado("f", 100, "2026-07-10T15:00:00Z")])
            texto = self._generar(
                proyecto, desde=date(2026, 8, 11), hasta=date(2026, 8, 17),
                etiqueta_periodo="Semanal",
            )
        self.assertIn("Sin registros en el periodo", texto)
        self.assertIn("</html>", texto)

    def test_sin_features_jsonl_no_rompe(self):
        with directorio_temporal() as tmp:
            texto = self._generar(Path(tmp))
        self.assertIn("</html>", texto)

    def test_incluye_seccion_de_consumo_por_etapa(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            escribir_features(proyecto, [registro("feature-a", 1000, 0.5, etapa="desarrollador")])
            texto = self._generar(proyecto)
        self.assertIn("Consumo por etapa", texto)
        self.assertIn("desarrollador", texto)

    def test_muestra_clasificacion_y_aviso_de_inferidas(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            escribir_features(proyecto, [
                registro_fechado("feature-a", 1000, "2026-08-14T15:00:00Z"),
                registro_fechado(
                    "feature-a",
                    500,
                    "2026-08-14T16:00:00Z",
                    session_id="s2",
                ) | {
                    "origen_complejidad": "declarado",
                    "origen_tipo": "declarado",
                    "tipo_tarea": "documentacion",
                    "complejidad": "media",
                },
            ])
            texto = self._generar(proyecto)
        self.assertIn("Complejidad (origen)", texto)
        self.assertIn("Origen complejidad", texto)
        self.assertIn("mixta", texto)
        self.assertIn("complejidad inferida", texto)
        self.assertIn("Etapa", texto)


if __name__ == "__main__":
    unittest.main()
