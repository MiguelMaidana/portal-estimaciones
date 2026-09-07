# Especificación Técnica (SDD) — Estimador de Historias de Usuario Asistido por IA

**Versión:** 1.3 — ver Historial de versiones (§0)
**Alcance:** POC (prueba de concepto) — el caso de uso/cliente concreto (Credicop u otro) se define después; esta especificación es agnóstica de cliente.
**Origen:** Reunión "Seguimiento del Plan de AI en ARG" — 3-sep-2026
**Estado:** Borrador para construcción con IA (Claude Code / agente de desarrollo)

> **Cómo leer este documento:** cada sección marca su origen entre corchetes.
> `[REUNIÓN]` = decisión o dato que surge directamente de la transcripción.
> `[PROPUESTA]` = decisión de diseño que la reunión no tomó y que se completa acá
> para que la especificación sea 100% construible. Requiere validación de negocio
> antes de pasar a producción, pero no bloquea la construcción del MVP.
> `[ABIERTO]` = punto que ninguna decisión técnica puede cerrar por sí sola —
> queda explícitamente fuera de esta especificación.
> `[NUEVO vX.Y]` = contenido agregado en la revisión vX.Y para cerrar un
> hueco detectado en una revisión de completitud posterior a la versión
> original. No cambia ninguna decisión `[REUNIÓN]` ya tomada, solo completa
> el diseño. El número de versión indica en qué revisión se agregó.

## 0. Historial de versiones `[NUEVO v1.1]`

| Versión | Fecha | Cambios |
|---|---|---|
| 1.0 | 2026-09-03 | Versión inicial, surgida de la reunión "Seguimiento del Plan de AI en ARG". |
| 1.1 | 2026-09-07 | Revisión de completitud pre-construcción. Cierra tres huecos técnicos: (1) falta de contrato de carga de imágenes en la API — §8, §9; (2) ausencia de modelo mínimo de autenticación/autorización — §5, §8; (3) falta de flujo de alta de datos maestros (cliente, matriz de sizing, período de consumo) — §14 nueva. No modifica ninguna decisión `[REUNIÓN]` existente. |
| 1.2 | 2026-09-07 | Agrega §16, guía de estilo visual del portal, traduciendo `ESTILO_TSOFT.md` (guía de identidad para presentaciones) a tokens y reglas aplicables a una app web, con mapeo explícito de colores semánticos a los estados de §6. |
| 1.3 | 2026-09-07 | Cierra dos puntos que quedaban totalmente en blanco: (1) §7.3 ahora incluye un prompt v1 completo del agente de calidad, en vez de delegar todo su diseño a la construcción; (2) §10 propone un umbral numérico de calibración por defecto. Ambos son `[PROPUESTA]` — un punto de partida a validar, no un valor definitivo. Los pesos de la matriz de sizing (§7.2) y el cliente concreto del POC siguen `[ABIERTO]` porque dependen de datos históricos reales y de una decisión organizacional, respectivamente — no se pueden cerrar responsablemente sin inventarlos. |

---

## 1. Resumen ejecutivo

Construir una consola, a modo de POC, donde un cliente (el caso de uso
concreto se define más adelante) carga una historia de usuario, un agente
valida su completitud y calidad, y —si está completa— el sistema
calcula un tamaño (XS/S/M/L/XL) mediante un cálculo **determinístico**
alimentado por criterios que una IA extrae de la historia. El tamaño acordado
descuenta puntos de una línea base mensual del cliente. `[REUNIÓN]`

El objetivo de negocio es migrar el modelo de cobro de "personas asignadas por
tiempo" a "consumo por historia de usuario entregada". `[REUNIÓN]`

## 2. Alcance

### Dentro de alcance (POC) `[PROPUESTA]`
- Un solo cliente/servicio configurado por instancia, pero **sin atarlo a
  Credicop ni a ningún caso de uso específico** — el modelo de datos soporta
  cualquier cliente/servicio que se decida usar como caso de prueba. `[decisión de este mensaje]`
- Una historia de usuario procesada por vez (sin análisis de paquetes de
  historias relacionadas). `[REUNIÓN]`
- Historias de usuario en texto, con soporte adicional de OCR best-effort
  para contenido en imágenes (ver §9 — no se garantiza 100% de precisión). `[decisión de este mensaje]`
- Flujo con validación humana obligatoria antes de responder al cliente
  (Fase 1). `[REUNIÓN]`
- Panel de consumo del cliente contra su línea base mensual.

### Fuera de alcance (Fase 2 o posterior) `[REUNIÓN]`
- Autogestión / respuesta inmediata sin intervención humana.
- Ejecución automática del desarrollo/certificación desde la consola.
- Soporte multi-cliente / multi-servicio simultáneo dentro de una misma
  instancia (se diseña el modelo de datos para soportarlo a futuro, pero el
  POC corre con un solo tenant configurado a la vez). `[PROPUESTA]`
- Análisis de paquetes de historias relacionadas entre sí.
- Garantía de precisión del OCR (queda como best-effort, ver §9).

## 3. Actores

| Actor | Rol | Origen |
|---|---|---|
| Cliente (caso de uso a definir) | Carga historias, ve sizing, acepta/rechaza, ve consumo | `[REUNIÓN]` |
| Líder del servicio | Valida/corrige el resultado antes de que llegue al cliente (Fase 1) | `[REUNIÓN]` |
| Equipo de delivery | Define y mantiene la matriz de sizing (fuera del sistema, vía archivo de configuración) | `[REUNIÓN]` |
| Agente de validación de calidad de HU | **No existe hoy** — se diseña y construye desde cero en este desarrollo (ver §7.3) | `[corrección de este mensaje]` |
| Motor de sizing | Combina extracción de criterios (IA) + cálculo determinístico (script) | `[REUNIÓN]` |

## 4. Arquitectura propuesta

Decisión explícita de la reunión: nada de frameworks agénticos pesados: llamar
al proveedor de IA directamente vía SDK. `[REUNIÓN]` Decisión de este mensaje:
monorepo, desplegado íntegramente en Vercel, con Supabase como base de datos —
todo en tier gratuito, dado que es un POC.

```
/monorepo
├── apps/
│   └── web/                 → Next.js (App Router): frontend + API routes,
│                               un solo proyecto Vercel (free tier)
├── packages/
│   ├── shared/               → tipos TypeScript y schemas (zod) compartidos
│   │                            entre frontend y backend
│   ├── quality-agent/        → prompt + lógica del agente de validación
│   │                            de calidad de HU (§7.3)
│   └── sizing-engine/        → extracción de criterios (IA) + cálculo
│                                determinístico contra la matriz (§7.1, §7.2)
└── supabase/
    └── migrations/           → esquema SQL versionado (Supabase CLI)
```

- **Frontend + Backend en un solo proyecto:** Next.js (App Router) con API
  routes, desplegado en Vercel (tier gratuito). No hace falta un backend
  separado ni otro hosting — simplifica el POC a un solo deploy.
- **Base de datos:** Supabase (Postgres administrado), tier gratuito. Se
  accede vía su cliente oficial o directamente por SQL/Prisma desde las API
  routes.
- **IA:** SDK oficial de Anthropic, llamado directo desde las API routes —
  sin frameworks agénticos intermedios. `[REUNIÓN]`
- **OCR:** Tesseract.js (open source, corre embebido en el propio backend,
  sin costo ni servicio externo) — ver §9.
- **Almacenamiento de imágenes `[NUEVO v1.1]`:** Supabase Storage (bucket
  `historias-imagenes`, tier gratuito), usado para persistir las imágenes
  adjuntas a una historia antes de correr OCR sobre ellas. Cada imagen queda
  referenciada por URL en `historia_usuario.imagenes_urls` (ver §5).
- **Autenticación `[NUEVO v1.1]`:** Supabase Auth (email/password, tier
  gratuito) para identificar a los actores `cliente` y `líder`. El rol y el
  `cliente_id` de cada usuario autenticado se resuelven server-side contra
  la tabla `usuario` (ver §5) a partir del token — ningún endpoint confía en
  un rol o identidad enviados en el body (ver §8).
- **Sin cola de mensajería ni orquestador** en el POC: cada paso del flujo se
  ejecuta de forma síncrona vía llamada a la API.
- Todo el stack se elige deliberadamente para no incurrir en costos durante
  la etapa de POC (Vercel free + Supabase free + Tesseract.js open source).

## 5. Modelo de datos `[PROPUESTA]`

```sql
-- Cliente / tenant (preparado para multi-cliente futuro, aunque el POC usa uno solo a la vez)
CREATE TABLE cliente (
  id                UUID PRIMARY KEY,
  nombre            TEXT NOT NULL,          -- nombre del cliente/caso de uso, configurable
  servicio          TEXT NOT NULL,          -- ej. 'QA', 'Desarrollo'
  linea_base_puntos INT NOT NULL,           -- puntos incluidos por mes
  activo            BOOLEAN DEFAULT TRUE
);

-- Usuario autenticado (vía Supabase Auth) — resuelve rol y cliente asociado [NUEVO v1.1]
CREATE TABLE usuario (
  id          UUID PRIMARY KEY REFERENCES auth.users(id),
  nombre      TEXT NOT NULL,
  rol         TEXT NOT NULL,                  -- 'cliente' | 'lider' | 'equipo_delivery'
  cliente_id  UUID REFERENCES cliente(id),    -- NULL si el rol no está atado a un cliente
  activo      BOOLEAN DEFAULT TRUE
);

-- Matriz de sizing versionada por servicio (el contenido lo define el equipo de delivery)
CREATE TABLE matriz_sizing (
  id          UUID PRIMARY KEY,
  cliente_id  UUID REFERENCES cliente(id),
  version     INT NOT NULL,
  criterios   JSONB NOT NULL,   -- ver §7.2 para el esquema
  umbrales    JSONB NOT NULL,   -- ver §7.2 para el esquema
  vigente_desde TIMESTAMP NOT NULL,
  creada_por  TEXT NOT NULL
);

-- Historia de usuario
CREATE TABLE historia_usuario (
  id                    UUID PRIMARY KEY,
  cliente_id            UUID REFERENCES cliente(id),
  texto_original         TEXT NOT NULL,
  texto_ocr              TEXT,            -- texto extraído de imágenes vía OCR, si aplica (ver §9)
  contiene_contenido_ocr BOOLEAN DEFAULT FALSE,
  imagenes_urls          JSONB,           -- URLs en Supabase Storage de las imágenes adjuntas [NUEVO v1.1]
  estado                TEXT NOT NULL,   -- ver §6 máquina de estados
  resultado_completitud TEXT,            -- 'completa' | 'incompleta'
  feedback_completitud  TEXT,            -- motivo si es incompleta
  sugerencias_mejora    JSONB,           -- salida del agente de calidad, ver §7.3
  criterios_extraidos   JSONB,           -- salida cruda de la IA, ver §7.1
  sizing_calculado      TEXT,            -- 'XS'|'S'|'M'|'L'|'XL'
  puntos_calculados     INT,
  sizing_validado_por   TEXT,
  sizing_validado_en    TIMESTAMP,
  aceptada_por_cliente  BOOLEAN,
  fecha_carga           TIMESTAMP NOT NULL DEFAULT now(),
  fecha_entrega         TIMESTAMP,
  matriz_sizing_id      UUID REFERENCES matriz_sizing(id)
);

-- Consumo mensual del cliente contra su línea base
CREATE TABLE consumo_mensual (
  id           UUID PRIMARY KEY,
  cliente_id   UUID REFERENCES cliente(id),
  periodo      DATE NOT NULL,  -- primer día del mes
  linea_base   INT NOT NULL,
  consumido    INT NOT NULL DEFAULT 0,
  disponible   INT GENERATED ALWAYS AS (linea_base - consumido) STORED
);

-- Auditoría (trazabilidad de cada evento sobre una historia)
CREATE TABLE log_auditoria (
  id           UUID PRIMARY KEY,
  historia_id  UUID REFERENCES historia_usuario(id),
  evento       TEXT NOT NULL,  -- 'cargada'|'completitud_evaluada'|'sizing_calculado'|'validada'|'aceptada'|'entregada'
  actor        TEXT NOT NULL,  -- 'sistema'|'cliente'|nombre del líder
  detalle      JSONB,
  timestamp    TIMESTAMP NOT NULL DEFAULT now()
);
```

`[NUEVO v1.1]` `sizing_validado_por` (en `historia_usuario`) y `actor` (en
`log_auditoria`) almacenan el `id` de `usuario` cuando el evento lo dispara
una persona autenticada, o el literal `'sistema'` cuando lo dispara un
proceso automático (ej. evaluación de completitud). Se resuelven siempre
desde la sesión autenticada (§8) — nunca desde un campo de texto libre
enviado en el body, a diferencia de lo que sugería el `body: { lider, ... }`
de la v1.0 de §8.

`[NUEVO v1.1]` El registro de `consumo_mensual` de un período se crea de
forma perezosa: la primera vez que se necesita para un `cliente_id` +
`periodo` dado (al cargar o al aceptar una historia) y no existe, el sistema
lo crea copiando `linea_base` desde `cliente.linea_base_puntos`, con
`consumido = 0`. No hace falta un proceso batch mensual en el POC.

## 6. Máquina de estados de una historia `[PROPUESTA]`

```
BORRADOR
  → EN_ANALISIS_COMPLETITUD
      → INCOMPLETA  (feedback al cliente, vuelve a BORRADOR al reenviar)
      → COMPLETA
          → EN_SIZING
              → SIZING_CALCULADO
                  → PENDIENTE_VALIDACION_LIDER   (Fase 1, obligatorio)
                      → SIZING_VALIDADO
                          → PENDIENTE_ACEPTACION_CLIENTE
                              → RECHAZADA_POR_CLIENTE (fin, sin descuento)
                              → ACEPTADA (descuenta línea base)
                                  → EN_EJECUCION   (fuera del sistema)
                                      → ENTREGADA (fin)
```

Reglas de transición clave `[REUNIÓN]`:
- El paso `PENDIENTE_VALIDACION_LIDER` es **obligatorio** en el POC — no existe
  camino directo de `SIZING_CALCULADO` a `PENDIENTE_ACEPTACION_CLIENTE`.
- El descuento de la línea base ocurre **solo** al pasar a `ACEPTADA`, nunca antes.
- `EN_EJECUCION` y `ENTREGADA` son actualizaciones manuales — el sistema no
  ejecuta ni certifica nada automáticamente.
- `EN_ANALISIS_COMPLETITUD` ejecuta la evaluación multi-dimensional completa
  del §7.3 (completitud, ambigüedad, buenas prácticas, INVEST, dependencias)
  — no es un único chequeo simple. Solo pasa a `COMPLETA` si **todas** las
  dimensiones cumplen; si falta una sola, el resultado es `INCOMPLETA`.

## 7. Motor de sizing

### 7.1 Extracción de criterios (componente generativo) `[PROPUESTA]`

La IA **no calcula el tamaño**. Solo lee la historia y devuelve criterios
estructurados en JSON. El contrato de salida se fuerza vía schema:

```json
{
  "complejidad_tecnica": "baja | media | alta",
  "menciona_integraciones": true,
  "integraciones_detectadas": ["string"],
  "ambiguedades_detectadas": ["string"],
  "cantidad_criterios_aceptacion_estimados": 0,
  "dependencias_externas": ["string"],
  "alerta_fuera_de_matriz": "string | null"
}
```

- `alerta_fuera_de_matriz`: si la IA detecta un aspecto de la historia que la
  matriz vigente no contempla (ej. menciona integraciones y la matriz no tiene
  ese criterio), lo señala acá — tal como se pidió explícitamente en la
  reunión ("fíjate que habla de integraciones y vos no tenés en la matriz
  nada que hable de integraciones"). `[REUNIÓN]`
- Este JSON queda persistido en `criterios_extraidos` para auditoría y para
  poder recalcular si la matriz cambia de versión.

### 7.2 Matriz de sizing (componente determinístico) `[PROPUESTA — estructura;
los valores reales deben ser definidos y validados por el equipo de delivery]`

La matriz traduce los criterios extraídos en un puntaje, y el puntaje en un
tamaño. Estructura propuesta (ejemplo con valores de muestra, **no
definitivos**):

```json
{
  "pesos": {
    "complejidad_tecnica": { "baja": 1, "media": 3, "alta": 5 },
    "por_integracion_detectada": 2,
    "por_ambiguedad_detectada": 1,
    "por_dependencia_externa": 2,
    "por_criterio_aceptacion": 0.5
  },
  "umbrales_tamano": [
    { "tamano": "XS", "puntos_max": 3 },
    { "tamano": "S",  "puntos_max": 6 },
    { "tamano": "M",  "puntos_max": 10 },
    { "tamano": "L",  "puntos_max": 16 },
    { "tamano": "XL", "puntos_max": null }
  ]
}
```

Algoritmo determinístico (pseudocódigo):

```
puntos = pesos.complejidad_tecnica[criterios.complejidad_tecnica]
puntos += len(criterios.integraciones_detectadas) * pesos.por_integracion_detectada
puntos += len(criterios.ambiguedades_detectadas) * pesos.por_ambiguedad_detectada
puntos += len(criterios.dependencias_externas) * pesos.por_dependencia_externa
puntos += criterios.cantidad_criterios_aceptacion_estimados * pesos.por_criterio_aceptacion

tamano = primer umbral cuyo puntos_max >= puntos (o XL si ninguno aplica)
```

Este cálculo corre en un script determinístico del backend — **nunca** se le
pide a la IA que devuelva el tamaño final. `[REUNIÓN — principio explícito]`

`[ABIERTO]` Los valores reales de pesos y umbrales no pueden definirse en esta
especificación: dependen del criterio de negocio del equipo de delivery
(Juan Cruz / Diego Canosa / Conde Z), que a la fecha de la reunión seguía en
proceso. La estructura de arriba es funcional para el MVP con valores de
ejemplo; deben reemplazarse antes de usar resultados reales con el cliente.

### 7.3 Agente de validación de calidad de HU (antes llamado "semáforo")

**Corrección importante:** no existe hoy ningún prompt ni agente armado para
esto — no hay un activo previo que reutilizar. Diseñar y construir este
agente **es parte del alcance de este desarrollo**, no una integración con
algo ya existente. `[corrección de este mensaje respecto de la versión anterior]`

La historia debe estar **100% completa en todas las dimensiones** evaluadas
antes de poder pasar al motor de sizing — no existe un sizing parcial o
"tentativo" sobre una historia con dimensiones pendientes. `[instrucción explícita de este mensaje]`

#### Dimensiones que el agente debe evaluar `[PROPUESTA — a validar/afinar durante la construcción, ya que no hay definición previa]`

1. **Completitud** — ¿la historia tiene los elementos mínimos (rol, acción,
   beneficio, contexto suficiente para ser entendida sin preguntas adicionales)?
2. **Ambigüedad** — ¿hay frases, condiciones o requisitos que admiten más de
   una interpretación razonable?
3. **Buenas prácticas de redacción** — ¿sigue una forma reconocible (ej.
   "Como \<rol\>, quiero \<acción\>, para \<beneficio\>")? ¿es atómica (no
   mezcla varias funcionalidades distintas en una sola historia)?
4. **Calidad de arquitectura de la HU** (criterios INVEST): Independiente,
   Negociable, Valiosa, Estimable, Small/acotada, Testeable.
5. **Dependencias** — ¿declara dependencias con otras historias o sistemas
   externos? ¿esas dependencias están resueltas o siguen abiertas/bloqueantes?

#### Contrato de entrada/salida

`[NUEVO v1.3]` El modelo **no** devuelve el campo `completa` — solo evalúa
las dimensiones. `completa` lo calcula el servidor de forma determinística
(T3.2), con la misma lógica de "nunca confiar en la IA para la decisión
final" que ya aplica en §7.2 al sizing. El campo se agrega recién cuando el
sistema persiste el resultado.

```json
// Input
{
  "historia_texto": "string",       // texto_original + texto_ocr si aplica
  "contiene_contenido_ocr": false
}

// Output crudo del modelo (sin "completa")
{
  "dimensiones": {
    "completitud":                 { "cumple": true, "detalle": "string" },
    "ambiguedad":                  { "cumple": true, "detalle": "string" },
    "buenas_practicas_redaccion":  { "cumple": true, "detalle": "string" },
    "arquitectura_invest": {
      "independiente": true,
      "negociable":    true,
      "valiosa":       true,
      "estimable":     true,
      "acotada":       true,
      "testeable":     true,
      "detalle": "string"
    },
    "dependencias": {
      "cumple": true,
      "detalle": "string",
      "dependencias_detectadas": ["string"]
    }
  },
  "sugerencias_mejora": ["string"],
  "feedback_resumen": "string"
}
```

El sistema agrega `completa` al persistir: `true` **solo si** todas las
claves `cumple` (y los seis booleanos de `arquitectura_invest`) son `true`.
Si cualquiera es `false`, la historia queda en estado `INCOMPLETA` y el
sistema devuelve `sugerencias_mejora` + `feedback_resumen`, señalando
puntualmente qué dimensión falló y por qué — no un mensaje genérico.

#### Prompt v1 `[PROPUESTA v1.3 — punto de partida a validar/afinar contra
el golden set de T3.4; no es un valor definitivo, pero deja de estar en
blanco]`

```
Sos un evaluador experto de historias de usuario para un equipo de
desarrollo de software. Tu única tarea es evaluar la historia de usuario
que te paso a continuación en las siguientes 5 dimensiones, sin opinar
sobre nada que no se te pida, y devolver el resultado ÚNICAMENTE en el
formato JSON indicado al final — sin texto antes ni después, sin markdown,
sin explicaciones adicionales fuera del JSON.

HISTORIA A EVALUAR:
"""
{{historia_texto}}
"""

{{#if contiene_contenido_ocr}}
Nota: parte de este texto proviene de reconocimiento óptico de caracteres
(OCR) sobre una imagen adjunta y puede contener errores de transcripción.
Tené esto en cuenta al evaluar ambigüedad y completitud: si una frase parece
corrupta o sin sentido, señalalo como ambigüedad en vez de asumir que la
historia está mal escrita.
{{/if}}

DIMENSIONES A EVALUAR:

1. COMPLETITUD: ¿la historia tiene rol, acción y beneficio identificables, y
   contexto suficiente para que un desarrollador la entienda sin tener que
   hacer preguntas adicionales? Si falta alguno de estos tres elementos, o
   el contexto es insuficiente, marcá `cumple: false` y explicá qué falta en
   `detalle`.

2. AMBIGÜEDAD: ¿hay frases, condiciones o requisitos que admiten más de una
   interpretación razonable? Ejemplos: "el sistema debe ser rápido" (sin
   definir qué es rápido), "en algunos casos" (sin especificar cuáles),
   verbos vagos como "gestionar" o "procesar" sin detallar qué acción
   concreta implican. Si encontrás alguna, marcá `cumple: false` y listalas
   en `detalle`.

3. BUENAS_PRACTICAS_REDACCION: ¿la historia sigue una forma reconocible tipo
   "Como <rol>, quiero <acción>, para <beneficio>" (no exige literalidad,
   pero sí que las tres partes estén identificables)? ¿es atómica, es decir,
   no mezcla dos o más funcionalidades independientes en una sola historia?
   Si mezcla funcionalidades o no tiene estructura identificable, marcá
   `cumple: false`.

4. ARQUITECTURA_INVEST: evaluá cada uno de los 6 criterios INVEST como
   booleano independiente:
   - independiente: ¿puede desarrollarse sin depender de que otra historia
     se implemente primero (más allá de dependencias externas declaradas)?
   - negociable: ¿describe un qué y no impone una única forma de
     implementación (un cómo)?
   - valiosa: ¿el beneficio para el usuario/negocio es explícito y
     entendible?
   - estimable: ¿hay información suficiente como para que un equipo técnico
     dé una estimación de esfuerzo razonable?
   - acotada (small): ¿es lo bastante chica como para completarse en una
     iteración normal de trabajo, sin necesitar dividirse?
   - testeable: ¿se puede verificar objetivamente si quedó bien
     implementada (aunque no haya criterios de aceptación explícitos aún)?

5. DEPENDENCIAS: ¿la historia menciona o implica dependencias con otras
   historias, sistemas externos o equipos? Si las hay, listalas en
   `dependencias_detectadas`. Marcá `cumple: false` únicamente si esas
   dependencias están bloqueantes y sin resolver (ej. "esto no se puede
   hacer hasta que el equipo X entregue Y" sin indicar que ya está
   resuelto). Si no hay dependencias, o las que hay ya están resueltas,
   marcá `cumple: true`.

REGLAS IMPORTANTES:
- No inventes información que la historia no tiene para "completarla" vos
  mismo — tu trabajo es señalar qué falta, no rellenarlo.
- `sugerencias_mejora` debe ser específico por dimensión fallida (ej. "Falta
  indicar qué significa 'rápido' en el criterio de rendimiento", nunca algo
  genérico como "mejorar la historia").
- `feedback_resumen` es un párrafo corto (2 a 4 líneas) dirigido al cliente
  que cargó la historia, en tono profesional y constructivo.
- No calcules ni menciones tamaño, puntos ni esfuerzo — eso lo hace otro
  proceso y no es tu tarea.

FORMATO DE SALIDA (JSON estricto, sin el campo "completa"):
{
  "dimensiones": {
    "completitud":                { "cumple": boolean, "detalle": "string" },
    "ambiguedad":                 { "cumple": boolean, "detalle": "string" },
    "buenas_practicas_redaccion": { "cumple": boolean, "detalle": "string" },
    "arquitectura_invest": {
      "independiente": boolean, "negociable": boolean, "valiosa": boolean,
      "estimable": boolean, "acotada": boolean, "testeable": boolean,
      "detalle": "string"
    },
    "dependencias": {
      "cumple": boolean, "detalle": "string",
      "dependencias_detectadas": ["string"]
    }
  },
  "sugerencias_mejora": ["string"],
  "feedback_resumen": "string"
}
```

Este prompt es el punto de partida para T3.1 — se ajusta iterando contra el
golden set de T3.4, no se congela de entrada. La notación `{{historia_texto}}`
/ `{{#if}}` es pseudocódigo ilustrativo para mostrar dónde va la interpolación
y la sección condicional — no impone ninguna librería de templating
particular; alcanza con construir el string en código.

## 8. Contratos de API `[PROPUESTA]`

`[NUEVO v1.1]` Todos los endpoints, salvo que se indique lo contrario,
requieren header `Authorization: Bearer <token de Supabase Auth>`. El
servidor resuelve `rol` y `cliente_id` contra la tabla `usuario` (§5) a
partir del token — ningún endpoint acepta un rol o identidad enviados en el
body. Sin token válido: `401`. Con token válido pero rol/cliente incorrecto
para la acción: `403`.

```
POST   /api/historias
  content-type: multipart/form-data                    [NUEVO v1.1]
  campos: cliente_id, texto_original, imagenes[] (0..n archivos jpg/png, opcional)
  → si hay imagenes[], se suben a Supabase Storage y se dispara OCR (§9)
  → crea historia en estado BORRADOR, dispara análisis de completitud
  → response: { id, estado, resultado_completitud, feedback_completitud, contiene_contenido_ocr }

GET    /api/historias/:id
  → response: historia completa con estado actual

POST   /api/historias/:id/reenviar
  content-type: multipart/form-data                    [NUEVO v1.1]
  campos: texto_original, imagenes[] (opcional, mismo tratamiento que en la creación)
  → solo válido si estado == INCOMPLETA
  → vuelve a disparar análisis de completitud

POST   /api/historias/:id/calcular-sizing
  → solo válido si estado == COMPLETA
  → ejecuta extracción de criterios + cálculo determinístico
  → pasa a estado SIZING_CALCULADO → PENDIENTE_VALIDACION_LIDER

POST   /api/historias/:id/validar
  body: { aprobado: boolean, sizing_corregido?: string }
  → solo accesible por un usuario con rol == 'lider'   [NUEVO v1.1: identidad
    resuelta desde el token, reemplaza al campo `lider` del body en la v1.0]
  → pasa a SIZING_VALIDADO o vuelve a EN_SIZING si se corrige

POST   /api/historias/:id/aceptar
  body: { aceptado: boolean }
  → solo accesible por un usuario con rol == 'cliente' cuyo cliente_id
    coincida con el de la historia                      [NUEVO v1.1]
  → solo válido si estado == PENDIENTE_ACEPTACION_CLIENTE
  → si aceptado: descuenta línea base (crea consumo_mensual del período si
    no existe, ver §5) y pasa a ACEPTADA
  → si no: pasa a RECHAZADA_POR_CLIENTE

POST   /api/historias/:id/entregar
  → solo válido si estado == ACEPTADA / EN_EJECUCION
  → pasa a ENTREGADA, registra fecha_entrega

GET    /api/clientes/:id/consumo?periodo=YYYY-MM
  → response: { linea_base, consumido, disponible, historias: [...] }
```

Cada endpoint escribe un registro en `log_auditoria`.

## 9. Historias con imágenes o diagramas (OCR best-effort)

Limitación reconocida en la reunión: analizar imágenes/diagramas dentro de
una historia es una debilidad conocida de este tipo de agentes. `[REUNIÓN]`
Decisión de este mensaje: se incorpora OCR para intentar extraer texto de
imágenes adjuntas, **asumiendo explícitamente que no va a funcionar al
100%**.

Flujo propuesto:
1. Si la historia incluye imágenes adjuntas, estas se suben primero a
   Supabase Storage (bucket `historias-imagenes`) y sus URLs quedan en
   `imagenes_urls` `[NUEVO v1.1]`; luego se ejecuta OCR (Tesseract.js) sobre
   cada una al momento de la carga.
2. El texto extraído se guarda en `texto_ocr` (separado de `texto_original`,
   nunca mezclado sin trazabilidad) y se marca `contiene_contenido_ocr = true`.
3. El agente de validación de calidad (§7.3) recibe `texto_original +
   texto_ocr` concatenado, pero el sistema **siempre deriva a revisión
   manual del líder** cualquier historia con `contiene_contenido_ocr = true`,
   incluso si el agente la marca como `completa` — dado que no hay garantía
   de que el OCR haya extraído correctamente el contenido de la imagen. `[mitigación de riesgo — decisión de este mensaje]`
4. La interfaz debe mostrarle al líder tanto el texto original como el texto
   OCR por separado, para que pueda verificar contra la imagen fuente si
   hace falta.

`[ABIERTO]` La precisión real del OCR sobre diagramas técnicos (a diferencia
de texto simple en una foto) es baja por naturaleza — este punto no se
resuelve con más ingeniería, es una limitación conocida y aceptada del POC.

## 10. Protocolo de calibración (riesgo de fiabilidad estadística) `[PROPUESTA]`

En la reunión se planteó el riesgo central del proyecto: que la misma
historia dé resultados distintos en corridas distintas, y que haya que
"estresar" la herramienta antes de confiar en ella. `[REUNIÓN]` Protocolo
propuesto para cerrar ese riesgo antes de pasar a producción con el cliente:

1. Tomar un set de al menos 20 historias reales ya estimadas históricamente
   por el equipo (sin IA), con su tamaño/tiempo real conocido.
2. Correr cada historia 3 veces por el motor de sizing y registrar la
   dispersión de resultados.
3. Definir un umbral de variación aceptable. `[PROPUESTA v1.3 — punto de
   partida para T9.3, requiere validación/ajuste del líder del servicio
   antes de habilitar producción; no es una cifra definitiva]`: como
   default, se considera aceptable si el tamaño calculado no varía en más
   de un nivel de la escala (ej. S↔M) en más del 20% de las corridas
   repetidas sobre la misma historia, y si el error promedio del puntaje
   calculado contra el tiempo/costo real histórico (paso 4) no supera ±30%.
   El apetito de riesgo real depende del negocio, no de una decisión
   técnica — este valor es un piso para poder correr T9.2–T9.4, sujeto a
   que el líder del servicio lo ajuste.
4. Comparar el tamaño calculado contra el tiempo/costo real histórico y medir
   error promedio.
5. No habilitar el flujo para el cliente real hasta que el resultado del
   punto 4 esté dentro de un margen aceptado por el líder del servicio.

## 11. Integración con otras plataformas

Hubo desacuerdo en la reunión sobre si esta herramienta debía integrarse a la
plataforma "TAI" que se está construyendo en paralelo, o quedar separada.
`[REUNIÓN]` **Decidido:** va a ser una plataforma aislada, standalone, con su
propia API REST. `[decisión de este mensaje]` No se integra con "TAI" ni con
ninguna otra plataforma en esta etapa. Como igual expone contratos de API
bien definidos (§8), queda técnicamente disponible para una integración
futura si se decidiera más adelante, aunque eso no es un objetivo del POC.

## 12. Fuera de esta especificación (decisiones organizacionales)

- **Decidido:** el desarrollo lo hace el equipo de Lean. `[decisión de este mensaje]`
- **Sigue abierto** `[ABIERTO]`: prioridad relativa de esta iniciativa frente
  a otras en curso (colegio de abogados, plugin de QA) — no es una decisión
  técnica.
- **Sigue abierto** `[ABIERTO]`: el "gris" señalado por Miguel Maidana sobre
  si las estimaciones de desarrollo ya asumen uso de IA en la ejecución — es
  un tema metodológico de cómo se comunican las estimaciones a los clientes,
  no un requisito del sistema.

## 13. Criterios de aceptación consolidados (Given/When/Then)

### Escenario: Historia incompleta
- **Dado** que el cliente carga una historia de usuario
- **Cuando** el agente de completitud determina que falta información
- **Entonces** el sistema devuelve `estado = INCOMPLETA` con el feedback específico, y la historia no avanza a sizing

### Escenario: Sizing calculado de forma determinística
- **Dado** que una historia está en estado `COMPLETA`
- **Cuando** se invoca `POST /historias/:id/calcular-sizing`
- **Entonces** el sistema persiste `criterios_extraidos` (salida de la IA) y calcula `sizing_calculado` mediante el script de la matriz vigente — nunca mediante una respuesta libre del modelo

### Escenario: Alerta de criterio fuera de matriz
- **Dado** que la IA detecta un aspecto de la historia no contemplado en la matriz vigente (ej. una integración)
- **Cuando** se ejecuta la extracción de criterios
- **Entonces** el campo `alerta_fuera_de_matriz` queda registrado y visible para el líder en la etapa de validación

### Escenario: Validación obligatoria del líder
- **Dado** que una historia está en `SIZING_CALCULADO`
- **Cuando** el sistema la deriva a `PENDIENTE_VALIDACION_LIDER`
- **Entonces** ningún cliente puede ver el resultado hasta que un líder del servicio lo apruebe o lo corrija explícitamente

### Escenario: Descuento de línea base solo tras aceptación
- **Dado** que el cliente ve un sizing validado
- **Cuando** el cliente acepta la estimación
- **Entonces** el sistema descuenta los puntos correspondientes de `consumo_mensual` y no antes de ese momento

### Escenario: Historia incompleta en una sola dimensión
- **Dado** que una historia cumple 4 de las 5 dimensiones evaluadas (ej. falla solo en "ambigüedad")
- **Cuando** el agente de validación de calidad la evalúa
- **Entonces** el resultado es `completa = false`, y el sistema no avanza la historia a sizing aunque el resto de las dimensiones esté correcto

### Escenario: Sugerencias de mejora específicas por dimensión
- **Dado** que una historia resulta incompleta
- **Cuando** el sistema devuelve el feedback al cliente
- **Entonces** `sugerencias_mejora` indica puntualmente qué dimensión falló y por qué, no un mensaje genérico tipo "corregir la historia"

### Escenario: Historia con contenido proveniente de OCR
- **Dado** que una historia incluye imágenes y el sistema extrajo texto vía OCR
- **Cuando** el agente de validación de calidad marca la historia como `completa = true`
- **Entonces** el sistema igual la deriva a revisión manual del líder antes de continuar al motor de sizing, mostrando el texto original y el texto OCR por separado

## 14. Administración de datos maestros (alta de cliente, matriz de sizing, período de consumo) `[NUEVO v1.1]`

El POC es de un solo tenant a la vez (§2), por lo que no hace falta un panel
de administración completo — alcanza con un mecanismo mínimo y auditable:

1. **Alta de `cliente`:** se crea mediante un script de seed
   (`supabase/seed/cliente.ts` o similar) ejecutado manualmente por el
   equipo de delivery al configurar una instancia del POC para un caso de
   uso concreto. No requiere endpoint ni UI en el POC.
2. **Alta/actualización de `matriz_sizing`:** el equipo de delivery mantiene
   pesos y umbrales (§7.2) en un archivo de configuración JSON versionado en
   el repo (`packages/sizing-engine/matrices/<cliente>.json`), tal como ya
   establece §3 ("vía archivo de configuración"). Un script
   (`scripts/cargar-matriz.ts`) lee ese archivo y crea una nueva fila en
   `matriz_sizing` con `version` incrementada y `vigente_desde = now()`. Las
   versiones anteriores nunca se editan ni se borran — quedan como historial
   para poder recalcular sizing de historias viejas.
3. **Alta de `consumo_mensual`:** no requiere alta manual — se crea de forma
   perezosa según §5, la primera vez que un `cliente_id` necesita un
   registro para el período en curso.

`[ABIERTO]` Si el POC pasa a producción con múltiples clientes simultáneos,
este mecanismo de scripts manuales deja de alcanzar y hace falta un panel de
administración real — queda fuera de alcance de esta especificación.

## 15. Puntos que siguen abiertos y bloquean producción (no bloquean construcción del POC)

Estos son puntos que **no se pueden cerrar responsablemente en una
especificación técnica**, porque no tienen una respuesta técnica correcta:
dependen de datos que todavía no existen o de una decisión que le
corresponde al negocio, no al diseño del sistema. Inventar un valor acá
sería peor que dejarlo marcado, porque generaría una falsa sensación de
certeza sobre algo que puede terminar afectando la facturación real a un
cliente.

- Valores reales de pesos y umbrales de la matriz de sizing (§7.2) — la
  estructura y el algoritmo están 100% definidos y son construibles; lo que
  falta son los *números*, que solo pueden salir de datos históricos reales
  del equipo de delivery (ver T9.1–T9.4).
- Precisión real del OCR sobre contenido gráfico/diagramas (§9) — no es un
  vacío de diseño, es una limitación física conocida del enfoque
  (Tesseract.js sobre diagramas), no resoluble con más ingeniería.
- Prioridad de esta iniciativa frente a otras en curso — decisión
  organizacional, ajena al sistema.
- Caso de uso/cliente concreto sobre el cual se va a correr el POC (Credicop
  u otro) — decisión organizacional, ajena al sistema.

**Ya no están en blanco, pero siguen pendientes de validación de negocio
`[NUEVO v1.3]`:** el umbral de calibración (§10) y el prompt del agente de
calidad (§7.3) ahora tienen una propuesta concreta de partida en la spec —
dejaron de ser "a definir en la construcción" para pasar a ser "a validar e
iterar", que es la naturaleza normal de un prompt o de un umbral de riesgo
(nunca se congelan sin probarlos contra casos reales, aun cuando estén
"cerrados" en la spec).

**Ya resuelto en esta iteración** (no bloquea): stack técnico (monorepo,
Vercel, Supabase, todo free tier), asignación al equipo de Lean, la decisión
de que sea una plataforma aislada sin integración con TAI, y —desde la
v1.1— el contrato de carga de imágenes, el modelo mínimo de
autenticación/autorización y el flujo de alta de datos maestros.

## 16. Guía de estilo visual del portal (referencia: `ESTILO_TSOFT.md`) `[NUEVO v1.2]`

`ESTILO_TSOFT.md` es una guía de identidad **para presentaciones/slides**
(portada, cierre, numeración de slide, footer con tagline), no una guía de
UI de aplicación web. Se toma como base de identidad de marca, pero no se
aplica literalmente — esta sección traduce lo aprovechable al contexto del
portal y aclara qué no corresponde.

**Se adopta tal cual:**
- Paleta de colores completa (principales, de soporte y semánticos) y
  tipografía (Calibri/Inter para UI, JetBrains Mono/Consolas para
  contenido técnico como JSON de auditoría).
- Regla "sin bullets genéricos": las vistas de completitud (§7.3), los
  criterios extraídos (§7.1) y las sugerencias de mejora se muestran en
  cards/tablas, nunca como una lista simple.
- El rojo `#E30613` se usa solo como acento (botones primarios, énfasis),
  nunca como fondo grande ni color de texto de cuerpo — regla explícita de
  la guía.

**Se reinterpreta para el portal (mapeo de colores semánticos → estados de
§6):**

| Estado de la historia | Color semántico | Hex |
|---|---|---|
| `BORRADOR`, `EN_ANALISIS_COMPLETITUD`, `EN_SIZING` | Azul (neutral / en progreso) | `#2C5282` |
| `INCOMPLETA`, `PENDIENTE_VALIDACION_LIDER`, `PENDIENTE_ACEPTACION_CLIENTE` | Amarillo (pendiente / requiere acción) | `#F5A524` |
| `SIZING_CALCULADO`, `SIZING_VALIDADO` | Azul (referencia) | `#2C5282` |
| `ACEPTADA`, `EN_EJECUCION`, `ENTREGADA` | Verde (confirmado / positivo) | `#16A37A` |
| `RECHAZADA_POR_CLIENTE` | Rojo oscuro (bloqueado / fin negativo) | `#A11820` |

**No aplica al portal** (son conceptos de deck, no de app web): numeración
de slide, layouts de "portada"/"cierre"/"sección separadora", shapes
triangulares decorativos, footer con logo + tagline en cada pantalla.

`[ABIERTO]` La implementación concreta (Tailwind config / design tokens CSS)
no se define en esta especificación — queda a criterio de quien construya
el frontend (T8.1), usando esta tabla y la paleta de `ESTILO_TSOFT.md` como
única fuente de valores de color.
