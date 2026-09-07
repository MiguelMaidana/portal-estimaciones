"""
reconciliador.py - Reconstruye el consumo por feature desde los rollouts.

Codex escribe un rollout JSONL por conversacion en ~/.codex/sessions/,
independientemente de si los hooks dispararon. En la extension de VS Code los
hooks no siempre corren, asi que el ledger queda incompleto; los rollouts no.

Este modulo los lee, filtra los del proyecto, segmenta el consumo por feature
y escribe tsoft-dev/metrics/features.jsonl.

No modifica ledger.jsonl ni los archivos de sesiones: la medicion por hooks en
CLI sigue funcionando igual.

Uso:
  py tsoft-dev/scripts/reconciliador.py
  py tsoft-dev/scripts/reconciliador.py --raiz-sesiones "D:/otra/ruta"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics_lib as ml


def raiz_sesiones() -> Path:
    """
    Carpeta donde Codex deja los rollouts de cada conversacion.

    Codex mismo respeta CODEX_HOME cuando esta seteada -- lo hacen, por
    ejemplo, herramientas de orquestacion (Orca) que redirigen el home de
    Codex para poder leer la transcripcion de los agentes que lanzan. Si
    este modulo ignora esa variable, busca en ~/.codex/sessions mientras
    los rollouts reales quedan en otro lado: Registros: 0 sin ningun error,
    porque la carpeta que mira simplemente no tiene nada nuevo.
    """
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home) / "sessions"
    return Path.home() / ".codex" / "sessions"


def listar_rollouts(raiz: Path) -> list[Path]:
    """Todos los rollouts bajo la raiz, ordenados por ruta."""
    raiz = Path(raiz)
    if not raiz.exists():
        return []
    return sorted(raiz.rglob("rollout-*.jsonl"))


def leer_session_meta(eventos: list[dict]) -> dict:
    """
    Delega en metrics_lib: todo el conocimiento del formato de rollout de
    Codex (claves, tipos de evento) vive ahi. Se mantiene este wrapper porque
    los tests existentes importan reconciliador.leer_session_meta.
    """
    return ml.leer_session_meta(eventos)


def pertenece_al_proyecto(meta: dict, raiz_proyecto: Path) -> bool:
    """
    True si el rollout se grabo trabajando en este proyecto o en una
    subcarpeta de el (por ejemplo, un desarrollador que hizo cd a
    tsoft-dev/ antes de abrir Codex). Esto es una decision de politica de
    paths, no de formato de rollout, por eso vive aca y no en metrics_lib.

    Usa normcase porque en Windows los paths no distinguen mayusculas y los
    rollouts guardan el drive en minuscula ("c:\\Users\\..."). La
    comparacion de subcarpeta exige que el separador de path aparezca justo
    despues de la raiz del proyecto, para no confundir un directorio
    hermano que solo comparte el prefijo del nombre (".../tsoft-ai-portal-
    backup" no debe matchear ".../tsoft-ai-portal").
    """
    cwd = (meta or {}).get("cwd")
    if not cwd:
        return False
    try:
        propio = os.path.normcase(str(Path(cwd).resolve()))
        objetivo = os.path.normcase(str(Path(raiz_proyecto).resolve()))
        return propio == objetivo or propio.startswith(objetivo + os.sep)
    except Exception:
        return False


def detectar_modelo(eventos: list[dict], meta: dict) -> str:
    """
    Delega en metrics_lib: todo el conocimiento del formato de rollout de
    Codex vive ahi. Se mantiene este wrapper porque los tests existentes
    importan reconciliador.detectar_modelo.
    """
    return ml.detectar_modelo(eventos, meta)


def detectar_developer(raiz_proyecto: Path | None = None) -> str:
    """
    Email del dev segun git. Identidad de maquina, no auditada: sirve para
    consolidar los reportes que cada uno genera y envia.

    Corre con cwd fijado en la raiz del proyecto: sin eso, subprocess.run
    hereda el cwd del proceso que lanzo el reconciliador y, si ese proceso
    esta parado en otro repo, resuelve la identidad git de ese otro repo.
    """
    try:
        salida = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(raiz_proyecto) if raiz_proyecto else None,
        )
        email = (salida.stdout or "").strip()
        return email or "desconocido"
    except Exception:
        return "desconocido"


RE_ESTADO_FEATURE = re.compile(r"Estado general:\s*(.+)", re.IGNORECASE)


def ruta_features(raiz_proyecto: Path) -> Path:
    destino = Path(raiz_proyecto) / "tsoft-dev" / "metrics" / "features.jsonl"
    destino.parent.mkdir(parents=True, exist_ok=True)
    return destino


def _iso(epoch: float | None) -> str | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def leer_estado_feature(raiz_proyecto: Path, feature: str) -> str:
    """
    Estado declarado por el Orquestador en tsoft-dev/[feature]/orquestador-estado.md.

    Es la unica senal de cierre confiable: la linea TAREA/COMPLEJIDAD/FEATURE
    se escribe en todos los cierres, se pause o se continue el flujo.
    """
    ruta = Path(raiz_proyecto) / "tsoft-dev" / feature / "orquestador-estado.md"
    if not ruta.exists():
        return "desconocido"
    try:
        texto = ruta.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return "desconocido"
    match = RE_ESTADO_FEATURE.search(texto)
    if not match:
        return "desconocido"
    return match.group(1).strip().lower()


# Carpetas propias del kit dentro de tsoft-dev/: nunca son features.
CARPETAS_NO_FEATURE = {"scripts", "metrics", "reportes", "config"}

RE_CARPETA_FEATURE = re.compile(r"tsoft-dev[/\\]([^/\\]+)[/\\]", re.IGNORECASE)


def feature_desde_evidencia(archivos_tocados) -> str | None:
    """
    Deduce la feature a partir de las carpetas donde la conversacion escribio.

    Es el respaldo para cuando no hubo marcador de texto. Cualquier etapa del
    flujo escribe en tsoft-dev/<feature>/ -- explorador-output.md, design.md,
    feature-doc.md, qa.md, orquestador-estado.md -- asi que la carpeta es una
    senal de lo que la conversacion HIZO, independiente de como se redacto el
    prompt que la inicio.

    Devuelve None si no hay candidata o si hay mas de una: ante la duda es
    preferible dejarlo en sin-feature antes que atribuir mal.
    """
    candidatas = set()

    for ruta in archivos_tocados or []:
        match = RE_CARPETA_FEATURE.search(str(ruta))
        if not match:
            continue
        carpeta = match.group(1)
        if carpeta.lower() in CARPETAS_NO_FEATURE:
            continue
        # Se normaliza igual que los nombres detectados por texto, para que
        # la carpeta feature-cambios.md caiga en el bucket feature-cambios.
        nombre = ml.limpiar_nombre_feature(carpeta)
        if nombre:
            candidatas.add(nombre)

    return candidatas.pop() if len(candidatas) == 1 else None



def construir_indice(rollouts) -> dict:
    """
    session_id -> datos del grafo, para resolver la feature de los subagentes.

    Se construye con TODOS los rollouts, sin filtrar por proyecto. Si se
    filtrara antes, un padre que quedo fuera del filtro cortaria la cadena de
    su hijo y el consumo del subagente volveria a caer en sin-feature.

    De cada feature se guarda solo (nombre, epoch) y no el bucket completo:
    los buckets traen la evidencia entera -- archivos y comandos de cada
    conversacion -- y retenerla para todos los rollouts a la vez no hace
    falta. construir_registros la recalcula para el rollout que procesa.
    """
    indice = {}

    for rollout in rollouts:
        try:
            eventos = ml.cargar_eventos(rollout)
            if not eventos:
                continue

            meta = ml.leer_session_meta(eventos)
            session_id = ml.id_conversacion(meta)
            if not session_id:
                continue

            spawn = ml.leer_spawn_subagente(meta)

            features = []
            for nombre, bucket in ml.segmentar_por_feature(eventos).items():
                if nombre == ml.SIN_FEATURE:
                    continue
                marcas = bucket.get("timestamps") or []
                features.append((nombre, min(marcas) if marcas else None))
            # Ordenadas por inicio, con las que no tienen marca al final: la
            # resolucion por momento de nacimiento depende de este orden.
            features.sort(key=lambda par: (par[1] is None, par[1]))

            indice[session_id] = {
                "padre": spawn["padre"],
                "rol": spawn["rol"],
                "apodo": spawn["apodo"],
                "depth": spawn["depth"],
                "inicio": ml.epoch_iso(meta.get("timestamp")),
                "features": features,
            }
        except Exception as exc:
            print(f"  aviso: no se pudo indexar {rollout.name}: {exc}", file=sys.stderr)

    return indice


def feature_activa_en(nodo: dict, momento) -> tuple:
    """
    La feature del nodo vigente en `momento`. Devuelve (feature, aproximada).

    Se toma la ultima cuyo inicio es anterior o igual. Si ninguna lo precede,
    o si no hay con que comparar, se devuelve la primera marcada como
    aproximada, para que el registro quede auditable en vez de silenciosamente
    dudoso.
    """
    features = (nodo or {}).get("features") or []
    if not features:
        return None, False

    if momento is not None:
        # features viene ordenada por epoch desde construir_indice.
        anteriores = [nombre for nombre, epoch in features
                      if epoch is not None and epoch <= momento]
        if anteriores:
            return anteriores[-1], False

    return features[0][0], True


def resolver_por_grafo(session_id: str, indice: dict) -> tuple:
    """
    Feature de una conversacion subiendo por parent_thread_id.

    Devuelve (feature, aproximada), o (None, False) si no resuelve.

    El subagente hereda la feature ACTIVA EN EL PADRE al momento de nacer, no
    la primera del padre. Hay un caso real de una conversacion que toco tres
    features y lanzo cuatro subagentes: con "la primera" los cuatro se
    atribuyen mal, los totales cierran igual, y el error queda invisible.
    """
    nodo_hijo = indice.get(session_id)
    if not nodo_hijo:
        return None, False

    nacimiento = nodo_hijo.get("inicio")
    visitados = {session_id}
    padre_id = nodo_hijo.get("padre")

    while padre_id and padre_id not in visitados:
        visitados.add(padre_id)
        padre = indice.get(padre_id)
        if not padre:
            return None, False          # padre ausente del disco

        feature, aproximada = feature_activa_en(padre, nacimiento)
        if feature:
            return feature, aproximada

        padre_id = padre.get("padre")   # depth > 1: se sigue subiendo

    return None, False


def etapa_de(spawn: dict) -> str:
    """
    La etapa del flujo a la que pertenece esta conversacion.

    Un subagente sin rol declarado NO es la conversacion principal: si cayera
    en `orquestador` mezclaria su consumo con el de las aprobaciones humanas,
    que es justamente lo que la etapa `orquestador` existe para medir.
    """
    if spawn.get("rol"):
        return spawn["rol"]
    if spawn.get("es_subagente"):
        return ml.ETAPA_SUBAGENTE_SIN_ROL
    return ml.ETAPA_PRINCIPAL


def construir_registros(
    rollout: Path,
    raiz_proyecto: Path,
    config: dict,
    developer: str,
    indice: dict | None = None,
    baselines: dict | None = None,
) -> list[dict]:
    """Un registro por cada feature presente en el rollout. Lista vacia si no es del proyecto."""
    eventos = ml.cargar_eventos(rollout)
    if not eventos:
        return []

    meta = ml.leer_session_meta(eventos)
    if not pertenece_al_proyecto(meta, raiz_proyecto):
        return []

    if baselines is None:
        try:
            baselines = ml.cargar_baselines(raiz_proyecto)
        except FileNotFoundError:
            baselines = ml.cargar_baselines()
    buckets = ml.segmentar_por_feature(eventos)
    if not buckets:
        return []

    modelo = ml.detectar_modelo(eventos, meta)
    modelos_detectados = ml.detectar_modelos(eventos)
    modelos_multiples = len(modelos_detectados) > 1
    umbral = config.get("umbral_inactividad_min", 30)
    cuota = ml.extraer_cuota(eventos)

    spawn = ml.leer_spawn_subagente(meta)
    session_id = ml.id_conversacion(meta)

    # Precedencia de atribucion, de mas exacta a mas inferida. Los niveles 3 y
    # 4 son los mecanismos de v1: cubren el 12% de conversaciones de subagente
    # que el grafo no alcanza, y la conversacion principal, que no es hija de
    # nadie. Borrarlos seria perder cobertura ya conseguida.
    origen_atribucion = "ninguno"
    aproximada = False

    if list(buckets.keys()) != [ml.SIN_FEATURE]:
        # 1 y 3. El marcador de texto ya resolvio adentro de
        # segmentar_por_feature, y el bucket declara cual fue.
        primera = next(n for n in buckets if n != ml.SIN_FEATURE)
        origen_atribucion = buckets[primera].get("origen") or "orquestador"
    else:
        # 2. El grafo: el runtime declara de quien nacio esta conversacion.
        del_grafo, aproximada = resolver_por_grafo(session_id, indice or {})
        if del_grafo:
            buckets = {del_grafo: buckets[ml.SIN_FEATURE]}
            origen_atribucion = "grafo"
        else:
            # 4. La carpeta que la conversacion escribio.
            archivos = buckets[ml.SIN_FEATURE]["evidencia"].get("archivos_tocados")
            deducida = feature_desde_evidencia(archivos)
            if deducida:
                buckets = {deducida: buckets[ml.SIN_FEATURE]}
                origen_atribucion = "carpeta"

    registros = []
    for feature, bucket in buckets.items():
        marcas = bucket["timestamps"]
        estado_clasificacion = {
            "tarea_declarada": bucket.get("tarea_declarada"),
            "complejidad_declarada": bucket.get("complejidad_declarada"),
            "archivos_tocados": bucket["evidencia"].get("archivos_tocados", []),
            "ediciones": bucket["evidencia"].get("ediciones", 0),
        }
        clasificacion = ml.clasificacion_normalizada(estado_clasificacion, baselines)
        registros.append({
            "feature": feature,
            "estado": leer_estado_feature(raiz_proyecto, feature),
            "developer": developer,
            "session_id": session_id,
            "rollout": rollout.name,
            "origen": meta.get("originator") or "",
            "modelo": modelo,
            "modelos_multiples": modelos_multiples,
            "modelos_detectados": modelos_detectados,
            "inicio": _iso(min(marcas)) if marcas else None,
            "fin": _iso(max(marcas)) if marcas else None,
            "tiempo_activo_h": ml.tiempo_activo(marcas, umbral_min=umbral),
            "tiempo_pared_h": ml.tiempo_pared(marcas),
            "turnos": bucket["turnos"],
            "tokens": bucket["tokens"],
            "costo": ml.costo_usd(bucket["tokens"], modelo, config),
            # La cuota es de la CONVERSACION, no de la feature: si una
            # conversacion toco dos features, las dos llevan el mismo valor.
            # Por eso los reportes muestran el pico del periodo y nunca la
            # suma, que contaria dos veces la misma conversacion.
            "cuota": cuota,
            # Evidencia de ESTA feature, no de la conversacion: si un rollout
            # toco dos features, cada una declara solo lo que produjo.
            "evidencia": bucket["evidencia"],
            "tipo_tarea": clasificacion["tipo_tarea"],
            "complejidad": clasificacion["complejidad"],
            "origen_tipo": clasificacion["origen_tipo"],
            "origen_complejidad": clasificacion["origen_complejidad"],
            # La etapa del flujo. El rol lo declara el runtime; la conversacion
            # principal no tiene rol porque ahi vive el Orquestador.
            "etapa": etapa_de(spawn),
            # Cual de los mecanismos atribuyo este registro. Permite auditar
            # cuanto del reporte es dato exacto y cuanto inferencia.
            "origen_atribucion": ("grafo-aproximado"
                                  if origen_atribucion == "grafo" and aproximada
                                  else origen_atribucion),
            "parent_session_id": spawn["padre"],
        })

    return registros


def escribir_features(
    registros: list[dict], raiz_proyecto: Path, permitir_vacio: bool = False
) -> Path:
    """
    Reescribe features.jsonl completo.

    Los rollouts son inmutables, asi que el archivo se regenera desde cero
    en cada corrida -- correr dos veces no duplica nada. Pero "cero
    registros" no siempre significa "no hay nada que medir": tambien pasa
    si la raiz de sesiones esta vacia o mal apuntada (CODEX_HOME, sesiones
    purgadas, cwd equivocado). Abrir en "w" incondicional en ese caso
    borraba un historico real y dejaba el reporte siguiente mostrando "0"
    como si fuera la verdad -- "no encontre nada" no es lo mismo que "la
    verdad es cero". Por eso, si da cero registros y ya habia contenido
    previo, se preserva el archivo (permitir_vacio=True lo fuerza a
    vaciarse igual, para cuando de verdad hace falta).

    Escribe primero a un temporal y reemplaza con os.replace (atomico en
    Windows y POSIX): una corrida interrumpida a la mitad no deja el
    archivo truncado.
    """
    destino = ruta_features(raiz_proyecto)

    if not registros and not permitir_vacio and destino.exists() and destino.stat().st_size > 0:
        print(
            f"aviso: 0 registros nuevos y {destino.name} ya tenia contenido -- "
            "se preserva el archivo anterior en vez de vaciarlo. Revisa "
            "CODEX_HOME o la raiz de sesiones si esperabas datos nuevos, o "
            "corre con --permitir-vacio si de verdad queres regenerarlo vacio.",
            file=sys.stderr,
        )
        return destino

    tmp = destino.with_suffix(f".{os.getpid()}.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for registro in registros:
            fh.write(json.dumps(registro, ensure_ascii=False) + "\n")
    os.replace(tmp, destino)
    return destino


def reconciliar(
    raiz_proyecto: Path | None = None,
    origen_sesiones: Path | None = None,
    permitir_vacio: bool = False,
):
    """Escanea todos los rollouts y regenera features.jsonl. Devuelve (ruta, registros)."""
    raiz_proyecto = Path(raiz_proyecto) if raiz_proyecto else ml.raiz_kit()
    origen = Path(origen_sesiones) if origen_sesiones else raiz_sesiones()

    config = ml.cargar_config(raiz_proyecto)
    baselines = ml.cargar_baselines(raiz_proyecto)
    developer = detectar_developer(raiz_proyecto)

    rollouts = listar_rollouts(origen)

    # Primera pasada: el grafo de quien lanzo a quien. Se construye con todos
    # los rollouts, sin filtrar por proyecto, porque un padre fuera del filtro
    # cortaria la cadena de su hijo.
    indice = construir_indice(rollouts)

    registros = []
    for rollout in rollouts:
        try:
            registros.extend(
                construir_registros(rollout, raiz_proyecto, config, developer, indice, baselines)
            )
        except Exception as exc:
            print(f"  aviso: no se pudo procesar {rollout.name}: {exc}", file=sys.stderr)

    destino = escribir_features(registros, raiz_proyecto, permitir_vacio=permitir_vacio)
    return destino, registros


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reconcilia consumo por feature desde rollouts")
    parser.add_argument("--raiz-sesiones", default=None, help="Ruta alternativa a ~/.codex/sessions")
    parser.add_argument(
        "--permitir-vacio",
        action="store_true",
        help="Vacia features.jsonl aunque de 0 registros, incluso si ya tenia contenido",
    )
    args = parser.parse_args()

    ruta, registros = reconciliar(
        origen_sesiones=args.raiz_sesiones, permitir_vacio=args.permitir_vacio
    )
    features = {registro["feature"] for registro in registros}
    tokens = sum(registro["tokens"].get("total", 0) for registro in registros)
    print(f"Registros: {len(registros)} | Features: {len(features)} | Tokens: {tokens:,}")
    print(f"Escrito: {ruta}")
