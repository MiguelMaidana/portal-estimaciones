"""
metrics_lib.py - Nucleo de medicion del TSOFT AI Dev Kit (Codex).

Responsabilidades:
  1. Localizar la raiz del kit desde cualquier cwd.
  2. Leer/escribir el ledger de eventos (JSONL append-only).
  3. Extraer consumo de tokens del transcript de la sesion de Codex.
  4. Clasificar tipo/complejidad de tarea segun baselines configurables.

Sin dependencias externas: solo stdlib (Windows / Linux / macOS).
El formato del transcript de Codex NO es una interfaz estable; el
extractor es defensivo y siempre reporta de que fuente salio el dato.
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

MARCADOR_RAIZ = "tsoft-dev/config/celula.json"

CLAVES_TOKENS = {
    "input_tokens": "input",
    "prompt_tokens": "input",
    "cached_input_tokens": "cache",
    "cached_tokens": "cache",
    "output_tokens": "output",
    "completion_tokens": "output",
    "reasoning_output_tokens": "reasoning",
    "reasoning_tokens": "reasoning",
    "total_tokens": "total",
}

PATRONES_SUBAGENTE = (
    re.compile(r"\b(?:resumen del|output actualizado del)\s+(explorador|planificador|desarrollador|documentador|qa)\b", re.IGNORECASE),
    # "de" y "del" son la misma frase: el Orquestador escribe las dos.
    re.compile(r"\bresumen del output del?\s+`?(explorador|planificador|desarrollador|documentador|qa)`?\b", re.IGNORECASE),
    re.compile(r"`?(explorador|planificador|desarrollador|documentador|qa)`?\s+completado y aprobado\b", re.IGNORECASE),
    re.compile(r"\breinvoco al\s+(explorador|planificador|desarrollador|documentador|qa)\b", re.IGNORECASE),
    re.compile(r"\b(spawne[aá] el subagente|subagente)\s+(explorador|planificador|desarrollador|documentador|qa)\b", re.IGNORECASE),
)

# Los patrones de arriba buscan senales de que un subagente YA corrio. Pero el
# Orquestador cierra casi todos sus mensajes ofreciendo el paso siguiente
# ("despues te ofrezco continuar con el Planificador"), y esa mencion futura no
# es evidencia de ejecucion. Sin este veto, el primer subagente del flujo
# arrastra al segundo y el registro dice que corrieron dos.
#
# Se aplica sobre el texto que ANTECEDE al match, exigiendo que no haya cierre
# de oracion en el medio: el marcador tiene que estar en la misma frase.
RE_MENCION_PROSPECTIVA = re.compile(
    r"\b(?:continuar|contin[uú]a|seguir|sigue|avanzar|pasar|arrancar|empezar"
    r"|comenzar|invocar|despachar|ofrezco|ofrecer|listo\s+para"
    r"|pr[oó]ximo\s+paso|siguiente\s+paso|queda\s+pendiente|pendiente)\b"
    r"[^.;\n]{0,60}$",
    re.IGNORECASE,
)


def _es_mencion_prospectiva(mensaje: str, inicio: int) -> bool:
    """True si el subagente detectado en `inicio` se menciona como paso futuro."""
    return bool(RE_MENCION_PROSPECTIVA.search(mensaje[:inicio]))


def raiz_kit(inicio: str | os.PathLike | None = None) -> Path:
    """Sube desde inicio (o cwd) hasta encontrar la raiz del kit."""
    env = os.environ.get("TSOFT_KIT_HOME")
    if env and (Path(env) / MARCADOR_RAIZ).exists():
        return Path(env).resolve()

    actual = Path(inicio or os.getcwd()).resolve()
    for candidato in [actual, *actual.parents]:
        if (candidato / MARCADOR_RAIZ).exists():
            return candidato

    return Path(__file__).resolve().parents[2]


def cargar_config(raiz: Path | None = None) -> dict:
    raiz = raiz or raiz_kit()
    with (raiz / MARCADOR_RAIZ).open(encoding="utf-8") as fh:
        return json.load(fh)


def cargar_baselines(raiz: Path | None = None) -> dict:
    raiz = raiz or raiz_kit()
    with (raiz / "tsoft-dev/config/baselines.json").open(encoding="utf-8") as fh:
        return json.load(fh)


def ruta_ledger(raiz: Path | None = None) -> Path:
    raiz = raiz or raiz_kit()
    destino = raiz / "tsoft-dev/metrics/ledger.jsonl"
    destino.parent.mkdir(parents=True, exist_ok=True)
    return destino


def ruta_estado(session_id: str, raiz: Path | None = None) -> Path:
    raiz = raiz or raiz_kit()
    destino = raiz / "tsoft-dev/metrics/sesiones" / f"{session_id}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    return destino


def ahora_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_ledger(evento: dict, raiz: Path | None = None) -> None:
    with ruta_ledger(raiz).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(evento, ensure_ascii=False) + "\n")


def leer_ledger(raiz: Path | None = None) -> list[dict]:
    """
    Lee el ledger salteando las lineas ilegibles en vez de abortar.

    Antes una sola linea rota tiraba TODO el historico: el ledger es
    append-only y una escritura interrumpida deja media linea al final, asi
    que el modo frágil convertia un renglon dañado en la perdida completa de
    los reportes. Las lineas descartadas se avisan por stderr, nunca por
    stdout: los hooks usan stdout para su protocolo JSON con Codex.
    """
    import sys

    ruta = ruta_ledger(raiz)
    if not ruta.exists():
        return []

    registros: list[dict] = []
    descartadas = 0

    with ruta.open(encoding="utf-8", errors="replace") as fh:
        for numero, linea in enumerate(fh, 1):
            if not linea.strip():
                continue
            try:
                registro = json.loads(linea)
            except Exception:
                descartadas += 1
                continue
            if isinstance(registro, dict):
                registros.append(registro)
            else:
                descartadas += 1

    if descartadas:
        print(
            f"aviso: {descartadas} linea(s) ilegibles en {ruta.name}, "
            f"se leyeron {len(registros)} registros",
            file=sys.stderr,
        )

    return registros


def ultimas_ejecuciones(ledger: list[dict]) -> list[dict]:
    """
    Una linea por sesion: la ultima de cada session_id.

    El ledger guarda una foto ACUMULADA en cada Stop, no un delta. Una sesion
    con tres cierres deja tres lineas y la ultima ya contiene todo lo anterior,
    asi que sumarlas multiplica el consumo. Con 21 cierres de una misma sesion
    el total se infla mas de diez veces.
    """
    ultimas: dict[str, dict] = {}
    for registro in ledger:
        if not isinstance(registro, dict) or registro.get("evento") != "ejecucion":
            continue
        session_id = registro.get("session_id")
        if session_id:
            ultimas[session_id] = registro
    return list(ultimas.values())


def subagentes_de_sesion(ledger: list[dict], session_id: str | None = None) -> list[dict]:
    """
    Una linea por subagente: la ultima de cada agent_id.

    Misma proteccion que ultimas_ejecuciones: si un agent_id dejara mas de un
    cierre, sumarlos duplicaria su consumo.

    El consumo del subagente NO esta incluido en el del padre. Se verifico
    contra Codex 0.149.1 comparando output_tokens: el padre reporto 935 y el
    hijo 969, o sea que el padre no pudo haber generado la salida del hijo.
    Por eso estos tokens SE SUMAN a los de la ejecucion, no la reemplazan.
    """
    ultimos: dict[str, dict] = {}
    for registro in ledger:
        if not isinstance(registro, dict) or registro.get("evento") != "subagente":
            continue
        if session_id and registro.get("session_id") != session_id:
            continue
        agent_id = registro.get("agent_id")
        if agent_id:
            ultimos[agent_id] = registro
    return list(ultimos.values())


def leer_estado(session_id: str, raiz: Path | None = None) -> dict:
    """
    Estado de la sesion; {} si el archivo no existe o quedo ilegible.

    Un estado corrupto hace perder la evidencia de esa sesion, pero levantar
    una excepcion adentro de un hook es peor: rompe el turno del usuario por
    un problema de contabilidad.
    """
    ruta = ruta_estado(session_id, raiz)
    if not ruta.exists():
        return {}
    try:
        with ruta.open(encoding="utf-8") as fh:
            datos = json.load(fh)
    except Exception:
        return {}
    return datos if isinstance(datos, dict) else {}


def escribir_estado(session_id: str, estado: dict, raiz: Path | None = None) -> None:
    """
    Escritura atomica: temporal + rename.

    Abrir en "w" trunca el archivo ANTES de escribir. Si el proceso muere en
    el medio (timeout del hook, cierre de Codex, Ctrl+C) el estado no queda a
    medias: queda destruido. Con os.replace el archivo viejo sigue intacto
    hasta que el nuevo esta completo en disco, y el reemplazo es atomico tanto
    en Windows como en POSIX.

    El temporal lleva el pid para que dos procesos que escriban la misma
    sesion no se pisen el archivo intermedio.
    """
    destino = ruta_estado(session_id, raiz)
    tmp = destino.with_suffix(f".{os.getpid()}.tmp")

    # Un proceso muerto a mitad de escritura deja su temporal. No molesta a
    # nadie (nadie lo lee) pero se acumula: se barren los viejos de paso.
    try:
        for viejo_tmp in destino.parent.glob("*.tmp"):
            if time.time() - viejo_tmp.stat().st_mtime > 3600:
                viejo_tmp.unlink()
    except Exception:
        pass

    try:
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(estado, fh, ensure_ascii=False, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, destino)
    except Exception:
        try:
            tmp.unlink()
        except Exception:
            pass
        raise


def _buscar_usos(nodo, camino: str = "") -> list[tuple[str, dict]]:
    """Busca recursivamente cualquier objeto con claves de uso de tokens."""
    resultados = []
    if isinstance(nodo, dict):
        claves_encontradas = set(nodo) & set(CLAVES_TOKENS)
        if claves_encontradas:
            resultados.append((camino, nodo))
        for clave, valor in nodo.items():
            resultados.extend(_buscar_usos(valor, f"{camino}.{clave}"))
    elif isinstance(nodo, list):
        for indice, item in enumerate(nodo):
            resultados.extend(_buscar_usos(item, f"{camino}[{indice}]"))
    return resultados


def _normalizar_uso(bruto: dict) -> dict:
    normalizado = {}
    for clave_original, categoria in CLAVES_TOKENS.items():
        if clave_original in bruto:
            valor = bruto[clave_original]
            if isinstance(valor, (int, float)):
                normalizado[categoria] = normalizado.get(categoria, 0) + valor
    return normalizado


def _cargar_transcript(ruta: Path):
    """
    Carga transcripts de Codex en formato JSON o JSONL.
    Devuelve el objeto parseado o una lista de eventos.
    """
    try:
        with ruta.open(encoding="utf-8", errors="replace") as fh:
            return json.load(fh)
    except Exception:
        pass

    eventos = []
    try:
        with ruta.open(encoding="utf-8", errors="replace") as fh:
            for linea in fh:
                linea = linea.strip()
                if not linea:
                    continue
                try:
                    eventos.append(json.loads(linea))
                except Exception:
                    continue
    except Exception:
        return None

    return eventos or None


def _extraer_tokens_jsonl(eventos: list[dict]) -> dict | None:
    """
    Busca eventos token_count en transcripts JSONL de Codex.
    Prioriza total_token_usage y luego last_token_usage.
    """
    for indice in range(len(eventos) - 1, -1, -1):
        evento = eventos[indice]
        if not isinstance(evento, dict):
            continue
        if evento.get("type") != "event_msg":
            continue

        payload = evento.get("payload")
        if not isinstance(payload, dict):
            continue
        if payload.get("type") != "token_count":
            continue

        info = payload.get("info")
        if not isinstance(info, dict):
            continue

        bruto = info.get("total_token_usage") or info.get("last_token_usage")
        if not isinstance(bruto, dict):
            continue

        normalizado = _normalizar_uso(bruto)
        if not normalizado:
            continue

        if "total" not in normalizado:
            normalizado["total"] = (
                normalizado.get("input", 0)
                + normalizado.get("output", 0)
                + normalizado.get("reasoning", 0)
            )

        normalizado["fuente"] = f"jsonl:event_msg.token_count[{indice}]"
        normalizado["estimacion"] = False
        return normalizado

    return None


RE_SECRETO_ESQUEMA = re.compile(r"(?i)\b(bearer|basic)\s+(\"[^\"]*\"|'[^']*'|[^\s\"']+)")
RE_SECRETO_CLAVE = re.compile(
    r"(?i)\b([\w-]*(?:token|api[_-]?key|apikey|x-api-key|secret|password|passwd|pwd|"
    r"access[_-]?token|authorization)[\w-]*)\s*[:=]\s*(?!bearer\b|basic\b)"
    r"(\"[^\"]*\"|'[^']*'|[^\s\"']+)"
)
RE_SECRETO_URL = re.compile(r"://([^\s:@/]+):([^\s@/]+)@")


def redactar_secretos(texto: str) -> str:
    """Enmascara credenciales antes de persistir un comando capturado.

    Los comandos se guardan truncados a 120 chars como evidencia (metrics/,
    ledger.jsonl). Ese es justo el rango donde suele vivir un token de un
    curl o una URL con usuario:clave. Sin esto quedan en texto plano.

    RE_SECRETO_CLAVE no exige limite de palabra pegado al nombre de la
    variable: en OPENAI_API_KEY o AWS_SECRET_ACCESS_KEY el "_" es caracter
    de palabra, asi que un \\b ahi no encuentra limite y deja pasar el
    secreto entero. Por eso la clave se busca en cualquier parte de un
    identificador mas largo, no solo pegada a un limite.
    """
    if not isinstance(texto, str):
        return texto
    texto = RE_SECRETO_ESQUEMA.sub(lambda m: f"{m.group(1).lower()} [REDACTADO]", texto)
    texto = RE_SECRETO_CLAVE.sub(lambda m: f"{m.group(1)}=[REDACTADO]", texto)
    texto = RE_SECRETO_URL.sub(r"://\1:[REDACTADO]@", texto)
    return texto


def _agregar_unico(destino: list, valor) -> None:
    if valor and valor not in destino:
        destino.append(valor)


def _evidencia_vacia() -> dict:
    return {
        "archivos_tocados": [],
        "comandos": [],
        "subagentes": [],
        "ediciones": 0,
    }


def acumular_evidencia(evento: dict, evidencia: dict) -> None:
    """
    Suma al acumulador la evidencia tecnica de UN evento del rollout.

    Trabaja de a un evento a proposito. El recorrido de segmentar_por_feature
    sabe que feature estaba activa en cada punto del archivo, asi que puede
    atribuir cada archivo y cada comando a la feature que lo produjo. Mirar la
    conversacion entera de una vez le daria la misma evidencia a todas.
    """
    if not isinstance(evento, dict):
        return

    payload = evento.get("payload")
    if not isinstance(payload, dict):
        return

    if evento.get("type") == "response_item":
        if payload.get("type") != "function_call":
            return

        nombre = payload.get("name") or ""
        argumentos_brutos = payload.get("arguments") or "{}"
        try:
            argumentos = json.loads(argumentos_brutos)
        except Exception:
            argumentos = {}

        if nombre in ("shell_command", "Bash"):
            cmd = argumentos.get("command") or argumentos.get("cmd") or ""
            if cmd:
                _agregar_unico(evidencia["comandos"], redactar_secretos(cmd)[:120])

        elif nombre in ("parallel", "multi_tool_use.parallel"):
            for uso in argumentos.get("tool_uses", []):
                if not isinstance(uso, dict):
                    continue
                recipient = uso.get("recipient_name") or ""
                params = uso.get("parameters") or {}
                if recipient == "functions.shell_command":
                    cmd = params.get("command") or params.get("cmd") or ""
                    if cmd:
                        _agregar_unico(evidencia["comandos"], redactar_secretos(cmd)[:120])
                elif recipient:
                    _agregar_unico(evidencia["subagentes"], recipient)

        elif nombre in ("apply_patch", "Edit", "Write"):
            archivo = (
                argumentos.get("path")
                or argumentos.get("file_path")
                or argumentos.get("filename")
            )
            if archivo:
                _agregar_unico(evidencia["archivos_tocados"], archivo)
            evidencia["ediciones"] += 1

        elif nombre:
            _agregar_unico(evidencia["subagentes"], nombre)

        return

    if evento.get("type") != "event_msg":
        return

    tipo = payload.get("type") or ""

    if tipo == "patch_apply_end":
        cambios = payload.get("changes") or {}
        evidencia["ediciones"] += len(cambios)
        for archivo in cambios:
            _agregar_unico(evidencia["archivos_tocados"], archivo)

    elif tipo == "agent_message":
        mensaje = payload.get("message") or ""
        for patron in PATRONES_SUBAGENTE:
            for match in patron.finditer(mensaje):
                grupos = [grupo for grupo in match.groups() if grupo]
                if not grupos:
                    continue
                if _es_mencion_prospectiva(mensaje, match.start()):
                    continue
                _agregar_unico(evidencia["subagentes"], grupos[-1].lower())


def _leer_eventos_transcript(transcript_path: str | None):
    """
    Carga el transcript una sola vez para que quien ya lo tenga leido se lo
    pase a extraer_evidencia_transcript/extraer_tokens en vez de que cada una
    lo vuelva a abrir y parsear por su cuenta -- el Stop hook llama a las dos
    con el mismo archivo en cada turno.
    """
    if not transcript_path:
        return None

    ruta = Path(transcript_path)
    if not ruta.exists():
        return None

    return _cargar_transcript(ruta)


def extraer_evidencia_transcript(transcript_path: str | None, eventos: list | None = None) -> dict:
    """
    Recorre el transcript JSONL completo y recupera evidencia tecnica aunque
    PostToolUse no haya matcheado el runtime actual.

    Es la vista de conversacion entera, que usa el camino de hooks: ahi cada
    sesion es una unidad y no hace falta separar por feature.

    Si el caller ya cargo el transcript (via _leer_eventos_transcript), se lo
    puede pasar en `eventos` para evitar leerlo de nuevo.
    """
    evidencia = _evidencia_vacia()

    if eventos is None:
        eventos = _leer_eventos_transcript(transcript_path)

    if not isinstance(eventos, list):
        return evidencia

    for evento in eventos:
        acumular_evidencia(evento, evidencia)

    return evidencia


def extraer_tokens(transcript_path: str | None, eventos: list | None = None) -> dict:
    """
    Lee el transcript de Codex y extrae el uso de tokens.
    Siempre declara la fuente. Si no puede, devuelve estimacion=True.

    Si el caller ya cargo el transcript (via _leer_eventos_transcript), se lo
    puede pasar en `eventos` para evitar leerlo de nuevo.
    """
    vacio = {
        "input": 0,
        "output": 0,
        "total": 0,
        "fuente": "estimacion",
        "estimacion": True,
    }

    if not transcript_path:
        return vacio

    if eventos is None:
        eventos = _leer_eventos_transcript(transcript_path)

    datos = eventos
    if datos is None:
        return vacio

    if isinstance(datos, list):
        desde_jsonl = _extraer_tokens_jsonl(datos)
        if desde_jsonl:
            return desde_jsonl

    if not isinstance(datos, (dict, list)):
        return vacio

    usos = _buscar_usos(datos)
    if not usos:
        return vacio

    camino, bruto = usos[-1]
    normalizado = _normalizar_uso(bruto)

    if not normalizado:
        return vacio

    if "total" not in normalizado:
        normalizado["total"] = (
            normalizado.get("input", 0)
            + normalizado.get("output", 0)
            + normalizado.get("reasoning", 0)
        )

    normalizado["fuente"] = f"transcript:{camino}"
    normalizado["estimacion"] = False
    return normalizado


def costo_usd(uso: dict, modelo: str, config: dict) -> dict:
    """
    Calcula el costo en USD del uso de tokens.

    Importante: cached_input_tokens es un subconjunto de input_tokens, no un
    valor adicional. Cobrar ambos a precio pleno duplica el cargo de todo lo
    que vino de cache. Por eso se cobra solo el input no cacheado a precio de
    entrada, y el cacheado a precio de cache.
    """
    precios = config.get("precios_usd_por_millon", {})
    tarifa = precios.get(modelo) or precios.get("_default", {})

    moneda = config.get("moneda_local", "")

    if not tarifa or all(tarifa.get(clave, 0) == 0 for clave in ("input", "output", "cache")):
        return {
            "usd": 0,
            "local": 0,
            "moneda": moneda,
            "tarifado": False,
            "aviso": "sin precios cargados",
        }

    cache = uso.get("cache", 0)
    input_no_cacheado = max(0, uso.get("input", 0) - cache)

    usd = (
        input_no_cacheado * tarifa.get("input", 0) / 1_000_000
        + cache * tarifa.get("cache", 0) / 1_000_000
        + uso.get("output", 0) * tarifa.get("output", 0) / 1_000_000
    )

    # La moneda local es configurable: el kit se usa en varios paises y no
    # tiene sentido cablear una sola. Sin tipo de cambio cargado se devuelve
    # cero en vez de inventar una conversion.
    tipo_cambio = config.get("usd_a_moneda_local", 0)
    local = usd * tipo_cambio if tipo_cambio else 0

    return {
        "usd": round(usd, 6),
        "local": round(local, 0),
        "moneda": moneda,
        "tarifado": True,
    }


RE_TAREA = re.compile(r"TAREA\s*=\s*([a-zA-Z0-9_\-]+)", re.IGNORECASE)
RE_COMPLEJIDAD = re.compile(r"COMPLEJIDAD\s*=\s*(baja|media|alta)", re.IGNORECASE)
RE_FEATURE = re.compile(r"FEATURE\s*=\s*(\S+)", re.IGNORECASE)
RE_TAG_TAREA = re.compile(r"#tarea:([a-zA-Z0-9_\-]+)", re.IGNORECASE)
RE_TAG_COMPLEJIDAD = re.compile(r"#complejidad:(baja|media|alta)", re.IGNORECASE)

# Valores que aparecen en la plantilla del Orquestador y no son features reales.
# Solo los placeholders que la plantilla del Orquestador emite de verdad.
# "feature" pelado NO va: no aparece en la plantilla y descartarlo tiraba a
# sin-feature la atribucion de un docs/feature.md real.
PLACEHOLDERS_FEATURE = {
    "nombre",
    "nombre-feature",
    "nombre_feature",
    "nombre-de-la-feature",
}


# Extensiones de documento que el Explorador acepta. Solo estas se sacan del
# nombre: recortar cualquier punto destrozaria una feature llamada "v2.0".
EXTENSIONES_DOC = (".md", ".txt", ".pdf", ".docx", ".xml")


def limpiar_nombre_feature(bruto: str | None) -> str | None:
    """
    Normaliza el nombre de feature capturado de un mensaje.

    La convencion es docs/<feature>/ con el mismo nombre en los tres lugares
    (carpeta de docs, carpeta de trabajo e invocacion). Igual se normaliza la
    ruta por si alguien la tipea completa: sin esto, "docs/x/" y "x" caerian
    en buckets distintos y partirian una misma feature en dos filas del
    reporte.

    Saca backticks, comillas, corchetes, el prefijo docs/, la barra final y la
    extension de documento. Si queda una ruta con carpetas, la feature es la
    primera: docs/cambio-de-color/brief.md -> cambio-de-color.

    Devuelve None si no queda un nombre usable o si es un placeholder de la
    plantilla del Orquestador.
    """
    if not bruto:
        return None

    # RE_ORQUESTADOR y RE_DESPACHO_SUBAGENTE matchean "[feature]" tal cual
    # aparece en orquestador/SKILL.md como placeholder de sus propios
    # ejemplos (no una invocacion real) -- ya sea citado con backticks o
    # seguido de puntuacion, segun como lo repita el orquestador al
    # explicarle algo a un subagente o al IA Maker. Se descarta solo esta
    # forma literal entre corchetes -- no "feature" pelado, que si podria
    # ser el nombre real de una feature.
    bruto_normalizado = str(bruto).strip()
    for caracter in ("`", '"', "'"):
        bruto_normalizado = bruto_normalizado.replace(caracter, "")
    bruto_normalizado = bruto_normalizado.strip().rstrip(".,;:").strip()
    if bruto_normalizado.lower() == "[feature]":
        return None

    nombre = str(bruto).strip()
    for caracter in ("`", '"', "'", "[", "]"):
        nombre = nombre.replace(caracter, "")

    nombre = nombre.replace("\\", "/").strip()
    # El prefijo se saca solo si es la carpeta docs, no si el nombre empieza
    # con esas letras (docsify-upgrade queda intacto).
    nombre = re.sub(r"^docs/+", "", nombre, flags=re.IGNORECASE)
    nombre = nombre.strip("/").strip()

    # La feature es la carpeta; lo que haya adentro no cambia su nombre.
    if "/" in nombre:
        nombre = nombre.split("/", 1)[0].strip()

    # El Orquestador despacha con "...para la feature cambiocolor." y ese
    # punto cierra la oracion, no forma parte del nombre. Solo se saca al
    # final: "feature-v2.0" conserva su punto interno.
    nombre = nombre.rstrip(".,;:").strip()

    for extension in EXTENSIONES_DOC:
        if nombre.lower().endswith(extension):
            nombre = nombre[: -len(extension)].strip()
            break

    if not nombre:
        return None
    if not re.match(r"^[A-Za-z0-9]", nombre):
        return None
    if nombre.lower() in PLACEHOLDERS_FEATURE:
        return None

    return nombre


SIN_FEATURE = "sin-feature"

# La extension de VS Code expande el comando a un link Markdown hacia el
# SKILL.md, por eso el patron acepta el sufijo "](ruta)" opcional.
RE_ORQUESTADOR = re.compile(
    r"\$orquestador(?:\]\([^)]*\))?\s+(\S+)",
    re.IGNORECASE,
)

# Los subagentes corren en conversaciones propias que NO arrancan con
# $orquestador, sino con el despacho que escribe el propio Orquestador. Sin
# esto su consumo cae en sin-feature, y suele ser mayor que el del turno del
# Orquestador que los invoco.
#
# Dos formas reales observadas, con "para la feature X" como denominador:
#   Spawnea el subagente explorador para la feature cambiocolor.
#   Actua como el subagente explorador del TSOFT AI Dev Kit para la feature X.
#
# Se exige la palabra "subagente" para no confundir con una charla que
# simplemente mencione una feature.
RE_DESPACHO_SUBAGENTE = re.compile(
    r"subagente\b.{0,200}?\bpara\s+la\s+feature\s+(\S+)",
    re.IGNORECASE | re.DOTALL,
)

# Los subagentes de revision citan la conversacion completa dentro de un
# mensaje. Contar esas menciones como invocaciones produce features fantasma.
MARCADORES_TRANSCRIPT_CITADO = (
    "TRANSCRIPT START",
    "whose request action you are assessing",
)

# El primer "mensaje de usuario" de TODA conversacion de Codex (orquestador o
# subagente) no es un turno real: es el bootstrap sintetico que el propio
# Codex inyecta antes de que llegue el primer prompt de verdad (contenido
# variable -- AGENTS.md, recommended_plugins, developer_instructions -- pero
# siempre cierra con este tag). Contarlo como turno deja una fila fantasma de
# "sin-feature" con 0 tokens por cada conversacion, casi siempre un subagente.
MARCADOR_BOOTSTRAP_SESION = "<environment_context>"


def _es_bootstrap_sesion(texto: str) -> bool:
    return MARCADOR_BOOTSTRAP_SESION in texto


def _es_transcript_citado(texto: str) -> bool:
    return any(marcador in texto for marcador in MARCADORES_TRANSCRIPT_CITADO)


def _bucket_vacio() -> dict:
    return {
        "tokens": {"input": 0, "cache": 0, "output": 0, "reasoning": 0, "total": 0},
        "timestamps": [],
        "turnos": 0,
        "evidencia": _evidencia_vacia(),
        "tarea_declarada": None,
        "complejidad_declarada": None,
        # Que marcador atribuyo esta feature: "orquestador" (invocacion humana
        # explicita) o "despacho" (texto que escribio el Orquestador). Los dos
        # producen un bucket con nombre, y desde afuera se ven iguales.
        "origen": None,
    }


def cargar_eventos(ruta) -> list[dict]:
    """Carga un rollout o transcript JSONL como lista de eventos."""
    datos = _cargar_transcript(Path(ruta))
    return datos if isinstance(datos, list) else []


def leer_session_meta(eventos: list[dict]) -> dict:
    """Payload del evento session_meta, que trae cwd, modelo y originator."""
    for evento in eventos:
        if isinstance(evento, dict) and evento.get("type") == "session_meta":
            payload = evento.get("payload")
            if isinstance(payload, dict):
                return payload
    return {}


def id_conversacion(meta: dict) -> str:
    """
    Identificador propio de esta conversacion.

    En un rollout de subagente, session_meta trae DOS ids distintos: `id` es el
    thread propio, y `session_id` es el de la sesion a la que pertenece -- o
    sea, el del padre, identico a parent_thread_id. Usar `session_id` como
    identificador propio hace que el hijo colisione con su padre.
    """
    if not isinstance(meta, dict):
        return ""
    return str(meta.get("id") or meta.get("session_id") or "")


def detectar_modelo(eventos: list[dict], meta: dict) -> str:
    """
    Modelo usado en la conversacion, para tarifar el rollout completo.

    session_meta no expone el modelo; vive en los eventos turn_context. Se
    prefiere igual la clave de session_meta por si una version futura de
    Codex la agrega. Devuelve el primer modelo visto: ver detectar_modelos
    para el caso (raro hoy, no imposible) de que la conversacion cambie de
    modelo a mitad de camino.
    """
    if (meta or {}).get("model"):
        return str(meta["model"])
    for evento in eventos:
        if not isinstance(evento, dict) or evento.get("type") != "turn_context":
            continue
        payload = evento.get("payload")
        if isinstance(payload, dict) and payload.get("model"):
            return str(payload["model"])
    return ""


def detectar_modelos(eventos: list[dict]) -> list[str]:
    """
    Todos los modelos distintos vistos en los eventos turn_context del
    rollout, en el orden en que aparecen.

    construir_registros tarifa el rollout entero con un solo modelo (el
    primero, ver detectar_modelo) porque hoy ningun rollout del proyecto usa
    mas de uno. Esta funcion existe para poder detectar y avisar cuando esa
    aproximacion deja de ser exacta.
    """
    modelos: list[str] = []
    for evento in eventos:
        if not isinstance(evento, dict) or evento.get("type") != "turn_context":
            continue
        payload = evento.get("payload")
        if not isinstance(payload, dict):
            continue
        modelo = payload.get("model")
        if modelo and str(modelo) not in modelos:
            modelos.append(str(modelo))
    return modelos


def extraer_cuota(eventos: list[dict]) -> dict | None:
    """
    Consumo de la cuota semanal segun lo que reporta Codex.

    En los planes por suscripcion (team, plus) no se paga por token: el limite
    real es una cuota con ventana movil de 7 dias, y llegar al 100% bloquea el
    trabajo hasta que la ventana se reinicia. Codex publica el porcentaje usado
    en cada evento token_count, dentro de rate_limits.primary.used_percent.

    Devuelve inicial, final, pico y consumida (final - inicial). Como la
    ventana es movil, el porcentaje puede bajar solo; en ese caso "consumida"
    queda en cero en vez de negativo.

    Devuelve None si el rollout no trae ninguna lectura.
    """
    lecturas = []
    plan = None

    for evento in eventos:
        if not isinstance(evento, dict) or evento.get("type") != "event_msg":
            continue
        payload = evento.get("payload")
        if not isinstance(payload, dict) or payload.get("type") != "token_count":
            continue

        limites = payload.get("rate_limits")
        if not isinstance(limites, dict):
            continue
        primary = limites.get("primary")
        if not isinstance(primary, dict):
            continue

        pct = primary.get("used_percent")
        if isinstance(pct, (int, float)):
            lecturas.append(float(pct))
            plan = plan or limites.get("plan_type")

    if not lecturas:
        return None

    return {
        "inicial": lecturas[0],
        "final": lecturas[-1],
        "pico": max(lecturas),
        "consumida": round(max(0.0, lecturas[-1] - lecturas[0]), 2),
        "plan": plan,
    }


def _texto_usuario(evento: dict) -> str | None:
    """
    Texto del mensaje del usuario, en cualquiera de los dos formatos de rollout.

    La extension de VS Code escribe `event_msg / user_message` con el texto en
    `payload.message`. La CLI NO escribe ese evento: el prompt vive en
    `response_item / message` con `role: "user"` y el texto dentro de
    `payload.content[].input_text`.

    Verificado contra Codex 0.149.1. Sin esto, en CLI no se cuentan turnos y,
    peor, nunca se ve la invocacion `$orquestador`: toda la sesion cae en
    sin-feature.
    """
    if not isinstance(evento, dict):
        return None
    payload = evento.get("payload")
    if not isinstance(payload, dict):
        return None

    if evento.get("type") == "event_msg" and payload.get("type") == "user_message":
        return payload.get("message") or ""

    if evento.get("type") == "response_item" and payload.get("type") == "message":
        if payload.get("role") != "user":
            return None
        partes = []
        for bloque in payload.get("content") or []:
            if isinstance(bloque, dict) and bloque.get("type") in ("input_text", "text"):
                partes.append(bloque.get("text") or "")
        return "\n".join(partes)

    return None


def _hay_user_message(eventos: list[dict]) -> bool:
    """True si el rollout trae eventos user_message propios (formato VS Code)."""
    for evento in eventos:
        if not isinstance(evento, dict) or evento.get("type") != "event_msg":
            continue
        payload = evento.get("payload")
        if isinstance(payload, dict) and payload.get("type") == "user_message":
            return True
    return False


def _guardar_clasificacion_declarada(mensaje: str, bucket: dict) -> None:
    """Conserva las etiquetas del rollout con la misma semantica que el hook."""
    match = RE_TAG_TAREA.search(mensaje)
    if match:
        bucket["tarea_declarada"] = match.group(1).lower()

    match = RE_TAG_COMPLEJIDAD.search(mensaje)
    if match:
        bucket["complejidad_declarada"] = match.group(1).lower()


def segmentar_por_feature(eventos: list[dict]) -> dict:
    """
    Recorre el rollout hacia adelante y acumula last_token_usage en el bucket
    de la feature activa.

    Distinto de _extraer_tokens_jsonl, que camina hacia atras y devuelve el
    total_token_usage acumulado del archivo entero. Ese acumulado no permite
    separar features dentro de una misma conversacion; los deltas por turno si.

    Los turnos previos a cualquier invocacion quedan en SIN_FEATURE, para no
    perder visibilidad del gasto total.

    La evidencia tecnica (archivos, comandos, subagentes) se acumula en el bucket
    de la feature activa en ese punto del recorrido. Antes se calculaba sobre el
    archivo entero y las dos features de una misma conversacion terminaban
    declarando los mismos archivos.
    """
    buckets: dict[str, dict] = {}
    activa = SIN_FEATURE
    total_previo = None  # acumulado del ultimo token_count considerado

    # Los rollouts de VS Code traen los dos formatos de mensaje de usuario;
    # los de CLI, solo response_item. Se prefiere user_message cuando existe
    # para no contar el mismo turno dos veces.
    usar_response_item = not _hay_user_message(eventos)

    for evento in eventos:
        if not isinstance(evento, dict):
            continue
        payload = evento.get("payload")
        if not isinstance(payload, dict):
            continue

        es_event_msg = evento.get("type") == "event_msg"
        tipo = payload.get("type")

        es_mensaje_usuario = (
            (es_event_msg and tipo == "user_message")
            or (usar_response_item
                and evento.get("type") == "response_item"
                and tipo == "message"
                and payload.get("role") == "user")
        )

        if es_mensaje_usuario:
            mensaje = _texto_usuario(evento) or ""
            if _es_transcript_citado(mensaje):
                continue
            if _es_bootstrap_sesion(mensaje):
                continue
            # El $orquestador manda: es la invocacion humana explicita. El
            # despacho a un subagente es la senal de respaldo, para las
            # conversaciones que abre el propio Orquestador.
            marcador = None
            match = RE_ORQUESTADOR.search(mensaje)
            if match:
                marcador = "orquestador"
            else:
                match = RE_DESPACHO_SUBAGENTE.search(mensaje)
                if match:
                    marcador = "despacho"

            if match:
                nombre = limpiar_nombre_feature(match.group(1))
                if nombre:
                    activa = nombre
                    buckets.setdefault(activa, _bucket_vacio())["origen"] = marcador
            bucket = buckets.setdefault(activa, _bucket_vacio())
            _guardar_clasificacion_declarada(mensaje, bucket)
            bucket["turnos"] += 1
            continue

        if es_event_msg and tipo == "token_count":
            info = payload.get("info")
            if not isinstance(info, dict):
                continue
            bruto = info.get("last_token_usage")
            if not isinstance(bruto, dict):
                continue

            # Algunos rollouts repiten un token_count con el mismo acumulado.
            # Si total_token_usage no cambio, el evento no reporta consumo
            # nuevo y sumar su last_token_usage duplicaria ese turno.
            bruto_total = info.get("total_token_usage")
            acumulado = bruto_total.get("total_tokens") if isinstance(bruto_total, dict) else None
            if acumulado is not None:
                if total_previo is not None and acumulado == total_previo:
                    continue
                total_previo = acumulado

            uso = _normalizar_uso(bruto)
            bucket = buckets.setdefault(activa, _bucket_vacio())
            for clave, valor in uso.items():
                bucket["tokens"][clave] = bucket["tokens"].get(clave, 0) + valor

            marca = epoch_de_evento(evento)
            if marca is not None:
                bucket["timestamps"].append(marca)
            continue

        acumular_evidencia(evento, buckets.setdefault(activa, _bucket_vacio())["evidencia"])

    # Un bucket que solo junto evidencia, sin turnos ni tokens, no representa
    # consumo: aparece cuando el rollout trae eventos tecnicos antes del primer
    # mensaje del usuario. No merece un registro propio.
    return {
        nombre: bucket
        for nombre, bucket in buckets.items()
        if bucket["turnos"] or any(bucket["tokens"].values())
    }


def clasificar_tarea(estado: dict, baselines: dict) -> tuple[str, str, str]:
    """
    Devuelve (tipo, complejidad, origen).
    origen: 'declarado' | 'inferido' | 'default'
    """
    tipo = estado.get("tarea_declarada")
    complejidad = estado.get("complejidad_declarada")

    if tipo and complejidad:
        return tipo, complejidad, "declarado"

    if not tipo:
        archivos = estado.get("archivos_tocados", [])
        patrones_back = re.compile(
            r"(src/)?(api|server|backend|services?|controllers?|repositor(y|ies)|domain|infrastructure|migrations?)(/|$)",
            re.IGNORECASE,
        )
        patrones_front = re.compile(
            r"(src/)?(components?|pages?|views?|hooks?|stores?|styles?|assets)(/|$)|\.(tsx|jsx|vue|svelte|scss|css)$",
            re.IGNORECASE,
        )

        tiene_back = any(patrones_back.search(archivo) for archivo in archivos)
        tiene_front = any(patrones_front.search(archivo) for archivo in archivos)

        if tiene_back and tiene_front:
            tipo = "evolutivo-fullstack"
        elif tiene_back:
            tipo = "evolutivo-backend"
        elif tiene_front:
            tipo = "evolutivo-frontend"

    if not complejidad:
        ediciones = estado.get("ediciones", 0)
        umbrales = baselines.get("umbrales_complejidad", {"media": 4, "alta": 12})
        if ediciones >= umbrales.get("alta", 12):
            complejidad = "alta"
        elif ediciones >= umbrales.get("media", 4):
            complejidad = "media"
        else:
            complejidad = "baja"

    if tipo and complejidad:
        return tipo, complejidad, "inferido"

    tipo_default = baselines.get("tipo_default", "mantenimiento-correctivo")
    return tipo_default, complejidad or "baja", "default"


def clasificacion_normalizada(estado: dict, baselines: dict) -> dict:
    """Clasificacion del registro, separando origen de tipo y complejidad."""
    tipo, complejidad, origen = clasificar_tarea(estado, baselines)

    if estado.get("tarea_declarada"):
        origen_tipo = "declarado"
    elif origen == "default":
        origen_tipo = "default"
    else:
        origen_tipo = "inferido"

    origen_complejidad = "declarado" if estado.get("complejidad_declarada") else "inferido"

    # Una etiqueta #tarea: mal escrita ("evolutivo" en vez de
    # "evolutivo-frontend") no es uno de los nueve tipos validos. No cambia
    # el calculo de nada (tipo/complejidad son metadato descriptivo, no
    # entran en ninguna formula de horas), pero vale avisarlo: es la unica
    # señal de que alguien escribio mal la etiqueta del prompt.
    tipos_validos = baselines.get("tipos_validos", [])
    tipo_reconocido = tipo in tipos_validos if tipos_validos else True

    return {
        "tipo_tarea": tipo,
        "complejidad": complejidad,
        "origen": origen,
        "origen_tipo": origen_tipo,
        "origen_complejidad": origen_complejidad,
        "tipo_reconocido": tipo_reconocido,
    }


def duracion_sesion(estado: dict) -> dict:
    """
    Duracion real de la sesion en horas, con guarda de confiabilidad.

    inicio_epoch falta si el estado de la sesion se corrompio o se perdio
    entre SessionStart y Stop (no es el camino normal: session_start.py
    siempre lo fija). Sin esta guarda, inicio caeria a epoch 0 y dur_h se
    dispararia a cientos de miles de horas sin que nadie lo note.
    """
    inicio = estado.get("inicio_epoch")
    fin = estado.get("fin_epoch", time.time())
    duracion_confiable = inicio is not None
    dur_h = (fin - inicio) / 3600 if duracion_confiable else 0.0

    return {
        "duracion_h": round(dur_h, 2),
        "duracion_confiable": duracion_confiable,
    }
def epoch_iso(texto) -> float | None:
    """Fecha ISO a epoch. None si no se puede parsear."""
    if not texto:
        return None
    try:
        return datetime.fromisoformat(str(texto).replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def epoch_de_evento(evento: dict) -> float | None:
    """Convierte el campo timestamp ISO de un evento de rollout a epoch."""
    if not isinstance(evento, dict):
        return None
    return epoch_iso(evento.get("timestamp"))


# Alias de rol observados en rollouts reales. Se mapea SOLO lo que es
# inequivocamente el mismo rol en otro idioma: el kit se instalo en proyectos
# con los agentes nombrados en ingles.
#
# "worker", "default" y "guardian" NO se mapean a proposito. Son genericos, y
# asumir que "worker" es el Desarrollador seria inventar un dato que el runtime
# no declara.
ALIAS_ROLES = {
    "explorer": "explorador",
}

# La conversacion principal no trae agent_role: ahi vive el Orquestador y las
# aprobaciones humanas. Es una etapa del flujo con costo propio -- unos 118.000
# tokens por intercambio humano -- asi que necesita nombre para poder medirla.
ETAPA_PRINCIPAL = "orquestador"

# Un subagente que no declara rol -- la variante {"subagent": {"other": ...}} --
# no es la conversacion principal. Mezclarlo con el Orquestador contaminaria la
# fila que mide el costo del Human in the Loop.
ETAPA_SUBAGENTE_SIN_ROL = "subagente-sin-rol"


def normalizar_rol(rol) -> str | None:
    """Rol del subagente en su forma canonica. Los desconocidos pasan tal cual."""
    if not isinstance(rol, str):
        return None
    limpio = rol.strip().lower()
    if not limpio:
        return None
    return ALIAS_ROLES.get(limpio, limpio)


def leer_spawn_subagente(meta: dict) -> dict:
    """
    Datos del subagente que el runtime declara en session_meta.

    Codex escribe en source.subagent.thread_spawn quien lanzo esta
    conversacion y con que rol. Es el mismo dato que traeria el hook
    SubagentStart, pero en el rollout -- que se escribe siempre, sin depender
    de cliente, version ni confianza.

    Devuelve las cinco claves siempre, en None si el rollout no es de un
    subagente, para que quien llame no tenga que distinguir los casos.
    """
    vacio = {"padre": None, "rol": None, "apodo": None, "depth": None, "es_subagente": False}

    if not isinstance(meta, dict):
        return vacio

    # La mayoria de los rollouts trae source como string: "vscode" o "cli".
    src = meta.get("source")
    if not isinstance(src, dict):
        return vacio

    sub = src.get("subagent")
    if not isinstance(sub, dict):
        return vacio

    # Si llegamos aqui, es un subagente (aunque sea sin thread_spawn)
    result = vacio.copy()
    result["es_subagente"] = True

    # Variante real observada sin thread_spawn: {"subagent": {"other": "guardian"}}
    spawn = sub.get("thread_spawn")
    if not isinstance(spawn, dict):
        return result

    depth = spawn.get("depth")
    return {
        "padre": spawn.get("parent_thread_id") or None,
        "rol": normalizar_rol(spawn.get("agent_role")),
        "apodo": spawn.get("agent_nickname") or None,
        "depth": depth if isinstance(depth, int) else None,
        "es_subagente": True,
    }



def tiempo_activo(timestamps: list[float], umbral_min: int = 30) -> float:
    """
    Horas de trabajo real: suma los intervalos entre eventos consecutivos
    descartando los huecos mayores al umbral.

    Una feature retomada al otro dia no consumio las horas intermedias.
    """
    marcas = sorted(marca for marca in timestamps if marca is not None)
    if len(marcas) < 2:
        return 0.0

    umbral_seg = umbral_min * 60
    total = 0.0
    for anterior, siguiente in zip(marcas, marcas[1:]):
        delta = siguiente - anterior
        if 0 < delta <= umbral_seg:
            total += delta

    return round(total / 3600, 4)


def tiempo_pared(timestamps: list[float]) -> float:
    """Horas entre el primer y el ultimo evento, huecos incluidos."""
    marcas = sorted(marca for marca in timestamps if marca is not None)
    if len(marcas) < 2:
        return 0.0
    return round((marcas[-1] - marcas[0]) / 3600, 4)


# --- Periodos de reporte ---------------------------------------------------
#
# Vive aca porque lo usan los dos generadores de reportes. Si cada uno definiera
# su propia "semana", el reporte Markdown y el HTML del mismo viernes darian
# numeros distintos, y nadie sabria a cual creerle.

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    TZ_LOCAL = ZoneInfo("America/Argentina/Buenos_Aires")
except Exception:  # tzdata ausente: se cae a la zona del sistema
    TZ_LOCAL = datetime.now().astimezone().tzinfo


def parse_iso(valor: str | None) -> datetime | None:
    """Fecha ISO de features.jsonl (en UTC) convertida a la zona local."""
    if not valor:
        return None
    try:
        return datetime.fromisoformat(valor.replace("Z", "+00:00")).astimezone(TZ_LOCAL)
    except Exception:
        return None


def parse_fecha(valor: str | None) -> date:
    """Fecha YYYY-MM-DD; sin valor, hoy en la zona local."""
    if not valor:
        return datetime.now(TZ_LOCAL).date()
    return date.fromisoformat(valor)


def fecha_referencia(registro: dict) -> datetime | None:
    """
    Fecha con la que un registro cae en un periodo.

    Se usa el fin del tramo: es cuando el consumo ya ocurrido quedo cerrado.
    """
    return parse_iso(registro.get("fin")) or parse_iso(registro.get("inicio"))


def periodo_diario(fecha_base: date) -> tuple[date, date, str]:
    return fecha_base, fecha_base, f"Diario {fecha_base.isoformat()}"


def periodo_semanal(fecha_base: date) -> tuple[date, date, str]:
    """Los siete dias que cierran en fecha_base, ella incluida."""
    inicio = fecha_base - timedelta(days=6)
    return inicio, fecha_base, f"Semanal {inicio.isoformat()} a {fecha_base.isoformat()}"


def filtrar_periodo(registros: list[dict], desde: date, hasta: date) -> list[dict]:
    """Registros cuya fecha de referencia cae en [desde, hasta], ordenados."""
    seleccionados = []
    for registro in registros:
        referencia = fecha_referencia(registro)
        if not referencia:
            continue
        if desde <= referencia.date() <= hasta:
            seleccionados.append(registro)
    seleccionados.sort(
        key=lambda item: fecha_referencia(item) or datetime.min.replace(tzinfo=TZ_LOCAL)
    )
    return seleccionados


def leer_stdin_json() -> dict:
    import sys

    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def salir_ok(payload: dict | None = None) -> None:
    import sys

    print(json.dumps(payload or {}, ensure_ascii=False))
    sys.exit(0)
