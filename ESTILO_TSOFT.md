# ESTILO VISUAL — TSOFT 

> Usá este archivo como referencia de estilo cuando generes presentaciones para TSOFT.
> Se aplica junto con el contenido que te pase. El estilo manda sobre cualquier default.

---

## IDENTIDAD GENERAL

- Las presentaciones son **ejecutivas y directas**. Sin relleno, sin bullets genéricos.
- El tono visual es **profesional pero con carácter**: fondo oscuro en portada y cierre, contenido claro al medio.
- Cada slide tiene **una sola idea principal**. Si hay demasiado, partilo en dos slides.
- Siempre hay **una etiqueta de categoría** pequeña arriba a la izquierda (ej: `ESTRATEGIA 01 · OVERVIEW`).
- Siempre hay **numeración de slide** abajo a la derecha (ej: `03 / 18`).
- Logo `TSOFT` + tagline `MAKE IT REAL` en el footer de cada slide.

---

## PALETA DE COLORES

### Colores principales

| Nombre        | Hex         | Uso                                                                 |
| ------------- | ----------- | ------------------------------------------------------------------- |
| Negro carbón | `#2B2E34` | Fondo de portada, slide de sección, cierre                         |
| Rojo         | `#E30613` | Acento primario: etiquetas, números destacados, shapes decorativos |
| Blanco        | `#FFFFFF` | Texto sobre fondo oscuro, fondo de slides de contenido              |
| Azul noche    | `#0E2841` | Variante de fondo oscuro (Plan IA)                                  |

### Colores de soporte

| Nombre      | Hex         | Uso                                       |
| ----------- | ----------- | ----------------------------------------- |
| Gris oscuro | `#4B4F58` | Fondos de tabla header, cards secundarios |
| Gris layout | `#ECEDF0` | Fondo de slides de contenido, divisores   |
| Off-white   | `#F5F6F8` | Fondo alternativo muy claro               |
| Gris texto  | `#7B808A` | Subtítulos, texto secundario, captions   |
| Gris borde  | `#C8CBD2` | Bordes de tabla, separadores              |

### Colores semánticos (estado / categoría)

| Nombre      | Hex         | Uso                                  |
| ----------- | ----------- | ------------------------------------ |
| Verde       | `#16A37A` | Confirmado, disponible, positivo, OK |
| Azul        | `#2C5282` | Categoría, referencia, neutral      |
| Amarillo    | `#F5A524` | Alerta, pendiente, advertencia       |
| Rojo oscuro | `#A11820` | Error, crítico, bloqueado           |
| Rosa claro  | `#FFE9EB` | Fondo de tag rojo suave              |
| Verde claro | `#CFECDF` | Fondo de tag verde suave             |

---

## TIPOGRAFÍA

| Elemento                         | Fuente                    | Peso    | Tamaño  | Color                     |
| -------------------------------- | ------------------------- | ------- | -------- | ------------------------- |
| Título de portada               | Calibri / Inter           | Bold    | 36–44pt | `#FFFFFF`               |
| Título de slide contenido       | Calibri                   | Bold    | 24–32pt | `#2B2E34`               |
| Número de estrategia / sección | Calibri                   | Bold    | 48–64pt | `#E30613`               |
| Subtítulo / descripción        | Calibri                   | Regular | 14–16pt | `#7B808A`               |
| Cuerpo / bullets                 | Calibri                   | Regular | 11–13pt | `#2B2E34`               |
| Etiqueta de categoría (header)  | Calibri                   | Bold    | 8–9pt   | `#E30613` (uppercase)   |
| Texto en tabla                   | Calibri                   | Regular | 9–11pt  | según fondo              |
| Código / técnico               | JetBrains Mono / Consolas | Regular | 10pt     | `#2B2E34` o `#FFFFFF` |
| Métrica / número grande        | Calibri                   | Bold    | 28–40pt | `#FFFFFF` o `#2B2E34` |
| Label de métrica                | Calibri                   | Regular | 9–10pt  | `#7B808A`               |

---

## LAYOUTS / TIPOS DE SLIDE

### 1. PORTADA

- Fondo: `#2B2E34` (o `#0E2841` para Plan IA)
- Título grande centrado o alineado izquierda, en blanco, 36–44pt Bold
- Subtítulo pequeño en gris claro
- Logo TSOFT arriba izquierda
- Métricas clave (si las hay) en fila inferior: número grande blanco + label gris
- Decoración: shapes triangulares o geométricos en `#E30613`

### 2. SLIDE DE CONTENIDO (el más común)

- Fondo: blanco o `#F5F6F8`
- Etiqueta de categoría arriba izquierda: `CATEGORÍA · SUBCATEGORÍA` en `#E30613`, 8pt, bold, uppercase
- Título en `#2B2E34`, 24–28pt, bold, máximo 2 líneas
- Subtítulo opcional en `#7B808A`, 12–13pt
- Contenido: cards, tabla, columnas — NUNCA bullets simples sobre fondo blanco

### 3. SLIDE DE SECCIÓN / SEPARADOR

- Fondo: `#2B2E34`
- Número de sección grande en `#E30613` (ej: `01`, `02`)
- Título en blanco, 32–40pt, bold
- Descripción corta opcional en gris claro

### 4. SLIDE DE MÉTRICAS

- Fondo: `#2B2E34` o blanco
- 3–5 métricas en fila: número grande (`+25 AÑOS`, `-65%`, `100%`) + label pequeño debajo
- Números en blanco (fondo oscuro) o `#E30613` / `#16A37A` según semántica
- Separadores verticales entre métricas

### 5. SLIDE DE TABLA

- Header: fondo `#2B2E34`, texto blanco, bold
- Filas: alternadas blanco / `#F5F6F8`
- Celda de estado: usar colores semánticos (verde/rojo/amarillo) con texto
- Columna "Crítico" o destacada: bold

### 6. SLIDE DE PROCESO / PASOS

- Numeración grande en `#E30613`: `01`, `02`, `03`, `04`
- Cada paso: título bold + descripción breve
- Distribución horizontal (timeline) o en grid 2×2
- Fondo blanco o `#F5F6F8`

### 7. SLIDE DE COMPARACIÓN / DOS COLUMNAS

- Título arriba
- Dos bloques lado a lado, cada uno con header de color diferente
- Usar `#2C5282` y `#16A37A` como colores de header de columna
- O `QUÉ SÍ` / `QUÉ NO` con verde/rojo

### 8. CIERRE / CTA

- Fondo: `#2B2E34`
- Frase grande y directa en blanco, con una palabra o frase clave en `#E30613`
- Llamado a la acción abajo
- Datos de contacto en footer

---

## ELEMENTOS VISUALES RECURRENTES

- **Shapes triangulares** en `#E30613` como decoración (esquinas, fondos de portada)
- **Tags de categoría** tipo pastilla: fondo `#E30613`, texto blanco, 8pt, rounded
- **Cards con borde superior** de color por categoría (4px top border)
- **Iconos simples** en círculos de color (`#E30613`, `#16A37A`, `#2C5282`)
- **Línea separadora** horizontal delgada en `#ECEDF0` entre secciones
- **Highlight de número** en rojo dentro de texto blanco (ej: `"que más le duele a BCI"` — "duele" en rojo)

---

## REGLAS QUE NUNCA SE ROMPEN

1. **Sin bullets genéricos** sobre fondo blanco vacío — siempre cards, tabla, steps o columnas
2. **Sin más de 2 fuentes** por slide
3. **Sin texto centrado en el cuerpo** — solo títulos de portada pueden centrarse
4. **La etiqueta de categoría siempre existe** en slides de contenido — aunque sea una sola palabra
5. **Portada y cierre siempre en oscuro** — el "sándwich" claro al medio
6. **Máximo 1 idea principal por slide** — si hay más contenido, más slides
7. **Los números grandes hablan primero** — si hay una métrica clave, que sea lo más grande del slide
8. **El rojo `#E30613` es solo para acentos** — no para fondos grandes ni texto de cuerpo

---

## CÓMO USAR ESTE ARCHIVO

Cuando me pases contenido para hacer una presentación, incluí este archivo y decime:

- Cuántos slides aproximadamente
- Si es TSOFT (fondo muy oscuro, estilo agresivo) o Plan IA (azul noche, más técnico)
- Si hay métricas, procesos, comparaciones o tablas en el contenido

Ejemplo de uso:

> "Tomá este contenido sobre el proceso de reclutamiento en TSOFT y hacé una presentación siguiendo el `ESTILO_TSOFT.md`"
