"""Tests del reconciliador. Correr con: py tsoft-dev/scripts/tests/test_reconciliador.py"""

import io
import json
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers_temporal import directorio_temporal
import reconciliador as rc


def escribir_rollout(carpeta: Path, nombre: str, cwd: str, eventos_extra=None):
    """
    Crea un rollout minimo con session_meta y devuelve su ruta.

    session_meta NO trae "model" a proposito: en los rollouts reales de Codex
    esa clave vive en los eventos turn_context, no en session_meta (ver
    detectar_modelo). Los tests que necesiten un modelo deben agregar un
    evento con evento_turn_context().
    """
    ruta = carpeta / nombre
    lineas = [
        {
            "timestamp": "2026-08-11T10:00:00Z",
            "type": "session_meta",
            "payload": {
                "session_id": nombre.replace("rollout-", "").replace(".jsonl", ""),
                "cwd": cwd,
                "originator": "codex_vscode",
            },
        }
    ]
    lineas.extend(eventos_extra or [])
    ruta.write_text(
        "\n".join(json.dumps(linea, ensure_ascii=False) for linea in lineas),
        encoding="utf-8",
    )
    return ruta


def evento_turn_context(modelo, ts="2026-08-11T10:00:00Z"):
    """Evento turn_context real: el modelo vive en payload.model, no en session_meta."""
    return {
        "timestamp": ts,
        "type": "turn_context",
        "payload": {"model": modelo},
    }


class TestDescubrimiento(unittest.TestCase):
    def test_lista_rollouts_de_subcarpetas(self):
        with directorio_temporal() as tmp:
            base = Path(tmp)
            dia = base / "2026" / "08" / "11"
            dia.mkdir(parents=True)
            escribir_rollout(dia, "rollout-uno.jsonl", "c:\\proyecto")
            escribir_rollout(dia, "rollout-dos.jsonl", "c:\\proyecto")
            (dia / "otra-cosa.txt").write_text("ruido", encoding="utf-8")

            encontrados = rc.listar_rollouts(base)
            self.assertEqual(len(encontrados), 2)

    def test_raiz_inexistente_devuelve_lista_vacia(self):
        self.assertEqual(rc.listar_rollouts(Path("no") / "existe"), [])

    def test_lee_session_meta(self):
        eventos = [
            {"type": "session_meta", "payload": {"cwd": "c:\\proyecto", "model": "gpt-5.4"}},
            {"type": "event_msg", "payload": {"type": "user_message", "message": "hola"}},
        ]
        meta = rc.leer_session_meta(eventos)
        self.assertEqual(meta["model"], "gpt-5.4")

    def test_session_meta_ausente_devuelve_dict_vacio(self):
        self.assertEqual(rc.leer_session_meta([{"type": "event_msg"}]), {})

    def test_raiz_sesiones_respeta_codex_home(self):
        # Herramientas de orquestacion (Orca) relanzan Codex con CODEX_HOME
        # apuntando a otro lado para poder leer la transcripcion de los
        # agentes. Si raiz_sesiones() lo ignora, busca en ~/.codex/sessions
        # mientras los rollouts reales quedan en otro lado: Registros: 0
        # sin ningun error visible.
        with patch.dict("os.environ", {"CODEX_HOME": "D:\\otro\\home"}):
            self.assertEqual(rc.raiz_sesiones(), Path("D:\\otro\\home") / "sessions")

    def test_raiz_sesiones_sin_codex_home_cae_al_default(self):
        with patch.dict("os.environ", {}, clear=False):
            import os as _os
            _os.environ.pop("CODEX_HOME", None)
            self.assertEqual(rc.raiz_sesiones(), Path.home() / ".codex" / "sessions")


class TestFiltrado(unittest.TestCase):
    def test_acepta_rollout_del_proyecto(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            meta = {"cwd": str(proyecto)}
            self.assertTrue(rc.pertenece_al_proyecto(meta, proyecto))

    def test_ignora_mayusculas_del_path_en_windows(self):
        # Path.resolve() normaliza el case consultando el filesystem, asi que
        # con un directorio real este test pasaria igual sin normcase. Se usa
        # una ruta inexistente para que la unica normalizacion posible sea la
        # de normcase.
        if not sys.platform.startswith("win"):
            self.skipTest("el case-insensitive de paths es especifico de Windows")
        proyecto = Path("C:/no/existe/proyecto-fantasma")
        meta = {"cwd": "c:\\NO\\EXISTE\\PROYECTO-FANTASMA"}
        self.assertTrue(rc.pertenece_al_proyecto(meta, proyecto))

    def test_rechaza_rollout_de_otro_proyecto(self):
        # Dos carpetas temporales independientes: ninguna es ancestro de la
        # otra, asi que representan proyectos genuinamente distintos (a
        # diferencia de una subcarpeta, que si se acepta - ver
        # test_acepta_rollout_iniciado_desde_una_subcarpeta).
        with directorio_temporal() as tmp_proyecto, directorio_temporal() as tmp_otro:
            proyecto = Path(tmp_proyecto)
            meta = {"cwd": tmp_otro}
            self.assertFalse(rc.pertenece_al_proyecto(meta, proyecto))

    def test_rechaza_meta_sin_cwd(self):
        self.assertFalse(rc.pertenece_al_proyecto({}, Path.cwd()))

    def test_acepta_rollout_iniciado_desde_una_subcarpeta(self):
        # Un dev que hizo cd a tsoft-dev/ antes de abrir Codex no deberia
        # perder su rollout: sigue siendo trabajo sobre este proyecto.
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            subcarpeta = proyecto / "tsoft-dev"
            subcarpeta.mkdir()
            meta = {"cwd": str(subcarpeta)}
            self.assertTrue(rc.pertenece_al_proyecto(meta, proyecto))

    def test_rechaza_directorio_hermano_que_comparte_prefijo_del_nombre(self):
        # "tsoft-ai-portal-backup" no es una subcarpeta de "tsoft-ai-portal":
        # un startswith ingenuo (sin exigir el separador) los confundiria.
        with directorio_temporal() as tmp:
            base = Path(tmp)
            proyecto = base / "tsoft-ai-portal"
            hermano = base / "tsoft-ai-portal-backup"
            proyecto.mkdir()
            hermano.mkdir()
            meta = {"cwd": str(hermano)}
            self.assertFalse(rc.pertenece_al_proyecto(meta, proyecto))


CONFIG = {
    "precios_usd_por_millon": {
        "gpt-5.4": {"input": 2.50, "cache": 0.25, "output": 15.00},
        "_default": {"input": 0, "cache": 0, "output": 0},
    },
    "moneda_local": "ARS",
    "usd_a_moneda_local": 1550,
    "umbral_inactividad_min": 30,
}

BASELINES = {
    "tipo_default": "evolutivo-frontend",
    "tipos_validos": ["evolutivo-frontend", "documentacion"],
    "umbrales_complejidad": {"media": 4, "alta": 12},
}


def evento_usuario(mensaje, ts="2026-08-11T10:00:00Z"):
    return {
        "timestamp": ts,
        "type": "event_msg",
        "payload": {"type": "user_message", "message": mensaje},
    }


def evento_escritura(ruta, ts="2026-08-11T10:00:00Z"):
    """Escritura de un archivo, tal como la registra el rollout real."""
    return {
        "timestamp": ts,
        "type": "response_item",
        "payload": {
            "type": "function_call",
            "name": "apply_patch",
            "arguments": json.dumps({"path": ruta}),
        },
    }


def evento_tokens(total, ts="2026-08-11T10:00:00Z"):
    return {
        "timestamp": ts,
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "last_token_usage": {
                    "input_tokens": total,
                    "cached_input_tokens": 0,
                    "output_tokens": 0,
                    "reasoning_output_tokens": 0,
                    "total_tokens": total,
                }
            },
        },
    }


class TestConstruccionDeRegistros(unittest.TestCase):
    def test_genera_un_registro_por_feature(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            rollout = escribir_rollout(
                proyecto,
                "rollout-abc.jsonl",
                str(proyecto),
                [
                    evento_usuario("$orquestador feature-a"),
                    evento_tokens(1000, ts="2026-08-11T10:00:00Z"),
                    evento_usuario("$orquestador feature-b", ts="2026-08-11T10:05:00Z"),
                    evento_tokens(2000, ts="2026-08-11T10:10:00Z"),
                ],
            )
            registros = rc.construir_registros(rollout, proyecto, CONFIG, "dev@tsoft.com")
            features = {registro["feature"]: registro for registro in registros}
            self.assertEqual(features["feature-a"]["tokens"]["total"], 1000)
            self.assertEqual(features["feature-b"]["tokens"]["total"], 2000)

    def test_el_registro_trae_los_campos_del_esquema(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            rollout = escribir_rollout(
                proyecto,
                "rollout-abc.jsonl",
                str(proyecto),
                [evento_usuario("$orquestador feature-a"), evento_tokens(1000)],
            )
            registro = rc.construir_registros(rollout, proyecto, CONFIG, "dev@tsoft.com")[0]
            for campo in (
                "feature", "estado", "developer", "session_id", "rollout",
                "origen", "modelo", "inicio", "fin", "tiempo_activo_h",
                "tiempo_pared_h", "turnos", "tokens", "costo", "evidencia",
                "tipo_tarea", "complejidad", "origen_tipo", "origen_complejidad",
            ):
                self.assertIn(campo, registro)
            self.assertEqual(registro["developer"], "dev@tsoft.com")
            self.assertEqual(registro["origen"], "codex_vscode")

    def test_persiste_clasificacion_declarada(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            rollout = escribir_rollout(
                proyecto,
                "rollout-abc.jsonl",
                str(proyecto),
                [
                    evento_usuario(
                        "$orquestador feature-a "
                        "#tarea:documentacion #complejidad:media"
                    ),
                    evento_tokens(1000),
                ],
            )
            registro = rc.construir_registros(
                rollout, proyecto, CONFIG, "dev@tsoft.com", baselines=BASELINES
            )[0]
            self.assertEqual(registro["tipo_tarea"], "documentacion")
            self.assertEqual(registro["complejidad"], "media")
            self.assertEqual(registro["origen_tipo"], "declarado")
            self.assertEqual(registro["origen_complejidad"], "declarado")

    def test_persiste_clasificacion_inferida_sin_degradar_el_caso_mixto(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            rollout_declarado = escribir_rollout(
                proyecto,
                "rollout-declarado.jsonl",
                str(proyecto),
                [
                    evento_usuario(
                        "$orquestador feature-a "
                        "#tarea:documentacion #complejidad:baja"
                    ),
                    evento_tokens(1000),
                ],
            )
            rollout_inferido = escribir_rollout(
                proyecto,
                "rollout-inferido.jsonl",
                str(proyecto),
                [
                    evento_usuario("$orquestador feature-a"),
                    evento_escritura("src/components/Panel.jsx"),
                    evento_tokens(1500),
                ],
            )
            declarados = rc.construir_registros(
                rollout_declarado, proyecto, CONFIG, "dev@tsoft.com", baselines=BASELINES
            )
            inferidos = rc.construir_registros(
                rollout_inferido, proyecto, CONFIG, "dev@tsoft.com", baselines=BASELINES
            )

        registros = declarados + inferidos
        origenes = {registro["origen_complejidad"] for registro in registros}
        self.assertEqual(origenes, {"declarado", "inferido"})
        self.assertEqual(inferidos[0]["tipo_tarea"], "evolutivo-frontend")
        self.assertEqual(inferidos[0]["complejidad"], "baja")

    def test_ignora_rollouts_de_otro_proyecto(self):
        # cwd de un proyecto genuinamente distinto (no una subcarpeta: esa
        # se acepta, ver TestFiltrado.test_acepta_rollout_iniciado_desde_una_subcarpeta).
        with directorio_temporal() as tmp_proyecto, directorio_temporal() as tmp_otro:
            proyecto = Path(tmp_proyecto)
            rollout = escribir_rollout(
                proyecto, "rollout-abc.jsonl", tmp_otro,
                [evento_usuario("$orquestador feature-a"), evento_tokens(1000)],
            )
            self.assertEqual(rc.construir_registros(rollout, proyecto, CONFIG, "dev@tsoft.com"), [])

    def test_calcula_costo_con_la_formula_corregida(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            rollout = escribir_rollout(
                proyecto, "rollout-abc.jsonl", str(proyecto),
                [
                    evento_turn_context("gpt-5.4"),
                    evento_usuario("$orquestador feature-a"),
                    evento_tokens(1_000_000),
                ],
            )
            registro = rc.construir_registros(rollout, proyecto, CONFIG, "dev@tsoft.com")[0]
            # 1M de input sin cache a 2.50 USD por millon.
            self.assertAlmostEqual(registro["costo"]["usd"], 2.50, places=4)

    def test_un_solo_modelo_marca_modelos_multiples_falso(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            rollout = escribir_rollout(
                proyecto, "rollout-abc.jsonl", str(proyecto),
                [
                    evento_turn_context("gpt-5.4"),
                    evento_usuario("$orquestador feature-a"),
                    evento_tokens(1000),
                ],
            )
            registro = rc.construir_registros(rollout, proyecto, CONFIG, "dev@tsoft.com")[0]
            self.assertFalse(registro["modelos_multiples"])
            self.assertEqual(registro["modelos_detectados"], ["gpt-5.4"])

    def test_dos_modelos_distintos_marcan_modelos_multiples_verdadero(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            rollout = escribir_rollout(
                proyecto, "rollout-abc.jsonl", str(proyecto),
                [
                    evento_turn_context("gpt-5.4"),
                    evento_usuario("$orquestador feature-a"),
                    evento_tokens(1000),
                    evento_turn_context("gpt-6", ts="2026-08-11T10:05:00Z"),
                    evento_tokens(500, ts="2026-08-11T10:06:00Z"),
                ],
            )
            registro = rc.construir_registros(rollout, proyecto, CONFIG, "dev@tsoft.com")[0]
            self.assertTrue(registro["modelos_multiples"])
            self.assertEqual(registro["modelos_detectados"], ["gpt-5.4", "gpt-6"])


class TestDeteccionDeModelo(unittest.TestCase):
    def test_detecta_modelo_desde_turn_context(self):
        # session_meta real no trae "model": vive en el payload de turn_context.
        eventos = [
            {"type": "session_meta", "payload": {"cwd": "c:\\proyecto"}},
            evento_turn_context("gpt-5.4"),
        ]
        meta = rc.leer_session_meta(eventos)
        self.assertEqual(rc.detectar_modelo(eventos, meta), "gpt-5.4")

    def test_session_meta_model_gana_si_esta_presente(self):
        # Si una version futura de Codex agrega "model" a session_meta, gana
        # sobre lo que diga turn_context.
        eventos = [
            {"type": "session_meta", "payload": {"cwd": "c:\\proyecto", "model": "gpt-6"}},
            evento_turn_context("gpt-5.4"),
        ]
        meta = rc.leer_session_meta(eventos)
        self.assertEqual(rc.detectar_modelo(eventos, meta), "gpt-6")

    def test_sin_modelo_en_ningun_lado_devuelve_vacio(self):
        eventos = [{"type": "session_meta", "payload": {"cwd": "c:\\proyecto"}}]
        meta = rc.leer_session_meta(eventos)
        self.assertEqual(rc.detectar_modelo(eventos, meta), "")


class TestDetectorDeveloper(unittest.TestCase):
    def test_corre_git_con_la_raiz_del_proyecto_como_cwd(self):
        # Sin esto, subprocess.run hereda el cwd del proceso, y correr el
        # reconciliador desde otro repo resolveria una identidad git ajena.
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            with patch("reconciliador.subprocess.run") as mock_run:
                mock_run.return_value.stdout = "dev@tsoft.com\n"
                rc.detectar_developer(proyecto)
                _, kwargs = mock_run.call_args
                self.assertEqual(kwargs.get("cwd"), str(proyecto))


class TestEscritura(unittest.TestCase):
    def test_regenera_el_archivo_en_cada_corrida(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            (proyecto / "tsoft-dev" / "metrics").mkdir(parents=True)
            registros = [{"feature": "feature-a", "tokens": {"total": 1}}]

            rc.escribir_features(registros, proyecto)
            rc.escribir_features(registros, proyecto)

            lineas = rc.ruta_features(proyecto).read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lineas), 1)  # no se duplico

    def test_no_toca_el_ledger(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            metrics = proyecto / "tsoft-dev" / "metrics"
            metrics.mkdir(parents=True)
            ledger = metrics / "ledger.jsonl"
            ledger.write_text('{"evento":"ejecucion"}\n', encoding="utf-8")
            original = ledger.read_text(encoding="utf-8")

            rc.escribir_features([{"feature": "feature-a"}], proyecto)

            self.assertEqual(ledger.read_text(encoding="utf-8"), original)

    def test_no_vacia_el_archivo_si_no_hay_registros_nuevos_y_ya_tenia_historico(self):
        # Caso real: CODEX_HOME mal seteado o raiz de sesiones vacia/purgada
        # -- el reconciliador no encuentra nada, pero "no encontre nada" no
        # es lo mismo que "la verdad es cero". No debe borrar el historico.
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            (proyecto / "tsoft-dev" / "metrics").mkdir(parents=True)
            rc.escribir_features([{"feature": "feature-a", "tokens": {"total": 1}}], proyecto)
            contenido_previo = rc.ruta_features(proyecto).read_text(encoding="utf-8")

            captura = io.StringIO()
            with redirect_stderr(captura):
                rc.escribir_features([], proyecto)

            self.assertEqual(rc.ruta_features(proyecto).read_text(encoding="utf-8"), contenido_previo)
            self.assertIn("aviso", captura.getvalue())
            self.assertIn("preserva", captura.getvalue())

    def test_permitir_vacio_fuerza_el_vaciado_aunque_habia_historico(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            (proyecto / "tsoft-dev" / "metrics").mkdir(parents=True)
            rc.escribir_features([{"feature": "feature-a", "tokens": {"total": 1}}], proyecto)

            rc.escribir_features([], proyecto, permitir_vacio=True)

            self.assertEqual(rc.ruta_features(proyecto).read_text(encoding="utf-8"), "")

    def test_cero_registros_sin_historico_previo_no_es_un_problema(self):
        # Primera corrida legitima sin nada que reportar todavia: no hay
        # nada que "preservar", asi que no debe avisar ni bloquear.
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            (proyecto / "tsoft-dev" / "metrics").mkdir(parents=True)

            captura = io.StringIO()
            with redirect_stderr(captura):
                rc.escribir_features([], proyecto)

            self.assertEqual(rc.ruta_features(proyecto).read_text(encoding="utf-8"), "")
            self.assertEqual(captura.getvalue(), "")


class TestCuotaEnElRegistro(unittest.TestCase):
    def test_el_registro_incluye_la_cuota_de_la_conversacion(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            evento = evento_tokens(1000)
            evento["payload"]["rate_limits"] = {
                "plan_type": "team",
                "primary": {"used_percent": 12.0, "window_minutes": 10080},
            }
            rollout = escribir_rollout(
                proyecto, "rollout-abc.jsonl", str(proyecto),
                [evento_turn_context("gpt-5.4"), evento_usuario("$orquestador feature-a"), evento],
            )
            registro = rc.construir_registros(rollout, proyecto, CONFIG, "dev@tsoft.com")[0]
            self.assertEqual(registro["cuota"]["pico"], 12.0)
            self.assertEqual(registro["cuota"]["plan"], "team")

    def test_sin_lecturas_de_cuota_el_campo_queda_en_none(self):
        # El campo existe siempre, para que la forma del registro sea estable.
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            rollout = escribir_rollout(
                proyecto, "rollout-abc.jsonl", str(proyecto),
                [evento_turn_context("gpt-5.4"), evento_usuario("$orquestador feature-a"), evento_tokens(1000)],
            )
            registro = rc.construir_registros(rollout, proyecto, CONFIG, "dev@tsoft.com")[0]
            self.assertIn("cuota", registro)
            self.assertIsNone(registro["cuota"])


class TestFeatureDesdeEvidencia(unittest.TestCase):
    """
    Respaldo de atribucion que no depende de como se redacto el prompt: si la
    conversacion escribio en tsoft-dev/<feature>/, es trabajo de esa feature.
    Se apoya en lo que la conversacion HIZO, no en lo que alguien ESCRIBIO.
    """

    def test_deduce_la_feature_de_la_carpeta_tocada(self):
        tocados = [
            r"C:\repo\tsoft-dev\mensajeria\qa.md",
            r"C:\repo\src\components\Dashboard\index.jsx",
        ]
        self.assertEqual(rc.feature_desde_evidencia(tocados), "mensajeria")

    def test_acepta_barras_normales(self):
        self.assertEqual(
            rc.feature_desde_evidencia(["/home/x/repo/tsoft-dev/mensajeria/design.md"]),
            "mensajeria",
        )

    def test_ignora_las_carpetas_propias_del_kit(self):
        # scripts, metrics, config y reportes son del kit, no features.
        tocados = [
            r"C:\repo\tsoft-dev\scripts\metrics_lib.py",
            r"C:\repo\tsoft-dev\metrics\ledger.jsonl",
            r"C:\repo\tsoft-dev\config\celula.json",
            r"C:\repo\tsoft-dev\reportes\features.md",
        ]
        self.assertIsNone(rc.feature_desde_evidencia(tocados))

    def test_dos_features_distintas_es_ambiguo(self):
        tocados = [
            r"C:\repo\tsoft-dev\mensajeria\qa.md",
            r"C:\repo\tsoft-dev\cambiocolor\design.md",
        ]
        self.assertIsNone(rc.feature_desde_evidencia(tocados))

    def test_sin_rutas_del_kit_no_deduce_nada(self):
        self.assertIsNone(rc.feature_desde_evidencia([r"C:\repo\src\App.jsx"]))
        self.assertIsNone(rc.feature_desde_evidencia([]))

    def test_normaliza_el_nombre_de_la_carpeta(self):
        # La carpeta feature-cambios.md debe caer en el mismo bucket que el
        # nombre que produce la deteccion por texto.
        self.assertEqual(
            rc.feature_desde_evidencia([r"C:\repo\tsoft-dev\feature-cambios.md\design.md"]),
            "feature-cambios",
        )


class TestRespaldoDeAtribucion(unittest.TestCase):
    def test_atribuye_una_conversacion_sin_marcador_de_texto(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            rollout = escribir_rollout(
                proyecto,
                "rollout-abc.jsonl",
                str(proyecto),
                [
                    evento_turn_context("gpt-5.4"),
                    # Sin $orquestador ni despacho: solo se ve que escribio.
                    evento_usuario("continuemos con lo que quedo pendiente"),
                    evento_escritura(r"C:\repo\tsoft-dev\mensajeria\qa.md"),
                    evento_tokens(1000),
                ],
            )
            registros = rc.construir_registros(rollout, proyecto, CONFIG, "dev@tsoft.com")
            self.assertEqual([r["feature"] for r in registros], ["mensajeria"])
            self.assertEqual(registros[0]["tokens"]["total"], 1000)

    def test_no_pisa_la_atribucion_por_texto(self):
        # El marcador explicito manda; el respaldo solo actua si no hubo ninguno.
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            rollout = escribir_rollout(
                proyecto,
                "rollout-abc.jsonl",
                str(proyecto),
                [
                    evento_turn_context("gpt-5.4"),
                    evento_usuario("$orquestador cambiocolor"),
                    evento_escritura(r"C:\repo\tsoft-dev\mensajeria\qa.md"),
                    evento_tokens(1000),
                ],
            )
            registros = rc.construir_registros(rollout, proyecto, CONFIG, "dev@tsoft.com")
            self.assertEqual([r["feature"] for r in registros], ["cambiocolor"])

    def test_sin_evidencia_queda_sin_feature(self):
        with directorio_temporal() as tmp:
            proyecto = Path(tmp)
            rollout = escribir_rollout(
                proyecto,
                "rollout-abc.jsonl",
                str(proyecto),
                [
                    evento_turn_context("gpt-5.4"),
                    evento_usuario("una consulta suelta"),
                    evento_tokens(800),
                ],
            )
            registros = rc.construir_registros(rollout, proyecto, CONFIG, "dev@tsoft.com")
            self.assertEqual([r["feature"] for r in registros], ["sin-feature"])



def rollout_con_spawn(carpeta, nombre, cwd, padre, rol="explorador", ts="2026-08-11T10:05:00Z",
                      eventos_extra=None):
    """
    Rollout de una conversacion de subagente, con su thread_spawn.

    Reproduce la forma real de session_meta en un subagente: "id" es el
    thread propio (derivado del nombre del archivo, como antes) y
    "session_id" es el de la sesion a la que pertenece -- el padre, igual a
    parent_thread_id. Indexar por "session_id" hace que el hijo colisione con
    el padre; por eso ml.id_conversacion prefiere "id".
    """
    ruta = carpeta / nombre
    propio = nombre.replace("rollout-", "").replace(".jsonl", "")
    lineas = [
        {
            "timestamp": ts,
            "type": "session_meta",
            "payload": {
                "id": propio,
                "session_id": padre,
                "cwd": cwd,
                "originator": "codex_vscode",
                "timestamp": ts,
                "source": {
                    "subagent": {
                        "thread_spawn": {
                            "parent_thread_id": padre,
                            "depth": 1,
                            "agent_path": None,
                            "agent_nickname": "Mapper",
                            "agent_role": rol,
                        }
                    }
                },
            },
        }
    ]
    lineas.extend(eventos_extra or [])
    if not eventos_extra:
        lineas.append({})
    ruta.write_text("\n".join(json.dumps(l, ensure_ascii=False) for l in lineas), encoding="utf-8")
    return ruta


def ev_usuario(mensaje, ts="2026-08-11T10:00:00Z"):
    return {"timestamp": ts, "type": "event_msg",
            "payload": {"type": "user_message", "message": mensaje}}


def ev_tokens(total, ts="2026-08-11T10:00:05Z"):
    return {"timestamp": ts, "type": "event_msg", "payload": {"type": "token_count", "info": {
        "last_token_usage": {"input_tokens": total, "cached_input_tokens": 0,
                             "output_tokens": 0, "reasoning_output_tokens": 0,
                             "total_tokens": total},
        "total_token_usage": {"total_tokens": total}}}}


class TestConstruirIndice(unittest.TestCase):
    def test_indexa_el_padre_el_rol_y_las_features(self):
        with directorio_temporal() as tmp:
            carpeta = Path(tmp)
            escribir_rollout(carpeta, "rollout-padre.jsonl", "c:\\proy", [
                ev_usuario("$orquestador feature-a"), ev_tokens(100),
            ])
            rollout_con_spawn(carpeta, "rollout-hijo.jsonl", "c:\\proy", padre="padre")
            indice = rc.construir_indice(sorted(carpeta.glob("rollout-*.jsonl")))

        self.assertEqual(indice["hijo"]["padre"], "padre")
        self.assertEqual(indice["hijo"]["rol"], "explorador")
        self.assertEqual([n for n, _e in indice["padre"]["features"]], ["feature-a"])

    def test_las_features_quedan_ordenadas_por_inicio(self):
        with directorio_temporal() as tmp:
            carpeta = Path(tmp)
            escribir_rollout(carpeta, "rollout-p.jsonl", "c:\\proy", [
                ev_usuario("$orquestador segunda", ts="2026-08-11T11:00:00Z"),
                ev_tokens(50, ts="2026-08-11T11:00:05Z"),
                ev_usuario("$orquestador primera", ts="2026-08-11T10:00:00Z"),
                ev_tokens(100, ts="2026-08-11T10:00:05Z"),
            ])
            indice = rc.construir_indice(sorted(carpeta.glob("rollout-*.jsonl")))
        # Se ordena por el epoch del primer evento, no por orden de aparicion.
        self.assertEqual([n for n, _e in indice["p"]["features"]], ["primera", "segunda"])

    def test_source_como_string_no_rompe_el_indice(self):
        with directorio_temporal() as tmp:
            carpeta = Path(tmp)
            escribir_rollout(carpeta, "rollout-a.jsonl", "c:\\proy", [ev_tokens(10)])
            indice = rc.construir_indice(sorted(carpeta.glob("rollout-*.jsonl")))
        self.assertIsNone(indice["a"]["padre"])

    def test_indexa_sin_filtrar_por_proyecto(self):
        # Si se filtrara antes, un padre de otro proyecto cortaria la cadena.
        with directorio_temporal() as tmp:
            carpeta = Path(tmp)
            escribir_rollout(carpeta, "rollout-otro.jsonl", "d:\\otro-proyecto", [ev_tokens(10)])
            indice = rc.construir_indice(sorted(carpeta.glob("rollout-*.jsonl")))
        self.assertIn("otro", indice)

    def test_un_rollout_ilegible_no_corta_el_indice(self):
        with directorio_temporal() as tmp:
            carpeta = Path(tmp)
            (carpeta / "rollout-roto.jsonl").write_text("{no es json", encoding="utf-8")
            escribir_rollout(carpeta, "rollout-sano.jsonl", "c:\\proy", [ev_tokens(10)])
            indice = rc.construir_indice(sorted(carpeta.glob("rollout-*.jsonl")))
        self.assertIn("sano", indice)

    def test_indice_vacio_si_no_hay_rollouts(self):
        self.assertEqual(rc.construir_indice([]), {})

    def test_resuelve_aunque_session_id_traiga_el_id_del_padre(self):
        # Forma real de un rollout de subagente: session_meta.id es el thread
        # propio y session_meta.session_id es el del padre. Indexar por
        # session_id hace que el hijo sobreescriba al padre en el indice.
        with directorio_temporal() as tmp:
            carpeta = Path(tmp)
            escribir_rollout(carpeta, "rollout-padre.jsonl", tmp, [
                ev_usuario("$orquestador feature-a"), ev_tokens(100)])
            rollout_con_spawn(carpeta, "rollout-hijo.jsonl", tmp, padre="padre",
                              eventos_extra=[ev_tokens(900, ts="2026-08-11T10:06:00Z")])
            rollouts = sorted(carpeta.glob("rollout-*.jsonl"))
            indice = rc.construir_indice(rollouts)

            # El padre NO puede haber sido sobreescrito por el hijo.
            self.assertIn("padre", indice)
            self.assertIn("hijo", indice)
            self.assertEqual(indice["hijo"]["padre"], "padre")
            self.assertEqual(rc.resolver_por_grafo("hijo", indice)[0], "feature-a")


def nodo(features=(), padre=None, inicio=None):
    """Nodo del indice, armado a mano para testear la resolucion."""
    return {"padre": padre, "rol": None, "apodo": None, "depth": None,
            "inicio": inicio, "features": list(features)}


class TestFeatureActivaEn(unittest.TestCase):
    """
    El subagente hereda la feature ACTIVA EN EL PADRE al momento de nacer.

    Caso real que lo motiva: un rollout del 30/07 toco tres features
    (feaure-cambiodecolor, feature-cambios, feature-prueba-hooks) y lanzo
    cuatro subagentes. Con "la primera del padre" los cuatro se atribuyen mal,
    los totales cierran igual, y el error queda invisible.
    """

    def test_elige_la_ultima_que_empezo_antes(self):
        n = nodo([("primera", 100.0), ("segunda", 200.0), ("tercera", 300.0)])
        self.assertEqual(rc.feature_activa_en(n, 250.0), ("segunda", False))

    def test_el_borde_exacto_cuenta_como_activa(self):
        n = nodo([("primera", 100.0), ("segunda", 200.0)])
        self.assertEqual(rc.feature_activa_en(n, 200.0), ("segunda", False))

    def test_si_nacio_antes_de_todas_devuelve_la_primera_como_aproximada(self):
        n = nodo([("primera", 100.0), ("segunda", 200.0)])
        self.assertEqual(rc.feature_activa_en(n, 50.0), ("primera", True))

    def test_sin_momento_devuelve_la_primera_como_aproximada(self):
        n = nodo([("primera", 100.0)])
        self.assertEqual(rc.feature_activa_en(n, None), ("primera", True))

    def test_features_sin_epoch_no_impiden_resolver(self):
        n = nodo([("con-marca", 100.0), ("sin-marca", None)])
        self.assertEqual(rc.feature_activa_en(n, 150.0), ("con-marca", False))

    def test_nodo_sin_features(self):
        self.assertEqual(rc.feature_activa_en(nodo(), 100.0), (None, False))


class TestResolverPorGrafo(unittest.TestCase):
    def test_hereda_la_feature_del_padre(self):
        indice = {
            "padre": nodo([("feature-a", 100.0)]),
            "hijo": nodo(padre="padre", inicio=150.0),
        }
        self.assertEqual(rc.resolver_por_grafo("hijo", indice), ("feature-a", False))

    def test_hereda_la_activa_al_nacer_y_no_la_primera(self):
        # El test que protege la decision central del diseno.
        indice = {
            "padre": nodo([("primera", 100.0), ("segunda", 200.0)]),
            "hijo": nodo(padre="padre", inicio=250.0),
        }
        self.assertEqual(rc.resolver_por_grafo("hijo", indice), ("segunda", False))

    def test_sube_dos_niveles(self):
        # depth > 1: un subagente que lanza otro subagente.
        indice = {
            "abuelo": nodo([("feature-a", 100.0)]),
            "padre": nodo(padre="abuelo", inicio=150.0),
            "nieto": nodo(padre="padre", inicio=200.0),
        }
        self.assertEqual(rc.resolver_por_grafo("nieto", indice), ("feature-a", False))

    def test_un_ciclo_no_cuelga(self):
        indice = {
            "a": nodo(padre="b", inicio=100.0),
            "b": nodo(padre="a", inicio=100.0),
        }
        self.assertEqual(rc.resolver_por_grafo("a", indice), (None, False))

    def test_padre_ausente_del_disco(self):
        indice = {"hijo": nodo(padre="no-esta", inicio=100.0)}
        self.assertEqual(rc.resolver_por_grafo("hijo", indice), (None, False))

    def test_sin_padre_no_resuelve(self):
        indice = {"solo": nodo([], padre=None)}
        self.assertEqual(rc.resolver_por_grafo("solo", indice), (None, False))

    def test_session_id_que_no_esta_en_el_indice(self):
        self.assertEqual(rc.resolver_por_grafo("fantasma", {}), (None, False))


CONFIG_MINIMA = {"precios_usd_por_millon": {"_default": {"input": 0, "cache": 0, "output": 0}},
                 "moneda_local": "ARS", "usd_a_moneda_local": 1500,
                 "umbral_inactividad_min": 30}


class TestPrecedenciaYCamposNuevos(unittest.TestCase):
    def _registros(self, carpeta, cwd):
        rollouts = sorted(carpeta.glob("rollout-*.jsonl"))
        indice = rc.construir_indice(rollouts)
        salida = []
        for r in rollouts:
            salida.extend(rc.construir_registros(r, Path(cwd), CONFIG_MINIMA, "dev", indice))
        return salida

    def test_el_orquestador_gana_y_se_declara(self):
        with directorio_temporal() as tmp:
            carpeta = Path(tmp)
            escribir_rollout(carpeta, "rollout-a.jsonl", tmp, [
                ev_usuario("$orquestador feature-a"), ev_tokens(100)])
            regs = self._registros(carpeta, tmp)
        uno = next(r for r in regs if r["feature"] == "feature-a")
        self.assertEqual(uno["origen_atribucion"], "orquestador")
        self.assertEqual(uno["etapa"], "orquestador")
        self.assertIsNone(uno["parent_session_id"])

    def test_el_grafo_atribuye_al_subagente(self):
        with directorio_temporal() as tmp:
            carpeta = Path(tmp)
            escribir_rollout(carpeta, "rollout-padre.jsonl", tmp, [
                ev_usuario("$orquestador feature-a"), ev_tokens(100)])
            rollout_con_spawn(carpeta, "rollout-hijo.jsonl", tmp, padre="padre",
                              eventos_extra=[ev_tokens(900, ts="2026-08-11T10:06:00Z")])
            regs = self._registros(carpeta, tmp)

        hijo = next(r for r in regs if r["session_id"] == "hijo")
        self.assertEqual(hijo["feature"], "feature-a")
        self.assertEqual(hijo["origen_atribucion"], "grafo")
        self.assertEqual(hijo["etapa"], "explorador")
        self.assertEqual(hijo["parent_session_id"], "padre")
        self.assertEqual(hijo["tokens"]["total"], 900)

    def test_el_respaldo_por_carpeta_sigue_funcionando(self):
        # Test de v1 que no debe romperse: sin grafo y sin marcador de texto,
        # la carpeta escrita sigue atribuyendo.
        with directorio_temporal() as tmp:
            carpeta = Path(tmp)
            patch_ev = {"timestamp": "2026-08-11T10:00:03Z", "type": "event_msg",
                        "payload": {"type": "patch_apply_end",
                                    "changes": {"tsoft-dev/feature-x/design.md": {}}}}
            escribir_rollout(carpeta, "rollout-a.jsonl", tmp, [
                ev_usuario("hola"), patch_ev, ev_tokens(100)])
            regs = self._registros(carpeta, tmp)
        uno = regs[0]
        self.assertEqual(uno["feature"], "feature-x")
        self.assertEqual(uno["origen_atribucion"], "carpeta")

    def test_sin_nada_queda_en_sin_feature(self):
        with directorio_temporal() as tmp:
            carpeta = Path(tmp)
            escribir_rollout(carpeta, "rollout-a.jsonl", tmp, [
                ev_usuario("una consulta suelta"), ev_tokens(100)])
            regs = self._registros(carpeta, tmp)
        self.assertEqual(regs[0]["feature"], "sin-feature")
        self.assertEqual(regs[0]["origen_atribucion"], "ninguno")

    def test_funciona_sin_indice(self):
        # indice es opcional: sin el, se comporta como v1.
        with directorio_temporal() as tmp:
            carpeta = Path(tmp)
            r = escribir_rollout(carpeta, "rollout-a.jsonl", tmp, [
                ev_usuario("$orquestador feature-a"), ev_tokens(100)])
            regs = rc.construir_registros(r, Path(tmp), CONFIG_MINIMA, "dev")
        self.assertEqual(regs[0]["feature"], "feature-a")

    def test_un_subagente_sin_rol_no_se_cuenta_como_orquestador(self):
        # Variante real {"subagent": {"other": "guardian"}}: es subagente pero
        # no declara rol. Si cayera en "orquestador" contaminaria la etapa que
        # mide el costo de las aprobaciones humanas.
        with directorio_temporal() as tmp:
            carpeta = Path(tmp)
            ruta = carpeta / "rollout-anon.jsonl"
            lineas = [
                {"timestamp": "2026-08-11T10:00:00Z", "type": "session_meta",
                 "payload": {"session_id": "anon", "cwd": tmp,
                             "timestamp": "2026-08-11T10:00:00Z",
                             "source": {"subagent": {"other": "guardian"}}}},
                ev_tokens(100),
            ]
            ruta.write_text("\n".join(json.dumps(l) for l in lineas), encoding="utf-8")
            regs = self._registros(carpeta, tmp)
        self.assertEqual(regs[0]["etapa"], "subagente-sin-rol")

    def test_la_conversacion_principal_es_la_etapa_orquestador(self):
        with directorio_temporal() as tmp:
            carpeta = Path(tmp)
            escribir_rollout(carpeta, "rollout-a.jsonl", tmp, [
                ev_usuario("$orquestador feature-a"), ev_tokens(100)])
            regs = self._registros(carpeta, tmp)
        self.assertEqual(regs[0]["etapa"], "orquestador")


if __name__ == "__main__":
    unittest.main()
