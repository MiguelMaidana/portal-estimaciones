"""
reporte.py - Generador de reportes Markdown del TSOFT AI Dev Kit.

Genera dos tipos de reporte:
  - Por ejecucion: resumen de una sesion especifica
  - Consolidado: indicadores del periodo con detalle por ejecucion

Uso:
  python tsoft-dev/scripts/reporte.py ejecucion --session-id <id>
  python tsoft-dev/scripts/reporte.py consolidado --desde 2026-07-01
  python tsoft-dev/scripts/reporte.py listar
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics_lib as ml


def _fecha(iso: str | None) -> str:
    if not iso:
        return "-"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return iso


def generar_ejecucion(session_id: str, raiz: Path | None = None, ledger: list[dict] | None = None) -> Path | None:
    """Si el caller ya leyo el ledger, se lo puede pasar en `ledger` para no releerlo."""
    raiz = raiz or ml.raiz_kit()
    ledger = ledger if ledger is not None else ml.leer_ledger(raiz)
    registros = [
        registro
        for registro in ledger
        if registro.get("session_id") == session_id and registro.get("evento") == "ejecucion"
    ]

    if not registros:
        return None

    reg = registros[-1]
    clasificacion = reg.get("clasificacion", {})
    tok = reg.get("tokens", {})
    cos = reg.get("costo", {})
    evidencia = reg.get("evidencia", {})

    lineas = [
        "# Reporte de ejecucion - TSOFT AI Dev Kit",
        "",
        "| Campo | Valor |",
        "|---|---|",
        f"| Session ID | `{session_id}` |",
        f"| Ticket | {reg.get('ticket') or '-'} |",
        f"| Feature | {reg.get('feature') or '-'} |",
        f"| Inicio | {_fecha(reg.get('inicio'))} |",
        f"| Fin | {_fecha(reg.get('fin'))} |",
        f"| Duracion | {reg.get('duracion_h', 0):.2f} h |",
        f"| Modelo | {reg.get('modelo') or '-'} |",
        "",
        "## Tarea",
        "",
        "| Campo | Valor |",
        "|---|---|",
        f"| Tipo | {clasificacion.get('tipo_tarea', '-')} "
        f"({clasificacion.get('origen_tipo', clasificacion.get('origen', '-'))}) |",
        f"| Complejidad | {clasificacion.get('complejidad', '-')} "
        f"({clasificacion.get('origen_complejidad', clasificacion.get('origen', '-'))}) |",
        f"| Origen clasificacion | {clasificacion.get('origen', '-')} |",
        "",
        "## Tokens y costo",
        "",
        "| Concepto | Valor |",
        "|---|---|",
        f"| Input | {tok.get('input', 0):,} |",
        f"| Output | {tok.get('output', 0):,} |",
        f"| Total | {tok.get('total', 0):,} |",
        f"| Fuente | {tok.get('fuente', '-')} |",
        f"| Costo USD | ${cos.get('usd', 0):.4f} |",
        f"| Costo {cos.get('moneda') or 'local'} | ${cos.get('local', 0):,.0f} |",
        "",
    ]

    # Los subagentes consumen aparte del orquestador; sin esto la sesion
    # subcuenta todo lo que se delego.
    subagentes = ml.subagentes_de_sesion(ledger, session_id)
    if subagentes:
        config = ml.cargar_config(raiz)
        tok_sub = sum(s.get("tokens", {}).get("total", 0) for s in subagentes)
        usd_sub = sum(
            ml.costo_usd(s.get("tokens", {}), s.get("modelo") or "", config)["usd"]
            for s in subagentes
        )
        lineas += [
            "## Subagentes",
            "",
            "| Tipo | Tokens | Costo USD | Duracion | Fuente |",
            "|---|---|---|---|---|",
        ]
        for s in sorted(subagentes, key=lambda x: -x.get("tokens", {}).get("total", 0)):
            st = s.get("tokens", {})
            su = ml.costo_usd(st, s.get("modelo") or "", config)["usd"]
            dur = s.get("duracion_h")
            dur_txt = f"{dur:.4f} h" if isinstance(dur, (int, float)) else "-"
            lineas.append(
                f"| {s.get('agent_type', '-')} "
                f"| {st.get('total', 0):,} "
                f"| ${su:.4f} "
                f"| {dur_txt} "
                f"| {st.get('fuente', '-')} |"
            )
        lineas += [
            "",
            "| Consumo de la sesion | Tokens | Costo USD |",
            "|---|---|---|",
            f"| Orquestador | {tok.get('total', 0):,} | ${cos.get('usd', 0):.4f} |",
            f"| Subagentes ({len(subagentes)}) | {tok_sub:,} | ${usd_sub:.4f} |",
            f"| **Real** | **{tok.get('total', 0) + tok_sub:,}** "
            f"| **${cos.get('usd', 0) + usd_sub:.4f}** |",
            "",
        ]

    lineas += [
        "## Evidencia",
        "",
        "| Metrica | Valor |",
        "|---|---|",
        f"| Archivos tocados | {len(evidencia.get('archivos_tocados', []))} |",
        f"| Ediciones | {evidencia.get('ediciones', 0)} |",
        f"| Comandos ejecutados | {len(evidencia.get('comandos', []))} |",
        f"| Subagentes invocados | {len(evidencia.get('subagentes', []))} |",
        f"| Turnos | {evidencia.get('turnos', 0)} |",
    ]

    if evidencia.get("archivos_tocados"):
        lineas += ["", "### Archivos tocados", ""]
        for archivo in evidencia["archivos_tocados"]:
            lineas.append(f"- `{archivo}`")

    if evidencia.get("comandos"):
        lineas += ["", "### Comandos ejecutados", ""]
        for comando in evidencia["comandos"]:
            lineas.append(f"- `{comando}`")

    if evidencia.get("subagentes"):
        lineas += ["", "### Subagentes invocados", ""]
        for subagente in evidencia["subagentes"]:
            lineas.append(f"- {subagente}")

    if cos.get("aviso"):
        lineas += ["", f"> Aviso: {cos['aviso']}"]

    if not clasificacion.get("tipo_reconocido", True):
        lineas += [
            "",
            f"> ATENCION: el tipo de tarea `{clasificacion.get('tipo_tarea')}` no "
            "es uno de los nueve tipos validos de baselines.json (tipos_validos). "
            "Revisar la etiqueta #tarea: del prompt.",
        ]

    if not reg.get("duracion_confiable", True):
        lineas += [
            "",
            "> ATENCION: no se pudo medir cuanto duro la sesion (inicio_epoch "
            "ausente en el estado). La duracion de esta fila quedo en 0h, no "
            "que la sesion fue instantanea.",
        ]

    if tok.get("estimacion"):
        lineas += ["", "> Aviso: tokens estimados; el transcript no expuso uso exacto"]

    destino = raiz / "tsoft-dev/reportes/ejecuciones" / f"{session_id}.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(lineas), encoding="utf-8")
    return destino


def generar_consolidado(desde: str | None = None, raiz: Path | None = None, ledger: list[dict] | None = None) -> Path:
    """Si el caller ya leyo el ledger, se lo puede pasar en `ledger` para no releerlo."""
    raiz = raiz or ml.raiz_kit()
    ledger = ledger if ledger is not None else ml.leer_ledger(raiz)

    # Una linea por sesion, no una por cierre: las lineas del ledger son fotos
    # acumuladas y sumarlas multiplica el consumo.
    ejecuciones = ml.ultimas_ejecuciones(ledger)

    if desde:
        ejecuciones = [registro for registro in ejecuciones if (registro.get("inicio") or "") >= desde]

    total_tok = sum(registro.get("tokens", {}).get("total", 0) for registro in ejecuciones)

    # Los subagentes consumen aparte del orquestador.
    sesiones_validas = {registro.get("session_id") for registro in ejecuciones}
    subagentes = [
        s for s in ml.subagentes_de_sesion(ledger)
        if s.get("session_id") in sesiones_validas
    ]
    total_tok_sub = sum(s.get("tokens", {}).get("total", 0) for s in subagentes)

    # El costo se recalcula, no se reusa el guardado: las lineas escritas antes
    # de corregir la formula cobraban el cache dos veces e inflaban el total
    # unas cinco veces. Recalcular sobre los tokens repara tambien el historico.
    config = ml.cargar_config(raiz)
    total_usd = sum(
        ml.costo_usd(
            registro.get("tokens", {}),
            registro.get("modelo") or "",
            config,
        )["usd"]
        for registro in ejecuciones
    )
    total_usd_sub = sum(
        ml.costo_usd(s.get("tokens", {}), s.get("modelo") or "", config)["usd"]
        for s in subagentes
    )

    por_agente: dict[str, dict] = {}
    for s in subagentes:
        tipo_ag = s.get("agent_type", "desconocido")
        acum = por_agente.setdefault(tipo_ag, {"n": 0, "tokens": 0, "usd": 0.0})
        acum["n"] += 1
        acum["tokens"] += s.get("tokens", {}).get("total", 0)
        acum["usd"] += ml.costo_usd(s.get("tokens", {}), s.get("modelo") or "", config)["usd"]

    lineas = [
        "# Reporte consolidado - TSOFT AI Dev Kit",
        "",
        f"Generado: {ml.ahora_iso()}",
        f"Periodo: {desde or 'todo el historico'}",
        "",
        "## Resumen",
        "",
        "| Metrica | Valor |",
        "|---|---|",
        f"| Ejecuciones | {len(ejecuciones)} |",
        f"| Tokens orquestador | {total_tok:,} |",
        f"| Tokens subagentes ({len(subagentes)}) | {total_tok_sub:,} |",
        f"| **Tokens totales** | **{total_tok + total_tok_sub:,}** |",
        f"| Costo USD orquestador | ${total_usd:.4f} |",
        f"| Costo USD subagentes | ${total_usd_sub:.4f} |",
        f"| **Costo USD total** | **${total_usd + total_usd_sub:.4f}** |",
        "",
    ]

    if any(not r.get("duracion_confiable", True) for r in ejecuciones):
        lineas += [
            "> ATENCION: alguna ejecucion del listado incluye una sesion sin "
            "duracion medible (inicio_epoch ausente). Su duracion quedo en 0h.",
            "",
        ]

    if por_agente:
        lineas += [
            "## Consumo por tipo de subagente",
            "",
            "| Subagente | Invocaciones | Tokens | Costo USD |",
            "|---|---|---|---|",
        ]
        for tipo_ag, dato in sorted(por_agente.items(), key=lambda item: -item[1]["tokens"]):
            lineas.append(
                f"| {tipo_ag} | {dato['n']} | {dato['tokens']:,} | ${dato['usd']:.4f} |"
            )
        lineas.append("")

    lineas += [
        "## Detalle por ejecucion",
        "",
        "| Session ID | Ticket | Feature | Tipo | Complejidad | Duracion | Tokens |",
        "|---|---|---|---|---|---|---|",
    ]

    for registro in ejecuciones:
        clasificacion = registro.get("clasificacion", {})
        tok = registro.get("tokens", {})
        lineas.append(
            f"| `{registro.get('session_id', '-')[:12]}` "
            f"| {registro.get('ticket') or '-'} "
            f"| {registro.get('feature') or '-'} "
            f"| {clasificacion.get('tipo_tarea', '-')} "
            f"| {clasificacion.get('complejidad', '-')} "
            f"| {registro.get('duracion_h', 0):.2f} h "
            f"| {tok.get('total', 0):,} |"
        )

    destino = raiz / "tsoft-dev/reportes/consolidado.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(lineas), encoding="utf-8")
    return destino


def cmd_listar(raiz: Path) -> None:
    ledger = ml.leer_ledger(raiz)
    ejecuciones = [registro for registro in ledger if registro.get("evento") == "ejecucion"]
    if not ejecuciones:
        print("Sin ejecuciones registradas todavia.")
        return

    print(f"{'Session ID':<16} {'Ticket':<14} {'Tipo':<25} {'Duracion':>9} {'Tokens':>8}")
    print("-" * 78)
    for registro in ejecuciones[-20:]:
        clasificacion = registro.get("clasificacion", {})
        tok = registro.get("tokens", {})
        print(
            f"{registro.get('session_id', '-')[:14]:<16} "
            f"{(registro.get('ticket') or '-')[:12]:<14} "
            f"{clasificacion.get('tipo_tarea', '-')[:23]:<25} "
            f"{registro.get('duracion_h', 0):>8.2f}h "
            f"{tok.get('total', 0):>8,}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reportes TSOFT AI Dev Kit")
    sub = parser.add_subparsers(dest="cmd")

    parser_ejecucion = sub.add_parser("ejecucion")
    parser_ejecucion.add_argument("--session-id", required=True)

    parser_consolidado = sub.add_parser("consolidado")
    parser_consolidado.add_argument("--desde", default=None)

    sub.add_parser("listar")

    args = parser.parse_args()
    raiz = ml.raiz_kit()

    if args.cmd == "ejecucion":
        ruta = generar_ejecucion(args.session_id, raiz)
        print(f"Reporte generado: {ruta}" if ruta else "Sin datos para esa sesion.")
    elif args.cmd == "consolidado":
        ruta = generar_consolidado(args.desde, raiz)
        print(f"Consolidado generado: {ruta}")
    elif args.cmd == "listar":
        cmd_listar(raiz)
    else:
        parser.print_help()
