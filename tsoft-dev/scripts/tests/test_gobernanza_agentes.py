"""Tests de consistencia entre los .toml de agentes y orquestador/SKILL.md.

Corren con: py -3 tsoft-dev/scripts/tests/test_gobernanza_agentes.py
"""

import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
MARCADOR_APROBACION = "**Aprobado por IA Maker: SI**"


class TestMarcadorDeAprobacion(unittest.TestCase):
    def test_desarrollador_y_orquestador_exigen_el_mismo_marcador(self):
        # Bug real que ya paso una vez en este kit (ver "retomar desde" en
        # metrics_lib.py): dos archivos de texto que tienen que decir
        # exactamente lo mismo, sin ningun chequeo automatico que los
        # mantenga sincronizados si uno cambia y el otro no.
        desarrollador = (RAIZ / ".codex" / "agents" / "desarrollador.toml").read_text(encoding="utf-8")
        orquestador = (RAIZ / ".codex" / "skills" / "orquestador" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(MARCADOR_APROBACION, desarrollador)
        self.assertIn(MARCADOR_APROBACION, orquestador)


class TestPlantillaAgentsMd(unittest.TestCase):
    """
    AGENTS.md fantasma (2026-08-30): el kit dependia de que el proyecto
    destino tuviera un AGENTS.md, pero ningun archivo del paquete lo traia
    ni lo creaba -- los 5 agentes mandaban leerlo "de la raiz" sin que
    nada garantizara que existiera. Estos tests protegen las dos partes
    del fix: que la plantilla siga trayendo la Convencion de features (de
    la que depende la medicion) y que empaquetar.ps1 la siga incluyendo.
    """

    def test_la_plantilla_existe_y_trae_la_convencion_de_features(self):
        plantilla = (RAIZ / "plantillas" / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("Convención de features", plantilla)
        self.assertIn("docs/[feature]/", plantilla)
        self.assertIn("tsoft-dev/[feature]/", plantilla)
        self.assertIn("$orquestador [feature]", plantilla)

    def test_empaquetar_incluye_la_carpeta_plantillas(self):
        empaquetar = (RAIZ / "empaquetar.ps1").read_text(encoding="utf-8")
        self.assertIn("'plantillas'", empaquetar)


class TestExclusionLocalDeMetricas(unittest.TestCase):
    """
    Excluir tsoft-dev/metrics|reportes con .gitignore/.git/info/exclude no
    alcanza si esas carpetas ya quedaron trackeadas -- Git las sigue
    versionando igual. Los dos instaladores tienen que detectar ese caso
    (no solo el de "no esta en el .gitignore") y el manual tiene que dar el
    comando exacto para sacarlas del indice sin borrar los archivos locales.
    """

    COMANDO_RM_CACHED = "git rm -r --cached tsoft-dev/metrics tsoft-dev/reportes"

    def test_instalar_ps1_detecta_carpetas_ya_trackeadas(self):
        texto = (RAIZ / "instalar.ps1").read_text(encoding="utf-8")
        self.assertIn("ls-files", texto)
        self.assertIn(self.COMANDO_RM_CACHED, texto)

    def test_instalar_sh_detecta_carpetas_ya_trackeadas(self):
        texto = (RAIZ / "instalar.sh").read_text(encoding="utf-8")
        self.assertIn("ls-files", texto)
        self.assertIn(self.COMANDO_RM_CACHED, texto)

    def test_manual_documenta_el_comando_git_rm_cached(self):
        manual = (RAIZ / "MANUAL-DEV.md").read_text(encoding="utf-8")
        self.assertIn(self.COMANDO_RM_CACHED, manual)
        self.assertIn("no los borra de tu disco", manual)


class TestRutasRelativas(unittest.TestCase):
    """
    /tsoft-dev/[feature]/... y /docs/[feature]/... (con barra inicial) son
    las instrucciones textuales que Codex lee para saber donde leer/escribir
    cada artefacto. En Windows, una ruta que empieza con "/" sin letra de
    unidad resuelve contra la raiz de la unidad actual (C:\tsoft-dev\...),
    no contra la raiz del proyecto -- un riesgo real, aunque no se
    reprodujo en las 2 corridas end-to-end reales que se hicieron con el
    kit (libreria-ecommerce-kit-e2e y la migracion en Claro).
    """

    ARCHIVOS = (
        RAIZ / ".codex" / "agents" / "desarrollador.toml",
        RAIZ / ".codex" / "agents" / "documentador.toml",
        RAIZ / ".codex" / "agents" / "explorador.toml",
        RAIZ / ".codex" / "agents" / "planificador.toml",
        RAIZ / ".codex" / "agents" / "qa.toml",
        RAIZ / ".codex" / "skills" / "orquestador" / "SKILL.md",
    )

    def test_no_quedan_rutas_con_barra_inicial(self):
        for archivo in self.ARCHIVOS:
            texto = archivo.read_text(encoding="utf-8")
            with self.subTest(archivo=archivo.name):
                self.assertNotIn("/tsoft-dev/", texto)
                self.assertNotIn("/docs/[feature]", texto)


class TestLimpiezaDeReferenciasAHH(unittest.TestCase):
    """
    La formula de HH ahorradas se elimino el 2026-08-27 (no queda ninguna
    funcion hh_* en metrics_lib.py), pero quedaron frases sueltas en la
    documentacion que todavia prometian o describian ese calculo. Este test
    no prohibe la palabra "ahorro" en general -- MANUAL-DEV.md tiene una
    seccion legitima que explica POR QUE no hay horas-hombre ahorradas, y
    esa tiene que seguir ahi. Prohibe las frases puntuales que describian
    el calculo como si todavia existiera.
    """

    FRASES_PROHIBIDAS = (
        "ahorro reportado",
        "un ahorro medido",
        "infla el ahorro",
        "medir HH automaticamente",
        "medir HH automáticamente",
        "cae a un valor de respaldo deliberadamente conservador",
    )

    def _sin_frases_prohibidas(self, texto: str):
        for frase in self.FRASES_PROHIBIDAS:
            self.assertNotIn(frase, texto)

    def test_manual_dev_no_promete_ahorro(self):
        manual = (RAIZ / "MANUAL-DEV.md").read_text(encoding="utf-8")
        self._sin_frases_prohibidas(manual)
        # La seccion que EXPLICA por que se elimino tiene que seguir estando.
        self.assertIn("Por qué no hay horas-hombre ahorradas", manual)

    def test_skill_orquestador_no_promete_medir_hh(self):
        skill = (RAIZ / ".codex" / "skills" / "orquestador" / "SKILL.md").read_text(encoding="utf-8")
        self._sin_frases_prohibidas(skill)

    def test_docstrings_no_mencionan_calcular_hh(self):
        metrics_lib = (RAIZ / "tsoft-dev" / "scripts" / "metrics_lib.py").read_text(encoding="utf-8")
        turn_stop = (RAIZ / ".codex" / "hooks" / "turn_stop.py").read_text(encoding="utf-8")
        self.assertNotIn("Calcular horas-hombre", metrics_lib)
        self.assertNotIn("mide tokens y HH", turn_stop)


class TestManejoDeBloqueosNoImplicaActuarElRol(unittest.TestCase):
    """
    Bug real confirmado en una corrida en vivo (2026-08-30, feature
    actualizar-ui): el Desarrollador se bloqueo por complejidad alta: el IA
    Maker eligio "1. Resolver el bloqueo y reintentar", y el Orquestador
    -- en vez de volver a spawnear al Desarrollador -- implemento la
    feature el mismo (10 apply_patch + varios exec_command en su propia
    conversacion, confirmado contra el rollout crudo). La seccion "Manejo
    de bloqueos" nunca aclaraba que "reintentar" significa reinvocar al
    mismo subagente, asi que el modelo lleno ese vacio haciendo el trabajo
    el mismo.
    """

    def test_manejo_de_bloqueos_aclara_que_reintentar_es_reinvocar(self):
        skill = (RAIZ / ".codex" / "skills" / "orquestador" / "SKILL.md").read_text(encoding="utf-8")
        seccion = skill.split("## Manejo de bloqueos", 1)[1]
        self.assertIn("volver a spawnear", seccion)
        self.assertIn("nunca implementar la solución vos mismo", seccion)


if __name__ == "__main__":
    unittest.main()
