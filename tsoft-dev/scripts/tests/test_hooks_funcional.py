"""
Tests funcionales de los 7 hooks: corren el script real (subprocess, con
tsoft-dev/scripts intacto) contra un proyecto de kit temporal y verifican
que dejan el estado/ledger/reportes correctos.

Esto es distinto de test_hooks_import_resilience.py: aquel prueba que un
hook no muere si metrics_lib no esta disponible (resiliencia). Este prueba
que, cuando SI esta disponible, el hook mide y escribe lo que dice que mide
-- el camino que hasta ahora solo se habia validado a mano.

Correr con: py -3 tsoft-dev/scripts/tests/test_hooks_funcional.py
"""

import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers_temporal import directorio_temporal

RAIZ_KIT_REAL = Path(__file__).resolve().parents[3]
DIR_HOOKS = RAIZ_KIT_REAL / ".codex" / "hooks"

CELULA = {
    "precios_usd_por_millon": {
        "gpt-5.4": {"input": 2.50, "cache": 0.25, "output": 15.00},
        "_default": {"input": 0, "cache": 0, "output": 0},
    },
    "moneda_local": "ARS",
    "usd_a_moneda_local": 1550,
}

BASELINES = {
    "tipo_default": "evolutivo-frontend",
    "tipos_validos": ["evolutivo-frontend", "evolutivo-backend", "documentacion"],
    "umbrales_complejidad": {"media": 4, "alta": 12},
}


def _preparar_proyecto(tmp: Path) -> Path:
    """Arma un proyecto minimo donde raiz_kit() encuentra el marcador real
    (tsoft-dev/config/celula.json) en vez de caer al fallback del kit."""
    (tmp / "tsoft-dev" / "config").mkdir(parents=True)
    (tmp / "tsoft-dev" / "config" / "celula.json").write_text(
        json.dumps(CELULA), encoding="utf-8"
    )
    (tmp / "tsoft-dev" / "config" / "baselines.json").write_text(
        json.dumps(BASELINES), encoding="utf-8"
    )
    return tmp


def _correr_hook(nombre_hook: str, payload: dict, timeout: int = 15):
    """Corre el hook real via subprocess, con stdin/stdout forzados a UTF-8
    (en Windows, sin esto el pipe puede decodificar mal cualquier caracter
    fuera de ASCII y el hook recibe datos corruptos sin avisar)."""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, str(DIR_HOOKS / nombre_hook)],
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        capture_output=True,
        timeout=timeout,
        env=env,
    )


def _stdout_json(resultado) -> dict:
    salida = resultado.stdout.decode("utf-8", "replace").strip()
    return json.loads(salida) if salida else {}


def _leer_estado(raiz: Path, session_id: str) -> dict:
    ruta = raiz / "tsoft-dev" / "metrics" / "sesiones" / f"{session_id}.json"
    if not ruta.exists():
        return {}
    return json.loads(ruta.read_text(encoding="utf-8"))


def _leer_ledger(raiz: Path) -> list:
    ruta = raiz / "tsoft-dev" / "metrics" / "ledger.jsonl"
    if not ruta.exists():
        return []
    return [
        json.loads(linea)
        for linea in ruta.read_text(encoding="utf-8").splitlines()
        if linea.strip()
    ]


def _crear_transcript_minimo(tmp: Path, nombre: str, input_tokens=1000, output_tokens=200) -> Path:
    """Transcript JSONL minimo con un evento token_count real, el unico
    formato que _extraer_tokens_jsonl() sabe leer -- no es un rollout
    completo de Codex, solo lo necesario para que la extraccion de tokens
    tenga algo real que parsear (en vez de caer en "estimacion")."""
    ruta = tmp / nombre
    evento = {
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "total_token_usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cached_input_tokens": 0,
                    "reasoning_output_tokens": 0,
                }
            },
        },
    }
    ruta.write_text(json.dumps(evento) + "\n", encoding="utf-8")
    return ruta


class TestSessionStart(unittest.TestCase):
    def test_crea_estado_inicial_con_los_defaults_correctos(self):
        with directorio_temporal() as tmp:
            raiz = _preparar_proyecto(Path(tmp))
            resultado = _correr_hook("session_start.py", {
                "session_id": "s1", "cwd": str(raiz), "model": "gpt-5.4",
                "permission_mode": "default", "transcript_path": "x.jsonl",
            })
            self.assertEqual(resultado.returncode, 0)
            cuerpo = _stdout_json(resultado)
            self.assertEqual(cuerpo["hookSpecificOutput"]["hookEventName"], "SessionStart")
            contexto = cuerpo["hookSpecificOutput"]["additionalContext"]
            self.assertIn("orquestador", contexto)
            self.assertNotIn("HH", contexto)

            estado = _leer_estado(raiz, "s1")
            self.assertEqual(estado["session_id"], "s1")
            self.assertEqual(estado["modelo"], "gpt-5.4")
            self.assertEqual(estado["archivos_tocados"], [])
            self.assertEqual(estado["turnos"], 0)
            self.assertIn("inicio_epoch", estado)

    def test_no_pisa_el_inicio_si_ya_existia(self):
        with directorio_temporal() as tmp:
            raiz = _preparar_proyecto(Path(tmp))
            _correr_hook("session_start.py", {"session_id": "s1", "cwd": str(raiz), "model": "gpt-5.4"})
            primero = _leer_estado(raiz, "s1")["inicio_epoch"]
            _correr_hook("session_start.py", {"session_id": "s1", "cwd": str(raiz), "model": "gpt-5.4"})
            segundo = _leer_estado(raiz, "s1")["inicio_epoch"]
            self.assertEqual(primero, segundo)


class TestUserPromptSubmit(unittest.TestCase):
    def test_captura_las_tres_etiquetas_y_cuenta_el_turno(self):
        with directorio_temporal() as tmp:
            raiz = _preparar_proyecto(Path(tmp))
            prompt = "dale #tarea:documentacion #complejidad:alta #ticket:abc-123 -- resto del pedido"
            resultado = _correr_hook("user_prompt_submit.py", {
                "session_id": "s1", "cwd": str(raiz), "prompt": prompt,
            })
            self.assertEqual(resultado.returncode, 0)
            estado = _leer_estado(raiz, "s1")
            self.assertEqual(estado["tarea_declarada"], "documentacion")
            self.assertEqual(estado["complejidad_declarada"], "alta")
            self.assertEqual(estado["ticket"], "ABC-123")
            self.assertEqual(estado["turnos"], 1)

    def test_no_persiste_el_texto_crudo_del_prompt(self):
        with directorio_temporal() as tmp:
            raiz = _preparar_proyecto(Path(tmp))
            prompt = "el dato sensible es hunter2-secreto-unico-9182"
            _correr_hook("user_prompt_submit.py", {"session_id": "s1", "cwd": str(raiz), "prompt": prompt})
            ruta_estado = raiz / "tsoft-dev" / "metrics" / "sesiones" / "s1.json"
            self.assertNotIn("hunter2-secreto-unico-9182", ruta_estado.read_text(encoding="utf-8"))

    def test_turnos_se_acumula_entre_llamadas(self):
        with directorio_temporal() as tmp:
            raiz = _preparar_proyecto(Path(tmp))
            _correr_hook("user_prompt_submit.py", {"session_id": "s1", "cwd": str(raiz), "prompt": "hola"})
            _correr_hook("user_prompt_submit.py", {"session_id": "s1", "cwd": str(raiz), "prompt": "de nuevo"})
            estado = _leer_estado(raiz, "s1")
            self.assertEqual(estado["turnos"], 2)


class TestPostToolUse(unittest.TestCase):
    def test_apply_patch_registra_archivos_y_cuenta_ediciones_por_archivo(self):
        with directorio_temporal() as tmp:
            raiz = _preparar_proyecto(Path(tmp))
            parche = "*** Add File: src/foo.py\n+contenido\n*** Update File: src/bar.py\n"
            _correr_hook("post_tool_use.py", {
                "session_id": "s1", "cwd": str(raiz),
                "tool_name": "apply_patch",
                "tool_input": {"command": parche},
            })
            estado = _leer_estado(raiz, "s1")
            self.assertEqual(sorted(estado["archivos_tocados"]), ["src/bar.py", "src/foo.py"])
            self.assertEqual(estado["ediciones"], 2)

    def test_no_duplica_el_archivo_pero_si_cuenta_la_edicion(self):
        with directorio_temporal() as tmp:
            raiz = _preparar_proyecto(Path(tmp))
            parche = "*** Update File: src/foo.py\n"
            for _ in range(2):
                _correr_hook("post_tool_use.py", {
                    "session_id": "s1", "cwd": str(raiz),
                    "tool_name": "apply_patch", "tool_input": {"command": parche},
                })
            estado = _leer_estado(raiz, "s1")
            self.assertEqual(estado["archivos_tocados"], ["src/foo.py"])
            self.assertEqual(estado["ediciones"], 2)

    def test_redacta_secretos_en_comandos_bash(self):
        with directorio_temporal() as tmp:
            raiz = _preparar_proyecto(Path(tmp))
            cmd = 'curl -H "Authorization: Bearer sk-secreto-real-no-deberia-quedar" https://api.example.com'
            _correr_hook("post_tool_use.py", {
                "session_id": "s1", "cwd": str(raiz),
                "tool_name": "Bash", "tool_input": {"command": cmd},
            })
            estado = _leer_estado(raiz, "s1")
            self.assertNotIn("sk-secreto-real-no-deberia-quedar", estado["comandos"][0])

    def test_registra_subagentes_invocados_por_tool_use(self):
        with directorio_temporal() as tmp:
            raiz = _preparar_proyecto(Path(tmp))
            _correr_hook("post_tool_use.py", {
                "session_id": "s1", "cwd": str(raiz),
                "tool_name": "Agent", "tool_input": {"agent_type": "explorador"},
            })
            estado = _leer_estado(raiz, "s1")
            self.assertIn("explorador", estado["subagentes"])


class TestSubagentStartStop(unittest.TestCase):
    def test_start_escribe_marcador_y_stop_lo_consume_y_borra(self):
        with directorio_temporal() as tmp:
            raiz = _preparar_proyecto(Path(tmp))
            transcript = _crear_transcript_minimo(raiz, "sub-transcript.jsonl", 500, 100)

            _correr_hook("subagent_start.py", {
                "agent_id": "ag-1", "agent_type": "desarrollador",
                "session_id": "padre-1", "cwd": str(raiz), "model": "gpt-5.4",
            })
            marcador = raiz / "tsoft-dev" / "metrics" / "sesiones" / "sub-ag-1.json"
            self.assertTrue(marcador.exists())

            _correr_hook("subagent_stop.py", {
                "agent_id": "ag-1", "agent_type": "desarrollador",
                "session_id": "padre-1", "cwd": str(raiz), "model": "gpt-5.4",
                "agent_transcript_path": str(transcript),
            })

            self.assertFalse(marcador.exists(), "el marcador deberia borrarse al cerrar")

            ledger = _leer_ledger(raiz)
            self.assertEqual(len(ledger), 1)
            registro = ledger[0]
            self.assertEqual(registro["evento"], "subagente")
            self.assertEqual(registro["agent_id"], "ag-1")
            self.assertEqual(registro["agent_type"], "desarrollador")
            self.assertEqual(registro["session_id"], "padre-1")
            self.assertTrue(registro["marcador_hallado"])
            self.assertEqual(registro["tokens"]["total"], 600)
            self.assertFalse(registro["tokens"]["estimacion"])

    def test_stop_sin_marcador_previo_no_rompe_y_lo_avisa(self):
        with directorio_temporal() as tmp:
            raiz = _preparar_proyecto(Path(tmp))
            resultado = _correr_hook("subagent_stop.py", {"agent_id": "huerfano", "cwd": str(raiz)})
            self.assertEqual(resultado.returncode, 0)
            ledger = _leer_ledger(raiz)
            self.assertEqual(len(ledger), 1)
            self.assertFalse(ledger[0]["marcador_hallado"])


class TestTurnStop(unittest.TestCase):
    def test_escribe_ledger_y_reportes_con_el_esquema_nuevo(self):
        with directorio_temporal() as tmp:
            raiz = _preparar_proyecto(Path(tmp))
            transcript = _crear_transcript_minimo(raiz, "transcript.jsonl", 5000, 1000)

            resultado = _correr_hook("turn_stop.py", {
                "session_id": "s1", "cwd": str(raiz), "model": "gpt-5.4",
                "transcript_path": str(transcript),
                "last_assistant_message": "TAREA = documentacion | COMPLEJIDAD = alta | FEATURE = mi-feature",
            })
            self.assertEqual(resultado.returncode, 0)
            cuerpo = _stdout_json(resultado)
            self.assertIn("Tokens=6,000", cuerpo["systemMessage"])

            ledger = _leer_ledger(raiz)
            self.assertEqual(len(ledger), 1)
            registro = ledger[0]
            self.assertEqual(registro["evento"], "ejecucion")
            self.assertEqual(registro["session_id"], "s1")
            self.assertEqual(registro["feature"], "mi-feature")
            self.assertEqual(registro["tokens"]["total"], 6000)
            self.assertEqual(registro["clasificacion"]["tipo_tarea"], "documentacion")
            self.assertEqual(registro["clasificacion"]["complejidad"], "alta")
            self.assertNotIn("hh", registro)

            self.assertTrue((raiz / "tsoft-dev" / "reportes" / "ejecuciones" / "s1.md").exists())
            self.assertTrue((raiz / "tsoft-dev" / "reportes" / "consolidado.md").exists())

    def test_dos_cierres_de_la_misma_sesion_el_consolidado_no_duplica(self):
        with directorio_temporal() as tmp:
            raiz = _preparar_proyecto(Path(tmp))
            transcript1 = _crear_transcript_minimo(raiz, "t1.jsonl", 1000, 100)
            transcript2 = _crear_transcript_minimo(raiz, "t2.jsonl", 3000, 300)

            _correr_hook("turn_stop.py", {"session_id": "s1", "cwd": str(raiz),
                                           "model": "gpt-5.4", "transcript_path": str(transcript1)})
            _correr_hook("turn_stop.py", {"session_id": "s1", "cwd": str(raiz),
                                           "model": "gpt-5.4", "transcript_path": str(transcript2)})

            ledger = _leer_ledger(raiz)
            self.assertEqual(len(ledger), 2, "cada Stop agrega una foto acumulada, no reemplaza")

            consolidado = (raiz / "tsoft-dev" / "reportes" / "consolidado.md").read_text(encoding="utf-8")
            self.assertIn("| Ejecuciones | 1 |", consolidado)

    def test_respeta_consolidado_automatico_false(self):
        with directorio_temporal() as tmp:
            raiz = _preparar_proyecto(Path(tmp))
            ruta_celula = raiz / "tsoft-dev" / "config" / "celula.json"
            celula = json.loads(ruta_celula.read_text(encoding="utf-8"))
            celula["consolidado_automatico"] = False
            ruta_celula.write_text(json.dumps(celula), encoding="utf-8")

            transcript = _crear_transcript_minimo(raiz, "t.jsonl")
            _correr_hook("turn_stop.py", {"session_id": "s1", "cwd": str(raiz),
                                           "model": "gpt-5.4", "transcript_path": str(transcript)})

            self.assertFalse((raiz / "tsoft-dev" / "reportes" / "consolidado.md").exists())
            self.assertTrue((raiz / "tsoft-dev" / "reportes" / "ejecuciones" / "s1.md").exists())


class TestSessionEnd(unittest.TestCase):
    def test_marca_el_fin_si_no_estaba(self):
        with directorio_temporal() as tmp:
            raiz = _preparar_proyecto(Path(tmp))
            _correr_hook("session_start.py", {"session_id": "s1", "cwd": str(raiz), "model": "gpt-5.4"})
            _correr_hook("session_end.py", {"session_id": "s1", "cwd": str(raiz)})
            estado = _leer_estado(raiz, "s1")
            self.assertIn("fin", estado)

    def test_no_pisa_un_fin_que_turn_stop_ya_puso(self):
        with directorio_temporal() as tmp:
            raiz = _preparar_proyecto(Path(tmp))
            transcript = _crear_transcript_minimo(raiz, "t.jsonl")
            _correr_hook("turn_stop.py", {"session_id": "s1", "cwd": str(raiz),
                                           "model": "gpt-5.4", "transcript_path": str(transcript)})
            fin_de_turn_stop = _leer_estado(raiz, "s1")["fin"]
            _correr_hook("session_end.py", {"session_id": "s1", "cwd": str(raiz)})
            fin_final = _leer_estado(raiz, "s1")["fin"]
            self.assertEqual(fin_de_turn_stop, fin_final)


class TestFlujoIntegradoDeSesion(unittest.TestCase):
    """Encadena varios hooks como en una sesion real chica: arranca, declara
    tarea, toca un archivo, corre un subagente, y cierra. Este es el tipo de
    bug que un test aislado por hook no agarra: un dato que un hook deja mal
    escrito y el siguiente hook lee mal (el error de plomeria, no de formula)."""

    def test_sesion_completa_de_punta_a_punta(self):
        with directorio_temporal() as tmp:
            raiz = _preparar_proyecto(Path(tmp))
            transcript_padre = _crear_transcript_minimo(raiz, "padre.jsonl", 2000, 500)
            transcript_hijo = _crear_transcript_minimo(raiz, "hijo.jsonl", 300, 50)

            _correr_hook("session_start.py", {"session_id": "s1", "cwd": str(raiz), "model": "gpt-5.4"})
            _correr_hook("user_prompt_submit.py", {
                "session_id": "s1", "cwd": str(raiz),
                "prompt": "$orquestador mi-feature #tarea:evolutivo-frontend #complejidad:media",
            })
            _correr_hook("post_tool_use.py", {
                "session_id": "s1", "cwd": str(raiz),
                "tool_name": "apply_patch",
                "tool_input": {"command": "*** Add File: src/nuevo.py\n"},
            })
            _correr_hook("subagent_start.py", {
                "agent_id": "ag-1", "agent_type": "explorador",
                "session_id": "s1", "cwd": str(raiz), "model": "gpt-5.4",
            })
            _correr_hook("subagent_stop.py", {
                "agent_id": "ag-1", "agent_type": "explorador",
                "session_id": "s1", "cwd": str(raiz), "model": "gpt-5.4",
                "agent_transcript_path": str(transcript_hijo),
            })
            _correr_hook("turn_stop.py", {
                "session_id": "s1", "cwd": str(raiz), "model": "gpt-5.4",
                "transcript_path": str(transcript_padre),
                "last_assistant_message": "TAREA = evolutivo-frontend | COMPLEJIDAD = media | FEATURE = mi-feature",
            })
            _correr_hook("session_end.py", {"session_id": "s1", "cwd": str(raiz)})

            estado = _leer_estado(raiz, "s1")
            self.assertEqual(estado["tarea_declarada"], "evolutivo-frontend")
            self.assertEqual(estado["archivos_tocados"], ["src/nuevo.py"])
            self.assertEqual(estado["feature"], "mi-feature")
            self.assertIn("fin", estado)

            ledger = _leer_ledger(raiz)
            eventos = {registro["evento"] for registro in ledger}
            self.assertEqual(eventos, {"ejecucion", "subagente"})

            ejecucion = next(r for r in ledger if r["evento"] == "ejecucion")
            self.assertEqual(ejecucion["feature"], "mi-feature")
            self.assertEqual(ejecucion["evidencia"]["archivos_tocados"], ["src/nuevo.py"])
            self.assertEqual(ejecucion["evidencia"]["turnos"], 1)


if __name__ == "__main__":
    unittest.main()
