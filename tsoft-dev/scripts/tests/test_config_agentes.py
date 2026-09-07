"""Tests de config de agentes: consistencia entre lo que dicen los .toml y
config.toml, y lo que el flujo del orquestador realmente hace.

Corren con: py -3 tsoft-dev/scripts/tests/test_config_agentes.py
"""

import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]


class TestSandboxModeConsistente(unittest.TestCase):
    def test_planificador_en_high_como_desarrollador(self):
        # El planificador decide arquitectura (su output template exige
        # "Decisiones de arquitectura"); dejarlo en un modelo mas barato
        # que el desarrollador -- que solo ejecuta lo ya decidido -- es
        # invertir el presupuesto de razonamiento al reves.
        texto = (RAIZ / ".codex" / "agents" / "planificador.toml").read_text(encoding="utf-8")
        self.assertIn('model_reasoning_effort = "high"', texto)

    def test_explorador_y_planificador_pueden_escribir_su_propio_artefacto(self):
        # read-only contradice que ambos tengan que escribir su output
        # (explorador-output.md, design.md). El patron del kit para esto
        # ya existe en documentador/qa: workspace-write + reforzar en
        # prosa que solo tocan su propio archivo.
        for archivo in ("explorador.toml", "planificador.toml"):
            texto = (RAIZ / ".codex" / "agents" / archivo).read_text(encoding="utf-8")
            self.assertIn('sandbox_mode = "workspace-write"', texto, archivo)

    def test_la_restriccion_esta_en_developer_instructions_no_solo_en_description(self):
        # description es metadata de seleccion de agente; developer_instructions
        # es el texto que de verdad llega al prompt del subagente spawneado. La
        # restriccion tiene que vivir ahi para que realmente lo frene.
        for archivo in ("explorador.toml", "planificador.toml"):
            texto = (RAIZ / ".codex" / "agents" / archivo).read_text(encoding="utf-8")
            self.assertIn(
                "No modificás ningún archivo del proyecto excepto tu propio artefacto",
                texto,
                archivo,
            )


class TestMaxThreadsHonesto(unittest.TestCase):
    def test_max_threads_no_promete_paralelismo_que_no_existe(self):
        # El flujo del orquestador invoca un subagente a la vez. Un
        # max_threads > 1 sin un flujo que realmente paralelice es un
        # numero que no hace nada, y alguien podria leerlo como que el
        # kit ya corre agentes en paralelo.
        texto = (RAIZ / ".codex" / "config.toml").read_text(encoding="utf-8")
        self.assertIn("max_threads = 1", texto)


class TestEficienciaDeTokens(unittest.TestCase):
    """Cambios del backlog de eficiencia de tokens (auditoria 2026-08-30),
    probados primero en un worktree aislado antes de darlos por version
    oficial del kit.
    """

    def test_modelo_del_orquestador_esta_a_nivel_raiz_antes_de_agents(self):
        # El Orquestador solo coordina -- no necesita el modelo mas caro.
        # La clave debe estar ANTES de [agents], sino TOML la asigna a esa
        # seccion y no gobierna la sesion del orquestador (verificado con
        # codex doctor --json).
        texto = (RAIZ / ".codex" / "config.toml").read_text(encoding="utf-8")
        pos_model = texto.index('\nmodel = "gpt-5.4-mini"')
        pos_agents = texto.index("\n[agents]")
        self.assertLess(pos_model, pos_agents)

    def test_documentador_usa_modelo_liviano(self):
        # Solo lee codigo y escribe documentacion -- no decide arquitectura
        # ni escribe codigo, no necesita el modelo mas caro.
        texto = (RAIZ / ".codex" / "agents" / "documentador.toml").read_text(encoding="utf-8")
        self.assertIn('model = "gpt-5.4-mini"', texto)

    def test_planificador_no_relee_material_crudo_si_ya_hay_explorador_output(self):
        # El explorador-output.md ya destilo docs/[feature]/ -- releerlo de
        # nuevo en el planificador duplica tokens sin sumar informacion.
        texto = (RAIZ / ".codex" / "agents" / "planificador.toml").read_text(encoding="utf-8")
        self.assertIn("Qué NO releés", texto)

    def test_desarrollador_no_valida_visualmente_en_navegador(self):
        # Verificar visualmente en el navegador es responsabilidad exclusiva
        # de QA, que corre despues. El desarrollador que tambien lo hace
        # duplica esa verificacion.
        texto = (RAIZ / ".codex" / "agents" / "desarrollador.toml").read_text(encoding="utf-8")
        self.assertIn("No hacés validación visual en navegador", texto)


if __name__ == "__main__":
    unittest.main()
