"""
reporte_features.py - Reporte de consumo por feature.

Lee tsoft-dev/metrics/features.jsonl (generado por reconciliador.py) y emite
un reporte Markdown agrupado por feature.

Sin filtro devuelve el acumulado historico, que es la lectura correcta para
"cuanto costo esta feature". Para el corte de fin de semana hay que pedir el
periodo: el reconciliador reprocesa siempre todos los rollouts, asi que el
acumulado crece para siempre y por si solo no contesta "que pasa esta semana".

Uso:
  py tsoft-dev/scripts/reporte_features.py
  py tsoft-dev/scripts/reporte_features.py --semana
  py tsoft-dev/scripts/reporte_features.py --semana --fecha 2026-08-15
  py tsoft-dev/scripts/reporte_features.py --desde 2026-08-01 --hasta 2026-08-15
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics_lib as ml
import plantilla_html as ph


def leer_features(raiz_proyecto: Path) -> list[dict]:
    ruta = Path(raiz_proyecto) / "tsoft-dev" / "metrics" / "features.jsonl"
    if not ruta.exists():
        return []
    with ruta.open(encoding="utf-8") as fh:
        return [json.loads(linea) for linea in fh if linea.strip()]


def _fusionar_intervalos(intervalos: list[tuple]) -> list[tuple]:
    """
    Combina intervalos [inicio, fin] que se solapan o son adyacentes.

    Necesario porque el Orquestador queda bloqueado dentro de `wait_agent`
    mientras corre cada subagente: su propio tramo de reloj YA cubre el
    mismo lapso que el tramo del subagente (Explorador, Planificador,
    Desarrollador, Documentador, QA). Sumar los dos tramos tal cual cuenta
    el mismo minuto de pared dos veces.
    """
    if not intervalos:
        return []
    ordenados = sorted(intervalos, key=lambda par: par[0])
    fusionados = [ordenados[0]]
    for inicio, fin in ordenados[1:]:
        ult_inicio, ult_fin = fusionados[-1]
        if inicio <= ult_fin:
            if fin > ult_fin:
                fusionados[-1] = (ult_inicio, fin)
        else:
            fusionados.append((inicio, fin))
    return fusionados


def _tiempo_real_h(intervalos: list[tuple], activo_sin_intervalo: float) -> float:
    """
    Duracion real de pared para un conjunto de tramos, sin contar dos veces
    el tiempo en que un tramo (el del Orquestador esperando) contiene a otro
    (el del subagente que corrio adentro de esa espera).

    `activo_sin_intervalo` es el tiempo_activo_h de los registros que no
    traen inicio/fin validos (rollouts viejos o datos sinteticos de test) --
    no hay con que fusionarlos, asi que se suman aparte, tal como se hacia
    antes de este fix.
    """
    fusionados = _fusionar_intervalos(intervalos)
    segundos = sum((fin - inicio).total_seconds() for inicio, fin in fusionados)
    return round(segundos / 3600 + activo_sin_intervalo, 4)


def agregar_por_feature(registros: list[dict]) -> list[dict]:
    """Suma los tramos de cada feature. Ordena por tokens descendente."""
    acumulado: dict[str, dict] = {}
    intervalos_por_feature: dict[str, list[tuple]] = {}

    for registro in registros:
        nombre = registro.get("feature") or ml.SIN_FEATURE
        fila = acumulado.setdefault(nombre, {
            "feature": nombre,
            "estado": registro.get("estado", "desconocido"),
            "tokens_total": 0,
            "tiempo_activo_h": 0.0,
            "turnos": 0,
            "conversaciones": 0,
            "usd": 0.0,
            "todo_tarifado": True,
            "modelos_multiples": False,
            "origenes": set(),
            "developers": set(),
            "tipos_tarea": set(),
            "complejidades": set(),
            "origenes_complejidad": set(),
        })

        fila["tokens_total"] += registro.get("tokens", {}).get("total", 0)
        inicio_dt = ml.parse_iso(registro.get("inicio"))
        fin_dt = ml.parse_iso(registro.get("fin"))
        if inicio_dt and fin_dt and fin_dt >= inicio_dt:
            intervalos_por_feature.setdefault(nombre, []).append((inicio_dt, fin_dt))
        else:
            fila["tiempo_activo_h"] += registro.get("tiempo_activo_h", 0.0)
        fila["turnos"] += registro.get("turnos", 0)
        fila["conversaciones"] += 1
        fila["usd"] += registro.get("costo", {}).get("usd", 0.0)
        if not registro.get("costo", {}).get("tarifado", False):
            fila["todo_tarifado"] = False
        if registro.get("modelos_multiples"):
            fila["modelos_multiples"] = True
        if registro.get("origen"):
            fila["origenes"].add(registro["origen"])
        if registro.get("developer"):
            fila["developers"].add(registro["developer"])
        if registro.get("tipo_tarea"):
            fila["tipos_tarea"].add(registro["tipo_tarea"])
        if registro.get("complejidad"):
            fila["complejidades"].add(registro["complejidad"])
        if registro.get("origen_complejidad"):
            fila["origenes_complejidad"].add(registro["origen_complejidad"])

    filas = []
    for fila in acumulado.values():
        fila["tiempo_activo_h"] = _tiempo_real_h(
            intervalos_por_feature.get(fila["feature"], []),
            fila["tiempo_activo_h"],
        )
        fila["usd"] = round(fila["usd"], 6)
        fila["origenes"] = sorted(fila["origenes"])
        fila["developers"] = sorted(fila["developers"])
        fila["tipos_tarea"] = sorted(fila["tipos_tarea"])
        fila["complejidades"] = sorted(fila["complejidades"])
        fila["origenes_complejidad"] = sorted(fila["origenes_complejidad"])
        fila["marcador_complejidad"] = resumir_origen_complejidad(
            fila["origenes_complejidad"]
        )
        filas.append(fila)

    filas.sort(key=lambda item: -item["tokens_total"])
    return filas


def agregar_por_etapa(registros: list[dict]) -> list[dict]:
    """Suma el consumo por etapa del flujo (explorador/planificador/.../orquestador)."""
    acumulado: dict[str, dict] = {}

    for registro in registros:
        etapa = registro.get("etapa") or "desconocida"
        fila = acumulado.setdefault(etapa, {
            "etapa": etapa,
            "tokens_total": 0,
            "usd": 0.0,
            "turnos": 0,
            "conversaciones": 0,
        })
        fila["tokens_total"] += registro.get("tokens", {}).get("total", 0)
        fila["usd"] += registro.get("costo", {}).get("usd", 0.0)
        fila["turnos"] += registro.get("turnos", 0)
        fila["conversaciones"] += 1

    filas = []
    for fila in acumulado.values():
        fila["usd"] = round(fila["usd"], 6)
        filas.append(fila)

    filas.sort(key=lambda item: -item["tokens_total"])
    return filas


def etiqueta_visible(nombre: str | None) -> str:
    """
    El nombre que se MUESTRA en el reporte. "sin-feature" es el identificador
    tecnico interno (el que usan el codigo, los filtros y los tests) -- para
    quien lee el reporte, que no tiene por que conocer esa jerga, se muestra
    como "Consumo general de sesion": tokens/costo reales que no se pudieron
    atribuir a ninguna feature de negocio (turnos antes de invocar
    $orquestador, o sin marcador de feature). Sigue sumando al total; solo
    cambia como se lo llama y deja de contarse en el KPI de "Features".
    """
    if not nombre:
        return "-"
    return "Consumo general de sesión" if nombre == ml.SIN_FEATURE else nombre


def resumir_origen_complejidad(origenes: list[str] | set[str]) -> str:
    origenes = {origen for origen in origenes if origen}
    if not origenes or origenes == {"declarado"}:
        return "todas declaradas"
    if origenes == {"inferido"}:
        return "con inferidas"
    return "mixta"


def _lista_o_guion(valores: list[str]) -> str:
    return ", ".join(valores) if valores else "-"


def features_con_actividad_afuera(todos: list[dict], del_periodo: list[dict]) -> list[str]:
    """
    Features del periodo que tambien tuvieron consumo fuera de el.

    Importa avisarlo: una feature que arranco el martes pasado y cerro el
    miercoles de esta semana aparece partida entre dos reportes, y el numero
    semanal es una parte de lo que costo, no el total. Sin este aviso el numero
    parcial se lee como si fuera el definitivo.
    """
    def clave(registro):
        return (registro.get("feature"), registro.get("session_id"), registro.get("inicio"))

    vistos = {clave(registro) for registro in del_periodo}
    afuera = {
        registro.get("feature")
        for registro in todos
        if clave(registro) not in vistos
    }
    presentes = {registro.get("feature") for registro in del_periodo}
    return sorted(nombre for nombre in afuera & presentes if nombre)


ETIQUETA_ACUMULADO = "Acumulado historico (todo lo registrado)"


def calcular(
    raiz_proyecto: Path,
    desde: date | None = None,
    hasta: date | None = None,
    etiqueta_periodo: str | None = None,
) -> dict:
    """
    Todo el dato del reporte, sin formato.

    Lo comparten el Markdown y el HTML. Si cada uno hiciera su propia cuenta,
    dos reportes del mismo viernes podrian mostrar totales distintos y no
    habria forma de saber a cual creerle.
    """
    todos = leer_features(raiz_proyecto)

    if desde and hasta:
        registros = ml.filtrar_periodo(todos, desde, hasta)
        partidas = features_con_actividad_afuera(todos, registros)
    else:
        registros = todos
        partidas = []

    filas = agregar_por_feature(registros)
    por_etapa = agregar_por_etapa(registros)
    inferidas = [
        registro for registro in registros
        if registro.get("origen_complejidad") == "inferido"
    ]

    # La cuota se reporta como pico, nunca sumada: es un porcentaje de una
    # ventana movil compartida, y una misma conversacion puede aparecer en
    # varias features.
    cuotas = [r["cuota"] for r in registros if r.get("cuota")]

    return {
        "registros": registros,
        "filas": filas,
        "por_etapa": por_etapa,
        "partidas": partidas,
        # len(filas) cuenta "sin-feature" como si fuera una feature de
        # negocio -- este campo es el que hay que mostrar en el KPI.
        "features_reales": len([f for f in filas if f["feature"] != ml.SIN_FEATURE]),
        "tokens_totales": sum(fila["tokens_total"] for fila in filas),
        "usd_total": sum(fila["usd"] for fila in filas),
        "sin_tarifar": [fila["feature"] for fila in filas if not fila["todo_tarifado"]],
        "modelos_mixtos": [fila["feature"] for fila in filas if fila.get("modelos_multiples")],
        "features_con_inferidas": sorted({
            registro.get("feature") for registro in inferidas if registro.get("feature")
        }),
        "conversaciones_con_inferidas": len(inferidas),
        "pico_cuota": max((c["pico"] for c in cuotas), default=None),
        "plan": next((c.get("plan") for c in cuotas if c.get("plan")), None),
        "periodo": etiqueta_periodo or ETIQUETA_ACUMULADO,
    }


def generar_markdown(
    raiz_proyecto: Path | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    etiqueta_periodo: str | None = None,
) -> Path:
    raiz_proyecto = Path(raiz_proyecto) if raiz_proyecto else ml.raiz_kit()
    datos = calcular(raiz_proyecto, desde, hasta, etiqueta_periodo)

    registros = datos["registros"]
    filas = datos["filas"]
    partidas = datos["partidas"]
    tokens_totales = datos["tokens_totales"]
    usd_total = datos["usd_total"]
    sin_tarifar = datos["sin_tarifar"]
    modelos_mixtos = datos["modelos_mixtos"]
    pico_cuota = datos["pico_cuota"]
    plan = datos["plan"]

    lineas = [
        "# Consumo por feature - TSOFT AI Dev Kit",
        "",
        f"Generado: {ml.ahora_iso()}",
        "",
        f"Periodo: {datos['periodo']}",
        "",
        "## Resumen",
        "",
        "| Metrica | Valor |",
        "|---|---|",
        f"| Features | {datos['features_reales']} |",
        f"| Tokens totales | {tokens_totales:,} |",
        # Dos decimales, igual que el HTML: un total con cuatro es precision
        # falsa. Las filas por feature si los llevan, porque ahi los centavos
        # distinguen una feature chica de otra.
        f"| Costo USD equivalente | ${usd_total:.2f} |",
    ]

    if pico_cuota is not None:
        lineas.append(f"| Pico de cuota semanal | {pico_cuota:.0f}% |")

    if plan and plan != "api":
        lineas += [
            "",
            f"> El plan es **{plan}**: no se paga por token, se paga una "
            "suscripcion fija. El costo en USD es el equivalente a precios de "
            "API y sirve para dimensionar, no es gasto real. El limite que "
            "importa es la cuota semanal.",
        ]

    if pico_cuota is not None and pico_cuota >= 90:
        lineas += [
            "",
            f"> **Atencion:** la cuota semanal llego al {pico_cuota:.0f}%. Al "
            "100% el trabajo queda bloqueado hasta que la ventana se reinicia.",
        ]

    lineas += [
        "",
        "## Consumo por etapa",
        "",
        "| Etapa | Tokens | Turnos | Conversaciones | USD |",
        "|---|---|---|---|---|",
    ]
    if not datos["por_etapa"]:
        lineas.append("| - | - | - | - | Sin registros en el periodo |")
    for fila in datos["por_etapa"]:
        lineas.append(
            f"| {fila['etapa']} "
            f"| {fila['tokens_total']:,} "
            f"| {fila['turnos']} "
            f"| {fila['conversaciones']} "
            f"| ${fila['usd']:.4f} |"
        )

    lineas += [
        "",
        "## Detalle por feature",
        "",
        "| Feature | Estado | Tipo | Complejidad (valores) | Complejidad (origen) | Tokens | Tiempo activo | Turnos | Conversaciones | USD | Origen |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    if not filas:
        lineas.append("| - | - | - | - | - | - | - | - | - | - | Sin registros en el periodo |")

    for fila in filas:
        lineas.append(
            f"| {etiqueta_visible(fila['feature'])} "
            f"| {fila['estado']} "
            f"| {_lista_o_guion(fila['tipos_tarea'])} "
            f"| {_lista_o_guion(fila['complejidades'])} "
            f"| {fila['marcador_complejidad']} "
            f"| {fila['tokens_total']:,} "
            f"| {fila['tiempo_activo_h']:.2f} h "
            f"| {fila['turnos']} "
            f"| {fila['conversaciones']} "
            f"| ${fila['usd']:.4f} "
            f"| {', '.join(fila['origenes']) or '-'} |"
        )

    lineas += [
        "",
        "## Detalle por conversacion",
        "",
        "| Feature | Etapa | Inicio | Tipo | Origen tipo | Complejidad | Origen complejidad | Tokens | Tiempo activo | Turnos | USD | Modelo | Origen |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    if not registros:
        lineas.append("| - | - | - | - | - | - | - | - | - | - | - | - | Sin registros en el periodo |")

    for registro in registros:
        inicio = ml.parse_iso(registro.get("inicio"))
        tokens = registro.get("tokens") or {}
        costo = registro.get("costo") or {}
        lineas.append(
            f"| {etiqueta_visible(registro.get('feature'))} "
            f"| {registro.get('etapa') or '-'} "
            f"| {inicio.strftime('%d/%m/%Y %H:%M') if inicio else '-'} "
            f"| {registro.get('tipo_tarea') or '-'} "
            f"| {registro.get('origen_tipo') or '-'} "
            f"| {registro.get('complejidad') or '-'} "
            f"| {registro.get('origen_complejidad') or '-'} "
            f"| {tokens.get('total', 0):,} "
            f"| {registro.get('tiempo_activo_h', 0):.2f} h "
            f"| {registro.get('turnos', 0)} "
            f"| ${costo.get('usd', 0):.4f} "
            f"| {registro.get('modelo') or '-'} "
            f"| {registro.get('origen') or '-'} |"
        )

    if datos["conversaciones_con_inferidas"]:
        lineas += [
            "",
            "> Aviso: "
            f"{datos['conversaciones_con_inferidas']} conversacion(es) del periodo "
            "tienen complejidad inferida (no declarada por el IA Maker). Features "
            "involucradas: " + ", ".join(etiqueta_visible(n) for n in datos["features_con_inferidas"]),
        ]

    if partidas:
        lineas += [
            "",
            "> Aviso: estas features tambien tuvieron consumo **fuera** del "
            "periodo, asi que los numeros de arriba son la parte que cayo en "
            "esta ventana y no el costo total de la feature. Para el total, "
            "correr el reporte sin filtro: " + ", ".join(etiqueta_visible(n) for n in partidas),
        ]

    if sin_tarifar:
        lineas += [
            "",
            "> Aviso: estas features tienen consumo sin tarifar porque el modelo "
            "no tiene precio cargado en celula.json: " + ", ".join(etiqueta_visible(n) for n in sin_tarifar),
        ]

    if modelos_mixtos:
        lineas += [
            "",
            "> Aviso: estas features tienen al menos un rollout con mas de un "
            "modelo detectado; el costo se tarifa completo con el primer "
            "modelo visto y puede no ser exacto para el tramo posterior al "
            "cambio de modelo: " + ", ".join(etiqueta_visible(n) for n in modelos_mixtos),
        ]

    destino = raiz_proyecto / "tsoft-dev" / "reportes" / "features.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(lineas), encoding="utf-8")
    return destino


def _avisos_html(datos: dict) -> list[str]:
    """Los mismos avisos que el Markdown, con el estilo de la plantilla."""
    avisos = []
    plan, pico = datos["plan"], datos["pico_cuota"]

    if plan and plan != "api":
        avisos.append(
            f'<div class="aviso">El plan es <b>{ph.esc(plan)}</b>: no se paga por '
            "token, se paga una suscripcion fija. El costo en USD es el "
            "equivalente a precios de API y sirve para dimensionar, "
            "<b>no es gasto real</b>. El limite que importa es la cuota semanal.</div>"
        )

    if pico is not None and pico >= 90:
        avisos.append(
            f'<div class="aviso alerta"><b>Atencion:</b> la cuota semanal llego al '
            f"{pico:.0f}%. Al 100% el trabajo queda bloqueado hasta que la ventana "
            "se reinicia.</div>"
        )

    if datos["partidas"]:
        avisos.append(
            '<div class="aviso ojo">Estas features tambien tuvieron consumo '
            "<b>fuera</b> del periodo, asi que los numeros de arriba son la parte "
            "que cayo en esta ventana y no el costo total de la feature. Para el "
            "total, generar el reporte sin filtro: <b>"
            + ph.esc(", ".join(etiqueta_visible(n) for n in datos["partidas"]))
            + "</b></div>"
        )

    if datos["conversaciones_con_inferidas"]:
        avisos.append(
            '<div class="aviso ojo">Hay <b>'
            + ph.esc(datos["conversaciones_con_inferidas"])
            + "</b> conversacion(es) del periodo con "
            "<b>complejidad inferida</b> (no declarada por el IA Maker). Features involucradas: <b>"
            + ph.esc(", ".join(etiqueta_visible(n) for n in datos["features_con_inferidas"]))
            + "</b></div>"
        )

    if datos["sin_tarifar"]:
        avisos.append(
            '<div class="aviso ojo">Estas features tienen consumo sin tarifar '
            "porque el modelo no tiene precio cargado en <b>celula.json</b>: "
            + ph.esc(", ".join(etiqueta_visible(n) for n in datos["sin_tarifar"]))
            + "</div>"
        )

    if datos["modelos_mixtos"]:
        avisos.append(
            '<div class="aviso ojo">Estas features tienen al menos una '
            "conversacion con mas de un modelo detectado; el costo se tarifa "
            "completo con el primer modelo visto y puede no ser exacto para el "
            "tramo posterior al cambio: "
            + ph.esc(", ".join(etiqueta_visible(n) for n in datos["modelos_mixtos"]))
            + "</div>"
        )

    return avisos


def _fila_conversacion(registro: dict) -> list[str]:
    inicio = ml.parse_iso(registro.get("inicio"))
    tokens = registro.get("tokens") or {}
    costo = registro.get("costo") or {}
    return [
        f'<td class="name">{ph.esc(etiqueta_visible(registro.get("feature")))}</td>',
        f'<td>{ph.esc(registro.get("etapa") or "-")}</td>',
        f'<td>{ph.esc(inicio.strftime("%d/%m/%Y %H:%M") if inicio else "-")}</td>',
        f'<td>{ph.esc(registro.get("tipo_tarea") or "-")}</td>',
        f'<td>{ph.esc(registro.get("origen_tipo") or "-")}</td>',
        f'<td>{ph.esc(registro.get("complejidad") or "-")}</td>',
        f'<td>{ph.esc(registro.get("origen_complejidad") or "-")}</td>',
        f'<td class="num">{ph.fmt_int(tokens.get("total"))}</td>',
        f'<td class="num">{ph.fmt_float(registro.get("tiempo_activo_h"), 2)} h</td>',
        f'<td class="num">{ph.fmt_int(registro.get("turnos"))}</td>',
        f'<td class="num">${ph.fmt_float(costo.get("usd"), 4)}</td>',
        f'<td>{ph.esc(registro.get("modelo") or "-")}</td>',
        f'<td>{ph.esc(registro.get("origen") or "-")}</td>',
    ]


def _generado_local() -> str:
    """
    Fecha de generacion en hora local, con el mismo formato que las fechas de
    las tablas. El ISO en UTC del Markdown junto a horas locales confunde.
    """
    momento = ml.parse_iso(ml.ahora_iso())
    return momento.strftime("%d/%m/%Y %H:%M") if momento else ml.ahora_iso()


def generar_html(
    raiz_proyecto: Path | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    etiqueta_periodo: str | None = None,
) -> Path:
    """Escribe tsoft-dev/reportes/features.html con el diseno TSOFT."""
    raiz_proyecto = Path(raiz_proyecto) if raiz_proyecto else ml.raiz_kit()
    datos = calcular(raiz_proyecto, desde, hasta, etiqueta_periodo)
    css, _origen = ph.cargar_css(raiz_proyecto)

    kpis = [
        ph.kpi(ph.fmt_int(datos["features_reales"]), "Features"),
        ph.kpi(ph.fmt_int(datos["tokens_totales"]), "Tokens totales", acento=True),
        ph.kpi(f"${ph.fmt_float(datos['usd_total'], 2)}", "Equivalente en USD"),
    ]
    if datos["pico_cuota"] is not None:
        kpis.append(ph.kpi(f"{datos['pico_cuota']:.0f}%", "Pico de cuota semanal"))

    filas_feature = [
        [
            f'<td class="name">{ph.esc(etiqueta_visible(fila["feature"]))}</td>',
            f'<td>{ph.pill_estado(fila["estado"])}</td>',
            f'<td>{ph.esc(_lista_o_guion(fila["tipos_tarea"]))}</td>',
            f'<td>{ph.esc(_lista_o_guion(fila["complejidades"]))}</td>',
            f'<td>{ph.esc(fila["marcador_complejidad"])}</td>',
            f'<td class="num">{ph.fmt_int(fila["tokens_total"])}</td>',
            f'<td class="num">{ph.fmt_float(fila["tiempo_activo_h"], 2)} h</td>',
            f'<td class="num">{ph.fmt_int(fila["turnos"])}</td>',
            f'<td class="num">{ph.fmt_int(fila["conversaciones"])}</td>',
            f'<td class="num">${ph.fmt_float(fila["usd"], 4)}</td>',
            f'<td>{ph.esc(", ".join(fila["origenes"]) or "-")}</td>',
        ]
        for fila in datos["filas"]
    ]

    secciones = [
        "<section>"
        '<div class="sec-title">Consumo por feature</div>'
        '<div class="sec-sub">Ordenado por consumo. El tiempo activo descarta '
        "las pausas largas.</div>"
        + ph.tabla(
            ["Feature", "Estado", "Tipo", "Complejidad (valores)", "Complejidad (origen)",
             ("Tokens", "num"), ("Tiempo activo", "num"), ("Turnos", "num"),
             ("Conversaciones", "num"), ("USD", "num"), "Origen"],
            filas_feature,
            vacio="Sin registros en el periodo",
        )
        + "".join(_avisos_html(datos))
        + "</section>",
        "<section>"
        '<div class="sec-title">Consumo por etapa</div>'
        '<div class="sec-sub">Cuanto tokens/costo se gasto en cada etapa del '
        "flujo. Incluye orquestador (aprobaciones del IA Maker) y, si algun "
        "registro no trae rol, subagente-sin-rol o desconocida.</div>"
        + ph.tabla(
            ["Etapa", ("Tokens", "num"), ("Turnos", "num"),
             ("Conversaciones", "num"), ("USD", "num")],
            [
                [
                    f'<td class="name">{ph.esc(fila["etapa"])}</td>',
                    f'<td class="num">{ph.fmt_int(fila["tokens_total"])}</td>',
                    f'<td class="num">{ph.fmt_int(fila["turnos"])}</td>',
                    f'<td class="num">{ph.fmt_int(fila["conversaciones"])}</td>',
                    f'<td class="num">${ph.fmt_float(fila["usd"], 4)}</td>',
                ]
                for fila in datos["por_etapa"]
            ],
            vacio="Sin registros en el periodo",
        )
        + "</section>",
        "<section>"
        '<div class="sec-title">Detalle por conversacion</div>'
        '<div class="sec-sub">Cada linea es una conversacion de Codex. Una '
        "feature puede tener varias. La clasificacion muestra si la "
        "complejidad fue declarada o inferida.</div>"
        + ph.tabla(
            ["Feature", "Etapa", "Inicio", "Tipo", "Origen tipo", "Complejidad",
             "Origen complejidad", ("Tokens", "num"), ("Tiempo activo", "num"),
             ("Turnos", "num"), ("USD", "num"), "Modelo", "Origen"],
            [_fila_conversacion(registro) for registro in datos["registros"]],
            vacio="Sin registros en el periodo",
        )
        + "</section>",
    ]

    destino = raiz_proyecto / "tsoft-dev" / "reportes" / "features.html"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        ph.documento(
            titulo="Consumo",
            acento="por feature",
            periodo=datos["periodo"],
            generado=_generado_local(),
            kpis=kpis,
            secciones=secciones,
            css=css,
        ),
        encoding="utf-8",
    )
    return destino


def resolver_periodo(args) -> tuple[date | None, date | None, str | None]:
    """
    Traduce los flags a (desde, hasta, etiqueta). Sin flags devuelve el
    acumulado, que es el comportamiento historico del comando.
    """
    if args.desde or args.hasta:
        if not (args.desde and args.hasta):
            raise SystemExit("--desde y --hasta van juntos.")
        desde = ml.parse_fecha(args.desde)
        hasta = ml.parse_fecha(args.hasta)
        if desde > hasta:
            raise SystemExit("--desde no puede ser posterior a --hasta.")
        return desde, hasta, f"{desde.isoformat()} a {hasta.isoformat()}"

    if args.semana:
        return ml.periodo_semanal(ml.parse_fecha(args.fecha))

    if args.diario:
        return ml.periodo_diario(ml.parse_fecha(args.fecha))

    return None, None, None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Reporte Markdown de consumo por feature. Sin filtro muestra el "
            "acumulado historico; con --semana, el corte de los ultimos 7 dias."
        )
    )
    parser.add_argument("--semana", action="store_true", help="Los ultimos 7 dias")
    parser.add_argument("--diario", action="store_true", help="Un solo dia")
    parser.add_argument(
        "--fecha",
        default=None,
        help="Dia en que cierra el periodo (YYYY-MM-DD). Por defecto, hoy",
    )
    parser.add_argument("--desde", default=None, help="Inicio del periodo (YYYY-MM-DD)")
    parser.add_argument("--hasta", default=None, help="Fin del periodo (YYYY-MM-DD)")
    parser.add_argument(
        "--html",
        action="store_true",
        help="Genera tambien features.html, con el diseno TSOFT",
    )
    args = parser.parse_args()

    desde, hasta, etiqueta = resolver_periodo(args)
    ruta = generar_markdown(desde=desde, hasta=hasta, etiqueta_periodo=etiqueta)
    print(f"Reporte generado: {ruta}")

    if args.html:
        ruta_html = generar_html(desde=desde, hasta=hasta, etiqueta_periodo=etiqueta)
        print(f"Reporte generado: {ruta_html}")

    print()
    print(ruta.read_text(encoding="utf-8"))
