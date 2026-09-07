"""Tests de metrics_lib. Correr con: py tsoft-dev/scripts/tests/test_metrics_lib.py"""

import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers_temporal import directorio_temporal
import metrics_lib as ml


CONFIG = {
    "precios_usd_por_millon": {
        "gpt-5.4": {"input": 2.50, "cache": 0.25, "output": 15.00},
        "_default": {"input": 0, "cache": 0, "output": 0},
    },
    "moneda_local": "ARS",
    "usd_a_moneda_local": 1550,
}


class TestCosto(unittest.TestCase):
    def test_no_cobra_los_tokens_cacheados_dos_veces(self):
        # Datos reales de la ultima linea del ledger. cached_input_tokens es
        # subconjunto de input_tokens, no un valor adicional.
        uso = {"input": 12002015, "cache": 11244288, "output": 67245}
        resultado = ml.costo_usd(uso, "gpt-5.4", CONFIG)
        # (12002015-11244288)*2.50 + 11244288*0.25 + 67245*15, todo sobre 1M
        self.assertAlmostEqual(resultado["usd"], 5.714, places=3)

    def test_convierte_a_la_moneda_local_configurada(self):
        uso = {"input": 1_000_000, "cache": 0, "output": 0}
        resultado = ml.costo_usd(uso, "gpt-5.4", CONFIG)
        self.assertAlmostEqual(resultado["usd"], 2.50, places=6)
        self.assertEqual(resultado["local"], 3875)   # 2.50 * 1550
        self.assertEqual(resultado["moneda"], "ARS")

    def test_cada_equipo_puede_usar_su_moneda(self):
        # El kit se usa en varios paises: la moneda no esta cableada.
        config = dict(CONFIG, moneda_local="CLP", usd_a_moneda_local=950)
        resultado = ml.costo_usd({"input": 1_000_000}, "gpt-5.4", config)
        self.assertEqual(resultado["local"], 2375)   # 2.50 * 950
        self.assertEqual(resultado["moneda"], "CLP")

    def test_sin_tipo_de_cambio_no_inventa_una_conversion(self):
        config = {k: v for k, v in CONFIG.items() if k != "usd_a_moneda_local"}
        resultado = ml.costo_usd({"input": 1_000_000}, "gpt-5.4", config)
        self.assertEqual(resultado["local"], 0)

    def test_modelo_sin_precio_queda_marcado_como_no_tarifado(self):
        resultado = ml.costo_usd({"input": 100, "output": 50}, "codex-auto-review", CONFIG)
        self.assertFalse(resultado["tarifado"])
        self.assertEqual(resultado["usd"], 0)

    def test_modelo_con_precio_queda_marcado_como_tarifado(self):
        resultado = ml.costo_usd({"input": 100, "output": 50}, "gpt-5.4", CONFIG)
        self.assertTrue(resultado["tarifado"])

    def test_cache_mayor_que_input_no_produce_costo_negativo(self):
        # Defensa ante datos inconsistentes del transcript.
        uso = {"input": 100, "cache": 500, "output": 0}
        resultado = ml.costo_usd(uso, "gpt-5.4", CONFIG)
        self.assertGreaterEqual(resultado["usd"], 0)


class TestTiempo(unittest.TestCase):
    BASE = 1_700_000_000.0

    def test_suma_los_intervalos_cortos(self):
        # Tres eventos separados por 10 minutos: 20 minutos activos.
        ts = [self.BASE, self.BASE + 600, self.BASE + 1200]
        self.assertAlmostEqual(ml.tiempo_activo(ts, umbral_min=30), 20 / 60, places=4)

    def test_descarta_el_hueco_largo(self):
        # 10 min de trabajo, 6 horas de pausa, 10 min mas: siguen siendo 20 min.
        ts = [
            self.BASE,
            self.BASE + 600,
            self.BASE + 600 + 21600,
            self.BASE + 600 + 21600 + 600,
        ]
        self.assertAlmostEqual(ml.tiempo_activo(ts, umbral_min=30), 20 / 60, places=4)

    def test_tiempo_de_pared_incluye_el_hueco(self):
        ts = [self.BASE, self.BASE + 3600]
        self.assertAlmostEqual(ml.tiempo_pared(ts), 1.0, places=4)

    def test_menos_de_dos_eventos_da_cero(self):
        self.assertEqual(ml.tiempo_activo([]), 0.0)
        self.assertEqual(ml.tiempo_activo([self.BASE]), 0.0)
        self.assertEqual(ml.tiempo_pared([]), 0.0)

    def test_timestamps_desordenados_se_ordenan(self):
        ts = [self.BASE + 1200, self.BASE, self.BASE + 600]
        self.assertAlmostEqual(ml.tiempo_activo(ts, umbral_min=30), 20 / 60, places=4)

    def test_epoch_de_evento_parsea_iso_con_z(self):
        evento = {"timestamp": "2026-08-11T14:44:53.262Z"}
        self.assertIsInstance(ml.epoch_de_evento(evento), float)

    def test_epoch_de_evento_tolera_basura(self):
        self.assertIsNone(ml.epoch_de_evento({}))
        self.assertIsNone(ml.epoch_de_evento({"timestamp": "no-es-fecha"}))


class TestNombreFeature(unittest.TestCase):
    def test_saca_backticks(self):
        self.assertEqual(ml.limpiar_nombre_feature("`feature-color-botones`"), "feature-color-botones")

    def test_saca_corchetes_y_comillas(self):
        self.assertEqual(ml.limpiar_nombre_feature('"feature-a"'), "feature-a")
        self.assertEqual(ml.limpiar_nombre_feature("[feature-b]"), "feature-b")

    def test_rechaza_placeholders_de_la_plantilla(self):
        self.assertIsNone(ml.limpiar_nombre_feature("nombre-feature"))
        self.assertIsNone(ml.limpiar_nombre_feature("[nombre]"))

    def test_rechaza_el_placeholder_literal_de_despacho(self):
        # orquestador/SKILL.md:302 dice literalmente "...para la feature
        # [feature]." como ejemplo del propio despacho -- RE_DESPACHO_SUBAGENTE
        # lo capta cada vez que un subagente lee el skill, no solo cuando el
        # Orquestador despacha de verdad. Se descarta la forma con corchetes.
        self.assertIsNone(ml.limpiar_nombre_feature("[feature]"))
        self.assertIsNone(ml.limpiar_nombre_feature("[feature]."))
        # Caso real: Codex cita la instruccion entre backticks al explicarle
        # algo a un subagente o al IA Maker ("`$orquestador [feature]`"), y
        # RE_ORQUESTADOR captura "[feature]`" con el backtick de cierre pegado.
        self.assertIsNone(ml.limpiar_nombre_feature("[feature]`"))
        # Pero "feature" pelado (sin corchetes) sigue siendo un nombre valido:
        # alguien podria llamar asi a una feature real.
        self.assertEqual(ml.limpiar_nombre_feature("feature"), "feature")
        self.assertEqual(ml.limpiar_nombre_feature("[feature-b]"), "feature-b")

    def test_rechaza_basura(self):
        # Es lo que quedo guardado hoy en el ledger.
        self.assertIsNone(ml.limpiar_nombre_feature("...`"))
        self.assertIsNone(ml.limpiar_nombre_feature(""))
        self.assertIsNone(ml.limpiar_nombre_feature(None))

    def test_conserva_nombre_valido(self):
        self.assertEqual(ml.limpiar_nombre_feature("feature_cambios.v2"), "feature_cambios.v2")


def evento_usuario(mensaje):
    return {
        "timestamp": "2026-08-11T10:00:00Z",
        "type": "event_msg",
        "payload": {"type": "user_message", "message": mensaje},
    }


def evento_tokens(total, ts="2026-08-11T10:00:00Z", cache=0):
    """Genera un token_count con last_token_usage. input + output = total."""
    return {
        "timestamp": ts,
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "last_token_usage": {
                    "input_tokens": total,
                    "cached_input_tokens": cache,
                    "output_tokens": 0,
                    "reasoning_output_tokens": 0,
                    "total_tokens": total,
                }
            },
        },
    }


def evento_tokens_con_acumulado(total, acumulado, ts="2026-08-11T10:00:00Z"):
    """
    Genera un token_count con last_token_usage y total_token_usage (el
    acumulado del archivo). Sirve para simular el token_count duplicado que
    algunos rollouts repiten con el mismo acumulado.
    """
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
                },
                "total_token_usage": {
                    "input_tokens": acumulado,
                    "cached_input_tokens": 0,
                    "output_tokens": 0,
                    "reasoning_output_tokens": 0,
                    "total_tokens": acumulado,
                },
            },
        },
    }


def evento_turn_context(modelo, ts="2026-08-11T10:00:00Z"):
    """Evento turn_context real: el modelo vive en payload.model."""
    return {"timestamp": ts, "type": "turn_context", "payload": {"model": modelo}}


class TestFormatoRollout(unittest.TestCase):
    """
    Todo el conocimiento del formato de rollout de Codex (session_meta,
    turn_context) debe vivir aca, no en reconciliador.py. reconciliador
    solo debe consumir estas funciones y razonar sobre valores ya extraidos.
    """

    def test_lee_session_meta(self):
        eventos = [
            {"type": "session_meta", "payload": {"cwd": "c:\\proyecto", "model": "gpt-5.4"}},
            {"type": "event_msg", "payload": {"type": "user_message", "message": "hola"}},
        ]
        meta = ml.leer_session_meta(eventos)
        self.assertEqual(meta["model"], "gpt-5.4")

    def test_session_meta_ausente_devuelve_dict_vacio(self):
        self.assertEqual(ml.leer_session_meta([{"type": "event_msg"}]), {})

    def test_detecta_modelo_desde_turn_context(self):
        # session_meta real no trae "model": vive en el payload de turn_context.
        eventos = [
            {"type": "session_meta", "payload": {"cwd": "c:\\proyecto"}},
            evento_turn_context("gpt-5.4"),
        ]
        meta = ml.leer_session_meta(eventos)
        self.assertEqual(ml.detectar_modelo(eventos, meta), "gpt-5.4")

    def test_session_meta_model_gana_si_esta_presente(self):
        eventos = [
            {"type": "session_meta", "payload": {"cwd": "c:\\proyecto", "model": "gpt-6"}},
            evento_turn_context("gpt-5.4"),
        ]
        meta = ml.leer_session_meta(eventos)
        self.assertEqual(ml.detectar_modelo(eventos, meta), "gpt-6")

    def test_sin_modelo_en_ningun_lado_devuelve_vacio(self):
        eventos = [{"type": "session_meta", "payload": {"cwd": "c:\\proyecto"}}]
        meta = ml.leer_session_meta(eventos)
        self.assertEqual(ml.detectar_modelo(eventos, meta), "")

    def test_detecta_modelos_multiples_en_orden_de_aparicion(self):
        eventos = [
            evento_turn_context("gpt-5.4"),
            evento_turn_context("gpt-5.4"),  # repetido, no debe duplicar
            evento_turn_context("gpt-6"),
        ]
        self.assertEqual(ml.detectar_modelos(eventos), ["gpt-5.4", "gpt-6"])

    def test_detecta_un_unico_modelo(self):
        eventos = [evento_turn_context("gpt-5.4"), evento_turn_context("gpt-5.4")]
        self.assertEqual(ml.detectar_modelos(eventos), ["gpt-5.4"])

    def test_sin_turn_context_devuelve_lista_vacia(self):
        self.assertEqual(ml.detectar_modelos([{"type": "session_meta", "payload": {}}]), [])


class TestSegmentacion(unittest.TestCase):
    def test_atribuye_cada_tramo_a_su_feature(self):
        eventos = [
            evento_usuario("una consulta suelta"),
            evento_tokens(100),
            evento_usuario("$orquestador feature-a"),
            evento_tokens(200),
            evento_usuario("$orquestador feature-b"),
            evento_tokens(300),
        ]
        buckets = ml.segmentar_por_feature(eventos)
        self.assertEqual(buckets[ml.SIN_FEATURE]["tokens"]["total"], 100)
        self.assertEqual(buckets["feature-a"]["tokens"]["total"], 200)
        self.assertEqual(buckets["feature-b"]["tokens"]["total"], 300)

    def test_detecta_el_comando_expandido_a_link_markdown(self):
        # La extension de VS Code reescribe $orquestador como link al SKILL.md.
        mensaje = (
            "[$orquestador](C:\\Users\\x\\.codex\\skills\\orquestador\\SKILL.md) "
            "feature-color-botones"
        )
        buckets = ml.segmentar_por_feature([evento_usuario(mensaje), evento_tokens(500)])
        self.assertEqual(buckets["feature-color-botones"]["tokens"]["total"], 500)

    def test_ignora_el_comando_dentro_de_un_transcript_citado(self):
        # Los subagentes de revision citan la conversacion; no son invocaciones.
        mensaje = (
            "The following is the Codex agent history whose request action you "
            "are assessing:\n>>> TRANSCRIPT START\n[1] user: $orquestador feature-fantasma"
        )
        buckets = ml.segmentar_por_feature([evento_usuario(mensaje), evento_tokens(700)])
        self.assertNotIn("feature-fantasma", buckets)
        self.assertEqual(buckets[ml.SIN_FEATURE]["tokens"]["total"], 700)

    def test_ignora_el_bootstrap_sintetico_del_arranque_de_sesion(self):
        # El primer "mensaje de usuario" de TODA conversacion de Codex
        # (orquestador o subagente) es en realidad el bootstrap sintetico que
        # Codex inyecta antes del primer prompt real (AGENTS.md,
        # environment_context, etc.), no un turno real. Contarlo dejaba una
        # fila fantasma de sin-feature con 0 tokens por cada subagente.
        bootstrap = (
            "# AGENTS.md instructions for /repo\n<INSTRUCTIONS>...</INSTRUCTIONS>\n"
            "<environment_context><cwd>/repo</cwd></environment_context>"
        )
        eventos = [
            evento_usuario(bootstrap),
            evento_usuario("Spawnea el subagente explorador para la feature real-feature."),
            evento_tokens(500),
        ]
        buckets = ml.segmentar_por_feature(eventos)
        self.assertNotIn(ml.SIN_FEATURE, buckets)
        self.assertEqual(buckets["real-feature"]["turnos"], 1)
        self.assertEqual(buckets["real-feature"]["tokens"]["total"], 500)

    def test_la_suma_de_los_buckets_iguala_el_total(self):
        eventos = [
            evento_usuario("$orquestador feature-a"),
            evento_tokens(120),
            evento_tokens(80),
            evento_usuario("$orquestador feature-b"),
            evento_tokens(50),
        ]
        buckets = ml.segmentar_por_feature(eventos)
        suma = sum(bucket["tokens"]["total"] for bucket in buckets.values())
        self.assertEqual(suma, 250)

    def test_cuenta_los_turnos_por_feature(self):
        eventos = [
            evento_usuario("$orquestador feature-a"),
            evento_tokens(10),
            evento_usuario("segui"),
            evento_tokens(10),
        ]
        buckets = ml.segmentar_por_feature(eventos)
        self.assertEqual(buckets["feature-a"]["turnos"], 2)

    def test_registra_timestamps_para_el_calculo_de_tiempo(self):
        eventos = [
            evento_usuario("$orquestador feature-a"),
            evento_tokens(10, ts="2026-08-11T10:00:00Z"),
            evento_tokens(10, ts="2026-08-11T10:10:00Z"),
        ]
        buckets = ml.segmentar_por_feature(eventos)
        marcas = buckets["feature-a"]["timestamps"]
        self.assertEqual(len(marcas), 2)
        self.assertAlmostEqual(ml.tiempo_activo(marcas, umbral_min=30), 10 / 60, places=4)

    def test_nombre_invalido_no_abre_feature(self):
        buckets = ml.segmentar_por_feature(
            [evento_usuario("$orquestador [nombre-feature]"), evento_tokens(40)]
        )
        self.assertEqual(buckets[ml.SIN_FEATURE]["tokens"]["total"], 40)

    def test_rollout_vacio_no_rompe(self):
        self.assertEqual(ml.segmentar_por_feature([]), {})

    def test_saltea_token_count_duplicado_con_acumulado_sin_cambios(self):
        # Codex a veces repite un token_count con el mismo total_token_usage
        # acumulado (visto en rollout-2026-08-03T15-49-21-019fc8f5). Sumar el
        # last_token_usage de ese duplicado contaria ese turno dos veces.
        eventos = [
            evento_usuario("$orquestador feature-a"),
            evento_tokens_con_acumulado(100, acumulado=100),
            evento_tokens_con_acumulado(100, acumulado=100),  # duplicado
            evento_tokens_con_acumulado(50, acumulado=150),
        ]
        buckets = ml.segmentar_por_feature(eventos)
        self.assertEqual(buckets["feature-a"]["tokens"]["total"], 150)

    def test_total_token_usage_corrupto_no_rompe_y_cuenta_el_turno(self):
        # Un JSONL malformado o un cambio de formato de Codex podria dejar
        # total_token_usage con un valor que no sea dict. No debe romper el
        # recorrido, y el last_token_usage del evento se sigue contando.
        evento_corrupto = {
            "timestamp": "2026-08-11T10:00:00Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {
                        "input_tokens": 60,
                        "cached_input_tokens": 0,
                        "output_tokens": 0,
                        "reasoning_output_tokens": 0,
                        "total_tokens": 60,
                    },
                    "total_token_usage": "corrupto",
                },
            },
        }
        buckets = ml.segmentar_por_feature([evento_usuario("$orquestador feature-a"), evento_corrupto])
        self.assertEqual(buckets["feature-a"]["tokens"]["total"], 60)

    def test_marca_que_el_marcador_fue_el_orquestador(self):
        eventos = [evento_usuario("$orquestador feature-a"), evento_tokens(100)]
        buckets = ml.segmentar_por_feature(eventos)
        self.assertEqual(buckets["feature-a"]["origen"], "orquestador")

    def test_marca_que_el_marcador_fue_un_despacho(self):
        # Distinguirlos importa: uno es invocacion humana explicita y el otro
        # es texto que escribio el Orquestador.
        mensaje = "Spawnea el subagente explorador para la feature cambiocolor."
        buckets = ml.segmentar_por_feature([evento_usuario(mensaje), evento_tokens(100)])
        self.assertEqual(buckets["cambiocolor"]["origen"], "despacho")

    def test_sin_feature_no_tiene_origen(self):
        buckets = ml.segmentar_por_feature([evento_usuario("una consulta"), evento_tokens(50)])
        self.assertIsNone(buckets[ml.SIN_FEATURE]["origen"])


class TestDespachoDeSubagente(unittest.TestCase):
    """
    Los subagentes corren en conversaciones propias que arrancan con el
    despacho del Orquestador, no con $orquestador. Sin detectarlas, su
    consumo -que suele superar al del propio Orquestador- cae en sin-feature.
    """

    def test_detecta_el_despacho_con_spawnea(self):
        mensaje = "Spawnea el subagente explorador para la feature cambiocolor."
        buckets = ml.segmentar_por_feature([evento_usuario(mensaje), evento_tokens(900)])
        self.assertEqual(buckets["cambiocolor"]["tokens"]["total"], 900)

    def test_detecta_el_despacho_con_actua_como(self):
        mensaje = (
            "Actua como el subagente explorador del TSOFT AI Dev Kit "
            "para la feature `feature-cambios`."
        )
        buckets = ml.segmentar_por_feature([evento_usuario(mensaje), evento_tokens(400)])
        self.assertEqual(buckets["feature-cambios"]["tokens"]["total"], 400)

    def test_atribuye_toda_la_conversacion_del_subagente(self):
        # La conversacion entera es trabajo de esa feature, no solo el 1er turno.
        eventos = [
            evento_usuario("Spawnea el subagente explorador para la feature cambiocolor."),
            evento_tokens(500),
            evento_usuario("continuemos"),
            evento_tokens(700),
        ]
        buckets = ml.segmentar_por_feature(eventos)
        self.assertEqual(buckets["cambiocolor"]["tokens"]["total"], 1200)
        self.assertNotIn(ml.SIN_FEATURE, buckets)

    def test_sin_mencion_de_feature_no_atribuye(self):
        # Este despacho real no nombra la feature: no hay nada que atribuir.
        mensaje = "Actua como el subagente local 'explorador' del TSOFT AI Dev Kit."
        buckets = ml.segmentar_por_feature([evento_usuario(mensaje), evento_tokens(300)])
        self.assertEqual(buckets[ml.SIN_FEATURE]["tokens"]["total"], 300)

    def test_ignora_el_despacho_dentro_de_un_transcript_citado(self):
        mensaje = (
            "whose request action you are assessing:\n>>> TRANSCRIPT START\n"
            "[1] user: Spawnea el subagente explorador para la feature fantasma."
        )
        buckets = ml.segmentar_por_feature([evento_usuario(mensaje), evento_tokens(600)])
        self.assertNotIn("fantasma", buckets)

    def test_la_palabra_feature_suelta_no_dispara(self):
        # Hablar de una feature no es despachar un subagente.
        mensaje = "Revisemos para la feature cambiocolor si el color quedo bien."
        buckets = ml.segmentar_por_feature([evento_usuario(mensaje), evento_tokens(250)])
        self.assertEqual(buckets[ml.SIN_FEATURE]["tokens"]["total"], 250)


def evento_agente(mensaje):
    return {"type": "event_msg", "payload": {"type": "agent_message", "message": mensaje}}


def evento_patch(*archivos):
    return {
        "type": "event_msg",
        "payload": {
            "type": "patch_apply_end",
            "changes": {archivo: {} for archivo in archivos},
        },
    }


def evento_shell(comando):
    return {
        "type": "response_item",
        "payload": {
            "type": "function_call",
            "name": "shell_command",
            "arguments": json.dumps({"command": comando}),
        },
    }


def subagentes_de(mensaje):
    evidencia = ml._evidencia_vacia()
    ml.acumular_evidencia(evento_agente(mensaje), evidencia)
    return evidencia["subagentes"]


class TestSubagentesEjecutados(unittest.TestCase):
    """
    La lista de subagentes debe reflejar los que CORRIERON. El Orquestador
    cierra casi todos sus mensajes ofreciendo el paso siguiente, y esa mencion
    futura llegaba al registro como si el subagente ya hubiera trabajado.
    """

    def test_no_cuenta_el_subagente_ofrecido_como_proximo_paso(self):
        # Mensaje real: el flujo solo habia corrido el Explorador.
        mensaje = (
            "Explorador completado y aprobado. Despues te ofrezco continuar con "
            "el subagente planificador o pausar, como pide el flujo del kit."
        )
        self.assertEqual(subagentes_de(mensaje), ["explorador"])

    def test_una_mencion_suelta_no_es_evidencia_de_ejecucion(self):
        mensaje = "El Planificador va a definir el plan de implementacion."
        self.assertEqual(subagentes_de(mensaje), [])

    def test_sigue_contando_el_despacho_explicito(self):
        mensaje = "Spawnea el subagente planificador para la feature cambiocolor."
        self.assertEqual(subagentes_de(mensaje), ["planificador"])

    def test_sigue_contando_el_resumen_de_un_output(self):
        mensaje = "Resumen del output del Explorador: la feature toca global.css."
        self.assertEqual(subagentes_de(mensaje), ["explorador"])

    def test_el_veto_no_cruza_el_cierre_de_oracion(self):
        # "continuar" pertenece a la frase anterior: no vetea este despacho.
        mensaje = "Listo para continuar. Spawnea el subagente desarrollador."
        self.assertEqual(subagentes_de(mensaje), ["desarrollador"])

    def test_no_cuenta_el_menu_de_retomar_como_ejecucion(self):
        # "Retomar desde X" (SKILL.md:101) es la opcion 1 de un menu que le
        # ofrece al usuario resumir un flujo -- nunca confirma que X ya
        # corrio. Si se cuenta esta frase, cada resume de feature le
        # atribuye al agente del "proximo paso pendiente" una ejecucion que
        # puede no haber pasado (el usuario puede elegir otra opcion del
        # menu). No hay ningun lugar del skill donde "retomar desde"
        # describa una ejecucion ya sucedida -- por eso el patron no
        # deberia existir en PATRONES_SUBAGENTE, y esta frase real del
        # menu no tiene que contar como evidencia.
        mensaje = (
            "Proximo paso pendiente: Planificador\n\n"
            "Que queres hacer?\n"
            "1. Retomar desde el Planificador\n"
            "2. Arrancar desde otro paso\n"
            "3. Ver el detalle del estado guardado"
        )
        self.assertEqual(subagentes_de(mensaje), [])


class TestEvidenciaPorFeature(unittest.TestCase):
    """
    Dos features de una misma conversacion no comparten evidencia: cada una
    declara los archivos y comandos que se produjeron mientras estaba activa.
    """

    def test_cada_feature_declara_solo_sus_archivos(self):
        eventos = [
            evento_usuario("$orquestador feature-a"),
            evento_tokens(100),
            evento_patch("tsoft-dev/feature-a/design.md"),
            evento_usuario("$orquestador feature-b"),
            evento_tokens(200),
            evento_patch("tsoft-dev/feature-b/design.md"),
        ]
        buckets = ml.segmentar_por_feature(eventos)
        self.assertEqual(
            buckets["feature-a"]["evidencia"]["archivos_tocados"],
            ["tsoft-dev/feature-a/design.md"],
        )
        self.assertEqual(
            buckets["feature-b"]["evidencia"]["archivos_tocados"],
            ["tsoft-dev/feature-b/design.md"],
        )

    def test_cada_feature_declara_solo_sus_comandos(self):
        eventos = [
            evento_usuario("$orquestador feature-a"),
            evento_shell("rg --files src"),
            evento_tokens(100),
            evento_usuario("$orquestador feature-b"),
            evento_shell("npm test"),
            evento_tokens(200),
        ]
        buckets = ml.segmentar_por_feature(eventos)
        self.assertEqual(buckets["feature-a"]["evidencia"]["comandos"], ["rg --files src"])
        self.assertEqual(buckets["feature-b"]["evidencia"]["comandos"], ["npm test"])

    def test_las_ediciones_se_cuentan_por_feature(self):
        eventos = [
            evento_usuario("$orquestador feature-a"),
            evento_tokens(100),
            evento_patch("a.md", "b.md"),
            evento_usuario("$orquestador feature-b"),
            evento_tokens(200),
            evento_patch("c.md"),
        ]
        buckets = ml.segmentar_por_feature(eventos)
        self.assertEqual(buckets["feature-a"]["evidencia"]["ediciones"], 2)
        self.assertEqual(buckets["feature-b"]["evidencia"]["ediciones"], 1)

    def test_evidencia_sin_consumo_no_crea_una_feature(self):
        # Sin turnos ni tokens no hay nada que reportar.
        self.assertEqual(ml.segmentar_por_feature([evento_shell("ls")]), {})

    def test_el_camino_de_hooks_sigue_viendo_la_conversacion_entera(self):
        eventos = [
            evento_usuario("$orquestador feature-a"),
            evento_patch("a.md"),
            evento_usuario("$orquestador feature-b"),
            evento_patch("b.md"),
        ]
        with directorio_temporal() as tmp:
            ruta = Path(tmp) / "rollout.jsonl"
            ruta.write_text(
                "\n".join(json.dumps(evento) for evento in eventos), encoding="utf-8"
            )
            evidencia = ml.extraer_evidencia_transcript(str(ruta))
        self.assertEqual(evidencia["archivos_tocados"], ["a.md", "b.md"])
        self.assertEqual(evidencia["ediciones"], 2)


def evento_cuota(pct, ts="2026-08-11T10:00:00Z", plan="team"):
    """token_count con la lectura de cuota semanal que reporta Codex."""
    return {
        "timestamp": ts,
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "last_token_usage": {
                    "input_tokens": 10, "cached_input_tokens": 0,
                    "output_tokens": 0, "reasoning_output_tokens": 0,
                    "total_tokens": 10,
                }
            },
            "rate_limits": {
                "limit_id": "codex",
                "plan_type": plan,
                "primary": {"used_percent": pct, "window_minutes": 10080},
            },
        },
    }


class TestCuotaSemanal(unittest.TestCase):
    """
    En plan Team no se paga por token: el limite real es una cuota semanal.
    Codex la reporta en cada token_count y llegar al 100% bloquea el trabajo.
    """

    def test_extrae_inicial_final_y_pico(self):
        eventos = [evento_cuota(8.0), evento_cuota(15.0), evento_cuota(12.0)]
        c = ml.extraer_cuota(eventos)
        self.assertEqual(c["inicial"], 8.0)
        self.assertEqual(c["final"], 12.0)
        self.assertEqual(c["pico"], 15.0)

    def test_el_consumo_es_la_diferencia_contra_el_inicio(self):
        c = ml.extraer_cuota([evento_cuota(10.0), evento_cuota(18.0)])
        self.assertAlmostEqual(c["consumida"], 8.0)

    def test_si_la_ventana_se_reinicia_no_da_negativo(self):
        # La ventana es movil: puede bajar sola sin que nadie consumiera menos.
        c = ml.extraer_cuota([evento_cuota(90.0), evento_cuota(5.0)])
        self.assertEqual(c["consumida"], 0.0)

    def test_registra_el_plan(self):
        c = ml.extraer_cuota([evento_cuota(8.0, plan="team")])
        self.assertEqual(c["plan"], "team")

    def test_sin_lecturas_devuelve_none(self):
        self.assertIsNone(ml.extraer_cuota([]))
        self.assertIsNone(ml.extraer_cuota([evento_tokens(100)]))

    def test_tolera_rate_limits_malformado(self):
        evento = evento_cuota(8.0)
        evento["payload"]["rate_limits"] = "corrupto"
        self.assertIsNone(ml.extraer_cuota([evento]))


class TestNormalizacionDeRuta(unittest.TestCase):
    """
    La convencion es docs/<feature>/ con el mismo nombre en los tres lugares,
    pero un dev puede tipear la ruta igual. La normalizacion evita que eso
    parta una misma feature en varias filas del reporte.
    """

    def test_saca_el_prefijo_docs_y_la_barra_final(self):
        self.assertEqual(ml.limpiar_nombre_feature("docs/cambio-de-color/"), "cambio-de-color")

    def test_toma_la_carpeta_cuando_le_pasan_el_archivo(self):
        # La feature es la carpeta, no el archivo que haya adentro.
        self.assertEqual(
            ml.limpiar_nombre_feature("docs/cambio-de-color/cambiodecolor.md"),
            "cambio-de-color",
        )

    def test_saca_la_extension_de_documento(self):
        self.assertEqual(ml.limpiar_nombre_feature("feature-cambios.md"), "feature-cambios")

    def test_fusiona_las_dos_formas_de_la_misma_feature(self):
        # En los datos reales feature-cambios y feature-cambios.md son la misma.
        self.assertEqual(
            ml.limpiar_nombre_feature("feature-cambios.md"),
            ml.limpiar_nombre_feature("feature-cambios"),
        )

    def test_acepta_barras_invertidas_de_windows(self):
        self.assertEqual(ml.limpiar_nombre_feature("docs\\cambio-de-color\\"), "cambio-de-color")

    def test_no_rompe_un_nombre_con_punto_que_no_es_extension(self):
        # Solo se sacan extensiones de documento conocidas: v2.0 debe sobrevivir.
        self.assertEqual(ml.limpiar_nombre_feature("feature-v2.0"), "feature-v2.0")

    def test_no_confunde_docs_con_el_comienzo_de_un_nombre(self):
        # "docsify" empieza con "docs" pero no es el prefijo de carpeta.
        self.assertEqual(ml.limpiar_nombre_feature("docsify-upgrade"), "docsify-upgrade")

    def test_una_ruta_que_queda_vacia_devuelve_none(self):
        self.assertIsNone(ml.limpiar_nombre_feature("docs/"))
        self.assertIsNone(ml.limpiar_nombre_feature("/"))

    def test_saca_el_punto_final_de_la_oracion(self):
        # El Orquestador despacha con "...para la feature cambiocolor." y ese
        # punto es puntuacion, no parte del nombre.
        self.assertEqual(ml.limpiar_nombre_feature("cambiocolor."), "cambiocolor")
        self.assertEqual(ml.limpiar_nombre_feature("`feature-cambios`."), "feature-cambios")

    def test_el_punto_final_no_se_come_una_version(self):
        self.assertEqual(ml.limpiar_nombre_feature("feature-v2.0"), "feature-v2.0")

    def test_feature_pelado_no_es_placeholder(self):
        # docs/feature.md es un doc real: al sacarle la extension queda
        # "feature", y descartarlo tiraba su atribucion a sin-feature.
        # La plantilla del Orquestador emite "nombre-feature", no "feature".
        self.assertEqual(ml.limpiar_nombre_feature("feature.md"), "feature")
        self.assertEqual(ml.limpiar_nombre_feature("feature"), "feature")



def meta_subagente(rol="explorador", padre="01a00bc0", apodo="Mapper", depth=1):
    """session_meta de una conversacion de subagente, como la escribe Codex."""
    return {
        "session_id": "01a00c11",
        "cwd": "c:\\proyecto",
        "source": {
            "subagent": {
                "thread_spawn": {
                    "parent_thread_id": padre,
                    "depth": depth,
                    "agent_path": None,
                    "agent_nickname": apodo,
                    "agent_role": rol,
                }
            }
        },
    }


class TestSpawnSubagente(unittest.TestCase):
    """
    Codex declara en session_meta.source.subagent.thread_spawn quien lanzo la
    conversacion y con que rol. Es el dato que reemplaza la inferencia por
    texto.
    """

    def test_lee_el_padre_y_el_rol(self):
        spawn = ml.leer_spawn_subagente(meta_subagente())
        self.assertEqual(spawn["padre"], "01a00bc0")
        self.assertEqual(spawn["rol"], "explorador")
        self.assertEqual(spawn["apodo"], "Mapper")
        self.assertEqual(spawn["depth"], 1)

    def test_source_como_string_no_rompe(self):
        # La mayoria de los rollouts trae source como "vscode" o "cli".
        spawn = ml.leer_spawn_subagente({"session_id": "x", "source": "vscode"})
        self.assertEqual(spawn, {"padre": None, "rol": None, "apodo": None, "depth": None, "es_subagente": False})

    def test_sin_source_no_rompe(self):
        spawn = ml.leer_spawn_subagente({"session_id": "x"})
        self.assertIsNone(spawn["padre"])

    def test_variante_sin_thread_spawn(self):
        # Variante real observada: {"subagent": {"other": "guardian"}}
        meta = {"session_id": "x", "source": {"subagent": {"other": "guardian"}}}
        spawn = ml.leer_spawn_subagente(meta)
        self.assertIsNone(spawn["padre"])
        self.assertIsNone(spawn["rol"])

    def test_meta_que_no_es_dict_no_rompe(self):
        self.assertIsNone(ml.leer_spawn_subagente(None)["padre"])

    def test_depth_no_entero_se_descarta(self):
        spawn = ml.leer_spawn_subagente(meta_subagente(depth="dos"))
        self.assertIsNone(spawn["depth"])

    def test_marca_es_subagente_aunque_no_haya_thread_spawn(self):
        # Variante real: es subagente, pero no declara rol ni padre. Hay que
        # poder distinguirla de una conversacion principal.
        meta = {"session_id": "x", "source": {"subagent": {"other": "guardian"}}}
        spawn = ml.leer_spawn_subagente(meta)
        self.assertTrue(spawn["es_subagente"])
        self.assertIsNone(spawn["rol"])

    def test_una_conversacion_principal_no_es_subagente(self):
        self.assertFalse(ml.leer_spawn_subagente({"source": "vscode"})["es_subagente"])
        self.assertFalse(ml.leer_spawn_subagente({})["es_subagente"])


class TestNormalizarRol(unittest.TestCase):
    def test_mapea_el_alias_en_ingles(self):
        # El kit se instalo en proyectos con los agentes nombrados en ingles.
        self.assertEqual(ml.normalizar_rol("explorer"), "explorador")

    def test_no_mapea_los_genericos(self):
        # Asumir que "worker" es el Desarrollador seria inventar un dato.
        self.assertEqual(ml.normalizar_rol("worker"), "worker")
        self.assertEqual(ml.normalizar_rol("default"), "default")
        self.assertEqual(ml.normalizar_rol("guardian"), "guardian")

    def test_un_rol_desconocido_pasa_tal_cual(self):
        self.assertEqual(ml.normalizar_rol("revisor-de-seguridad"), "revisor-de-seguridad")

    def test_normaliza_espacios_y_mayusculas(self):
        self.assertEqual(ml.normalizar_rol("  Planificador  "), "planificador")

    def test_vacio_o_none_devuelve_none(self):
        self.assertIsNone(ml.normalizar_rol(None))
        self.assertIsNone(ml.normalizar_rol("   "))
        self.assertIsNone(ml.normalizar_rol(123))


class TestEpochIso(unittest.TestCase):
    def test_convierte_iso_con_z(self):
        self.assertEqual(ml.epoch_iso("2026-08-17T13:15:40Z"), 1786972540.0)

    def test_acepta_milisegundos(self):
        # session_meta.timestamp los trae: 2026-08-20T12:09:08.510Z
        self.assertAlmostEqual(ml.epoch_iso("2026-08-20T12:09:08.510Z"), 1787227748.51, places=2)

    def test_basura_devuelve_none(self):
        self.assertIsNone(ml.epoch_iso("ayer"))
        self.assertIsNone(ml.epoch_iso(None))
        self.assertIsNone(ml.epoch_iso(""))


class TestRedactarSecretos(unittest.TestCase):
    def test_enmascara_bearer_token(self):
        cmd = 'curl -H "Authorization: Bearer sk-proj-abc123XYZ" https://api.example.com/v1/x'
        resultado = ml.redactar_secretos(cmd)
        self.assertNotIn("sk-proj-abc123XYZ", resultado)
        self.assertIn("[REDACTADO]", resultado)

    def test_enmascara_credenciales_en_url(self):
        cmd = "curl https://miguel:hunter2@example.com/api"
        resultado = ml.redactar_secretos(cmd)
        self.assertNotIn("hunter2", resultado)
        self.assertIn("miguel:[REDACTADO]@", resultado)

    def test_enmascara_variable_de_entorno_con_clave(self):
        cmd = "API_KEY=abcdef123456 py -3 script.py"
        resultado = ml.redactar_secretos(cmd)
        self.assertNotIn("abcdef123456", resultado)
        self.assertIn("[REDACTADO]", resultado)

    def test_no_toca_comandos_sin_secretos(self):
        cmd = "git status --short"
        self.assertEqual(ml.redactar_secretos(cmd), cmd)

    def test_enmascara_variable_de_entorno_con_prefijo(self):
        # El prefijo (OPENAI_, GITHUB_) tiene "_" antes de la palabra clave:
        # un limite de palabra estricto ahi no encuentra separacion y deja
        # pasar el secreto entero. Es el caso mas comun en una shell real.
        cmd = "export OPENAI_API_KEY=sk-proj-REALSECRET123"
        resultado = ml.redactar_secretos(cmd)
        self.assertNotIn("sk-proj-REALSECRET123", resultado)
        self.assertIn("[REDACTADO]", resultado)

    def test_enmascara_token_con_sufijo(self):
        cmd = "export GITHUB_TOKEN=ghp_REALSECRET123"
        resultado = ml.redactar_secretos(cmd)
        self.assertNotIn("ghp_REALSECRET123", resultado)
        self.assertIn("[REDACTADO]", resultado)

    def test_enmascara_clave_en_medio_del_identificador(self):
        cmd = "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMISECRETO"
        resultado = ml.redactar_secretos(cmd)
        self.assertNotIn("wJalrXUtnFEMISECRETO", resultado)
        self.assertIn("[REDACTADO]", resultado)

    def test_enmascara_authorization_basic(self):
        cmd = 'curl -H "Authorization: Basic dXNlcjpwYXNzd29yZA=="'
        resultado = ml.redactar_secretos(cmd)
        self.assertNotIn("dXNlcjpwYXNzd29yZA==", resultado)
        self.assertIn("[REDACTADO]", resultado)

    def test_no_falla_con_valores_no_string(self):
        self.assertIsNone(ml.redactar_secretos(None))
        self.assertEqual(ml.redactar_secretos(123), 123)


class TestTipoReconocido(unittest.TestCase):
    """
    Un tipo de tarea no reconocido (typo en la etiqueta #tarea:) no esta en
    tipos_validos. No cambia ningun calculo (tipo/complejidad son metadato
    descriptivo, no hay formula de horas en el kit), pero vale avisarlo: es
    la unica señal de que alguien escribio mal la etiqueta del prompt.
    """

    BASELINES = {
        "tipos_validos": ["evolutivo-fullstack", "documentacion"],
    }

    def _estado(self, tipo, complejidad):
        return {"tarea_declarada": tipo, "complejidad_declarada": complejidad}

    def test_tipo_no_listado_no_se_reconoce(self):
        estado = self._estado("evolutivo-typo", "baja")
        resultado = ml.clasificacion_normalizada(estado, self.BASELINES)
        self.assertFalse(resultado["tipo_reconocido"])

    def test_tipo_listado_se_reconoce(self):
        estado = self._estado("evolutivo-fullstack", "baja")
        resultado = ml.clasificacion_normalizada(estado, self.BASELINES)
        self.assertTrue(resultado["tipo_reconocido"])

    def test_sin_tipos_validos_configurados_no_rechaza_nada(self):
        # baselines.json sin la clave tipos_validos (o vacia) no puede
        # convertir cualquier tipo declarado en "no reconocido".
        estado = self._estado("lo-que-sea", "baja")
        resultado = ml.clasificacion_normalizada(estado, {})
        self.assertTrue(resultado["tipo_reconocido"])


class TestDuracionSesion(unittest.TestCase):
    """
    inicio_epoch falta si el estado de la sesion se corrompio o se perdio
    entre SessionStart y Stop. Sin guarda, dur_h se dispara a cientos de
    miles de horas (epoch 0 hasta ahora) sin que nadie lo note.
    """

    def test_sin_inicio_epoch_no_dispara_horas_gigantes(self):
        estado = {"fin_epoch": time.time()}
        resultado = ml.duracion_sesion(estado)
        self.assertFalse(resultado["duracion_confiable"])
        self.assertEqual(resultado["duracion_h"], 0.0)

    def test_con_inicio_epoch_normal_queda_confiable(self):
        ahora = time.time()
        estado = {"inicio_epoch": ahora - 3600, "fin_epoch": ahora}
        resultado = ml.duracion_sesion(estado)
        self.assertTrue(resultado["duracion_confiable"])
        self.assertAlmostEqual(resultado["duracion_h"], 1.0, places=2)

    def test_inicio_epoch_en_cero_se_trata_como_presente(self):
        # epoch 0 es un timestamp valido (1970-01-01), no "ausente". Si la
        # guarda usara un chequeo de falsy en vez de "is not None", este
        # caso se confundiria con inicio_epoch faltante.
        estado = {"inicio_epoch": 0, "fin_epoch": 3600}
        resultado = ml.duracion_sesion(estado)
        self.assertTrue(resultado["duracion_confiable"])
        self.assertAlmostEqual(resultado["duracion_h"], 1.0, places=2)


if __name__ == "__main__":
    unittest.main()
