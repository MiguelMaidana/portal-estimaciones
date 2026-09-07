"""
plantilla_html.py - Sistema de diseno TSOFT para los reportes HTML.

El CSS vive aca como constante, no en un archivo aparte, a proposito: el
generador tiene que funcionar en cualquier repo donde se instale el kit, y una
plantilla externa es una dependencia mas que se puede borrar, mover o quedar
sin copiar. Embutida, el reporte sale siempre.

Si un equipo quiere su propia marca, puede dejar un CSS en
tsoft-dev/config/estilos-reporte.css y ese reemplaza al default. Va en config/
y no en reportes/ porque reportes/ es carpeta de salida: limpiar los reportes
viejos no tiene que llevarse el estilo puesto.

En los dos casos el CSS termina inline en el HTML generado, asi el reporte es un
archivo solo y se puede mandar por mail sin que se despeine.
"""

from __future__ import annotations

import html
from pathlib import Path

RUTA_CSS_PROPIO = "tsoft-dev/config/estilos-reporte.css"

# Las fuentes se piden por CDN pero siempre con fallback del sistema: un dev
# generando el reporte sin internet tiene que obtener algo legible, no Times.
FUENTES_CDN = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800'
    '&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">'
)

CSS_DEFAULT = """
:root{
  --carbon:#2B2E34;
  --red:#E30613;
  --white:#FFFFFF;
  --gray-dark:#4B4F58;
  --gray-layout:#ECEDF0;
  --offwhite:#F5F6F8;
  --gray-text:#7B808A;
  --gray-border:#C8CBD2;
  --green:#16A37A;
  --yellow:#F5A524;
  --red-dark:#A11820;
  --pink-bg:#FFE9EB;
  --green-bg:#CFECDF;
  --yellow-bg:#FFF4DC;
  --font-body:'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
  --font-mono:'JetBrains Mono', ui-monospace, 'Cascadia Mono', Consolas, monospace;
}

*{ box-sizing:border-box; margin:0; padding:0; }
body{
  font-family:var(--font-body);
  color:var(--carbon);
  background:var(--offwhite);
  -webkit-font-smoothing:antialiased;
  line-height:1.5;
}
.wrap{ max-width:1180px; margin:0 auto; padding:0 0 64px; }

/* ---------- ENCABEZADO ---------- */
.head{ background:var(--carbon); color:var(--white); padding:40px 56px 36px; position:relative; overflow:hidden; }
.head .tri-deco{ position:absolute; top:-50px; right:-30px; width:0; height:0;
  border-style:solid; border-width:0 180px 180px 0;
  border-color:transparent var(--red) transparent transparent; opacity:0.85; }
.eyebrow{ font-size:8.5px; font-weight:700; letter-spacing:0.12em; text-transform:uppercase; color:#FF6B73; }
.head h1{ font-size:34px; font-weight:800; letter-spacing:-0.01em; margin-top:14px; line-height:1.1; }
.head h1 .accent{ color:var(--red); }
.head .periodo{ margin-top:14px; font-family:var(--font-mono); font-size:12px; color:#C7CAD1; }
.head .generado{ margin-top:4px; font-size:10.5px; color:#9AA0AA; }

/* ---------- KPIs ---------- */
.kpis{ background:var(--carbon); display:flex; flex-wrap:wrap; padding:0 56px 40px; }
.kpi{ flex:1; min-width:170px; padding:0 32px 0 0; border-right:1px solid #4B4F58; }
.kpi:last-child{ border-right:none; }
.kpi .num{ font-size:36px; font-weight:800; color:var(--white); letter-spacing:-0.01em; }
.kpi .num.accent{ color:var(--red); }
.kpi .label{ margin-top:8px; font-size:9.5px; color:#9AA0AA; text-transform:uppercase; letter-spacing:0.08em; line-height:1.5; }

/* ---------- SECCIONES ---------- */
section{ padding:40px 56px 0; }
.sec-title{ font-size:22px; font-weight:800; color:var(--carbon); }
.sec-sub{ font-size:12.5px; color:var(--gray-text); margin-top:6px; }

/* ---------- TABLAS ---------- */
table.data{ width:100%; border-collapse:collapse; margin-top:18px; font-size:12px; background:var(--white); }
table.data thead th{ background:var(--carbon); color:var(--white); text-align:left; font-weight:700;
  padding:12px 14px; font-size:10.5px; text-transform:uppercase; letter-spacing:0.04em; white-space:nowrap; }
table.data thead th.num{ text-align:right; }
table.data tbody td{ padding:12px 14px; border-bottom:1px solid var(--gray-border); color:var(--gray-dark); vertical-align:top; }
table.data tbody tr:nth-child(even){ background:var(--offwhite); }
table.data td.name{ font-family:var(--font-mono); font-weight:600; color:var(--carbon); white-space:nowrap; }
table.data td.num{ font-family:var(--font-mono); text-align:right; white-space:nowrap; color:var(--carbon); }
table.data td.vacio{ text-align:center; color:var(--gray-text); font-style:italic; }

.pill{ display:inline-block; font-size:9.5px; font-weight:700; padding:2px 9px; border-radius:20px;
  background:var(--gray-layout); color:var(--gray-dark); white-space:nowrap; }
.pill.ok{ background:var(--green-bg); color:#0E7C5A; }
.pill.curso{ background:var(--pink-bg); color:var(--red-dark); }
.pill.pausa{ background:var(--yellow-bg); color:#8A5A00; }

/* ---------- AVISOS ---------- */
.aviso{ margin-top:16px; font-size:12px; color:var(--gray-dark); line-height:1.65;
  border-left:3px solid var(--gray-border); padding:2px 0 2px 14px; }
.aviso b{ color:var(--carbon); }
.aviso.alerta{ border-left-color:var(--red); }
.aviso.ojo{ border-left-color:var(--yellow); }

/* ---------- PIE ---------- */
.foot{ margin-top:48px; padding:24px 56px 0; border-top:1px solid var(--gray-border);
  display:flex; align-items:center; gap:10px; }
.foot .logo{ font-size:13px; font-weight:800; letter-spacing:-0.02em; color:var(--carbon); }
.foot .logo .tri{ color:var(--red); }
.foot .tagline{ font-size:8px; letter-spacing:0.12em; color:var(--gray-text);
  text-transform:uppercase; border-left:1px solid var(--gray-border); padding-left:8px; }

@media (max-width:900px){
  .head, .kpis, section, .foot{ padding-left:24px; padding-right:24px; }
  .head h1{ font-size:26px; }
  .kpis{ flex-direction:column; gap:24px; }
  .kpi{ border-right:none; border-bottom:1px solid #4B4F58; padding:0 0 18px; }
  .kpi:last-child{ border-bottom:none; padding-bottom:0; }
  table.data{ font-size:11px; }
}

@media print{
  body{ background:var(--white); }
  section{ break-inside:avoid; }
}
"""


def cargar_css(raiz_proyecto: Path | None = None) -> tuple[str, str]:
    """
    Devuelve (css, origen). Si el proyecto trae su propio CSS lo usa; si no,
    el default. Un archivo vacio o ilegible no deja el reporte sin estilo.
    """
    if raiz_proyecto:
        propio = Path(raiz_proyecto) / RUTA_CSS_PROPIO
        try:
            if propio.is_file():
                texto = propio.read_text(encoding="utf-8").strip()
                if texto:
                    return texto, RUTA_CSS_PROPIO
        except Exception:
            pass
    return CSS_DEFAULT, "default"


def esc(valor) -> str:
    """Todo lo que viene del rollout es texto ajeno: nunca va crudo al HTML."""
    return html.escape("" if valor is None else str(valor), quote=True)


def fmt_int(valor) -> str:
    """1234567 -> 1.234.567 (formato local)."""
    try:
        return f"{int(valor):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "-"


def fmt_float(valor, decimales: int = 2) -> str:
    """1234.5 -> 1.234,50 (formato local)."""
    try:
        texto = f"{float(valor):,.{decimales}f}"
    except (TypeError, ValueError):
        return "-"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def kpi(numero: str, etiqueta: str, acento: bool = False) -> str:
    clase = "num accent" if acento else "num"
    return (
        f'<div class="kpi"><div class="{clase}">{esc(numero)}</div>'
        f'<div class="label">{esc(etiqueta)}</div></div>'
    )


def tabla(encabezados: list, filas: list[list[str]], vacio: str = "Sin datos") -> str:
    """
    Tabla de datos. Las celdas llegan ya como HTML (para pills y clases), asi
    que quien las arma es responsable de escapar su contenido.

    Un encabezado puede ser "Feature" o la tupla ("Tokens", "num"), para que la
    columna de numeros quede alineada con sus valores.
    """
    ths = []
    for titulo in encabezados:
        if isinstance(titulo, (tuple, list)):
            etiqueta, clase = titulo[0], titulo[1]
            ths.append(f'<th class="{esc(clase)}">{esc(etiqueta)}</th>')
        else:
            ths.append(f"<th>{esc(titulo)}</th>")
    ths = "".join(ths)
    if filas:
        cuerpo = "".join("<tr>" + "".join(celdas) + "</tr>" for celdas in filas)
    else:
        cuerpo = (
            f'<tr><td class="vacio" colspan="{len(encabezados)}">{esc(vacio)}</td></tr>'
        )
    return (
        f'<table class="data"><thead><tr>{ths}</tr></thead><tbody>{cuerpo}</tbody></table>'
    )


CLASES_ESTADO = {
    "completado": "ok",
    "en curso": "curso",
    "pausado": "pausa",
}


def pill_estado(estado: str) -> str:
    clase = CLASES_ESTADO.get((estado or "").lower(), "")
    return f'<span class="pill {clase}">{esc(estado or "-")}</span>'


def documento(
    titulo: str,
    acento: str,
    periodo: str,
    generado: str,
    kpis: list[str],
    secciones: list[str],
    css: str,
    eyebrow: str = "AI Adoption Program · Medicion",
) -> str:
    """Arma el HTML completo, con el CSS inline para que sea un archivo solo."""
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(titulo)} — {esc(periodo)}</title>
{FUENTES_CDN}
<style>{css}</style>
</head>
<body>
<div class="wrap">

<header class="head">
  <div class="tri-deco"></div>
  <div class="eyebrow">{esc(eyebrow)}</div>
  <h1>{esc(titulo)}<br><span class="accent">{esc(acento)}</span></h1>
  <div class="periodo">{esc(periodo)}</div>
  <div class="generado">Generado: {esc(generado)}</div>
</header>

<div class="kpis">
{"".join(kpis)}
</div>

{"".join(secciones)}

<div class="foot">
  <span class="logo">TSOFT<span class="tri"> &#9654;</span></span>
  <span class="tagline">Make it real</span>
</div>

</div>
</body>
</html>
"""
