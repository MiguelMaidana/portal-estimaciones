# Backlog de tareas atómicas — Estimador de Historias de Usuario (POC)

**Fuente:** `SPEC_estimador-historias-poc.md` v1.3
**Alineación:** las tareas marcadas `[NUEVO v1.1]` cubren los tres agregados
de la spec v1.1 (contrato de carga de imágenes, autenticación/autorización
mínima, alta de datos maestros). Las marcadas `[NUEVO v1.2]` cubren la guía
de estilo del portal (§16, basada en `ESTILO_TSOFT.md`). Las marcadas
`[NUEVO v1.3]` reflejan que el prompt de calidad (§7.3) y el umbral de
calibración (§10) ahora parten de una propuesta concreta en vez de estar en
blanco.
**Cómo usar este backlog:** cada tarea es independiente, tiene su propio
Definition of Done y referencia a la sección de la spec que la respalda.
Pasále al agente de desarrollo la spec completa + una tarea a la vez —
nunca varias juntas — y validá contra el DoD antes de pasar a la siguiente.
El orden entre épicas respeta dependencias reales (una épica no arranca
antes de que la anterior esté cerrada), salvo donde se indica que puede
paralelizarse.

---

## EPIC 0 — Setup e infraestructura
*Bloquea todo lo demás. Referencia: §4, §5*

### T0.1 — Estructura del monorepo
Crear la estructura de carpetas de §4 (`apps/web`, `packages/shared`,
`packages/quality-agent`, `packages/sizing-engine`, `supabase/migrations`)
con workspaces configurados (npm/pnpm workspaces).
- **DoD:** estructura creada, `package.json` raíz con workspaces, cada
  paquete con su propio `package.json` mínimo, README con pasos de setup local.

### T0.2 — Proyectos Vercel y Supabase (free tier)
Crear el proyecto en Vercel y el proyecto en Supabase, conectar variables de
entorno entre ambos. `[NUEVO v1.1]` incluye habilitar Supabase Auth
(email/password) y crear el bucket de Supabase Storage `historias-imagenes`.
- **DoD:** `.env.example` documentado con todas las variables necesarias
  (Supabase URL/key, Anthropic API key), deploy vacío en Vercel funcionando,
  conexión a Supabase verificada con una query de prueba, bucket
  `historias-imagenes` creado y accesible, Supabase Auth habilitado.

### T0.3 — Migración SQL inicial
Escribir y aplicar la migración con las 6 tablas de §5 (`cliente`,
`usuario` `[NUEVO v1.1]`, `matriz_sizing`, `historia_usuario`,
`consumo_mensual`, `log_auditoria`), incluyendo los campos `texto_ocr`,
`contiene_contenido_ocr`, `imagenes_urls` `[NUEVO v1.1]` y
`sugerencias_mejora` en `historia_usuario`.
- **DoD:** migración versionada en `supabase/migrations`, aplicada en el
  proyecto Supabase, tipos de columnas verificados 1:1 contra §5, `usuario.id`
  referencia correctamente a `auth.users(id)`.

### T0.4 — Script de alta de datos maestros `[NUEVO v1.1]`
Referencia: §14. Scripts de seed/carga: `supabase/seed/cliente.ts` (alta de
`cliente`) y `scripts/cargar-matriz.ts` (lee un JSON de
`packages/sizing-engine/matrices/<cliente>.json` y crea una nueva versión de
`matriz_sizing`).
- **DoD:** correr ambos scripts contra una base de test deja un `cliente` y
  una `matriz_sizing` vigente listos para usar; correr `cargar-matriz.ts` dos
  veces crea dos versiones distintas sin pisar ni borrar la anterior.

---

## EPIC 1 — Tipos compartidos y capa de datos
*Depende de EPIC 0. Referencia: §5, §7.1, §7.3, §8*

### T1.1 — Tipos y schemas compartidos
En `packages/shared`, definir tipos TypeScript + schemas `zod` para las 6
tablas de §5 (incluye `usuario` `[NUEVO v1.1]`), y para los dos contratos
JSON de la spec: salida cruda del agente de calidad —sin `completa`,
ver §7.3 `[NUEVO v1.3]`— y salida de extracción de criterios (§7.1). Definir
también el tipo persistido de `historia_usuario`, que sí incluye `completa`
una vez que T3.2 lo calcula.
- **DoD:** cada schema `zod` valida correctamente los ejemplos de JSON que
  aparecen literalmente en la spec (usarlos como fixtures de test).

### T1.2 — Repositorio de datos para `historia_usuario`
Funciones de acceso a datos: crear, leer por id, actualizar estado y campos
relacionados (sizing, validación, aceptación, entrega, `imagenes_urls`
`[NUEVO v1.1]`).
- **DoD:** funciones con test unitario contra una base de test o mock de
  Supabase; ninguna función escribe SQL suelto fuera de esta capa.

### T1.3 — Middleware de resolución de identidad `[NUEVO v1.1]`
Referencia: §5, §8. Función/middleware que, dado el token de Supabase Auth
de la request, resuelve `usuario.rol` y `usuario.cliente_id` contra la
tabla `usuario`. Rechaza con `401` si no hay token válido.
- **DoD:** test que verifica resolución correcta de rol/cliente para un
  token válido, `401` sin token o con token inválido, y que ningún handler
  de API confía en un campo de rol/identidad enviado en el body.

---

## EPIC 2 — Máquina de estados
*Depende de EPIC 1. Referencia: §6*

### T2.1 — Módulo puro de transiciones de estado
Implementar la máquina de estados de §6 como módulo puro (sin I/O): dado un
estado actual y un evento, devuelve el siguiente estado o rechaza la
transición.
- **DoD:** un test por cada flecha del diagrama de §6; cualquier transición
  no listada en el diagrama lanza un error explícito (no falla silenciosamente).

### T2.2 — Registro de auditoría por transición
Cada cambio de estado exitoso escribe un registro en `log_auditoria` con
evento, actor y timestamp.
- **DoD:** test que verifica que toda transición de T2.1 genera exactamente
  un registro de auditoría correspondiente.

---

## EPIC 3 — Agente de validación de calidad de HU
*Puede arrancar en paralelo con EPIC 2. Referencia: §7.3*

### T3.1 — Prompt inicial de las 5 dimensiones
Partir del prompt v1 de §7.3 `[NUEVO v1.3]` (completitud, ambigüedad,
buenas prácticas de redacción, arquitectura INVEST y dependencias, salida
JSON sin `completa`) y ajustarlo iterando contra el golden set de T3.4 —no
es un prompt para escribir desde cero, sino para validar y afinar.
- **DoD:** función callable `evaluarCalidadHU(historia_texto)` que devuelve
  un JSON validado contra el schema de T1.1.

### T3.2 — Lógica de agregación `completa`
`completa = true` solo si **todas** las claves `cumple` y los 6 booleanos de
`arquitectura_invest` son `true`.
- **DoD:** tests unitarios: todas pasan → `true`; una sola dimensión falla →
  `false`; los 6 de INVEST pasan pero falla `dependencias` → `false`.

### T3.3 — Sugerencias de mejora específicas por dimensión
Generar `sugerencias_mejora` y `feedback_resumen` que identifiquen
puntualmente qué dimensión falló y por qué.
- **DoD:** cubre el escenario Given/When/Then "sugerencias de mejora
  específicas por dimensión" de §13 — el feedback no puede ser un mensaje
  genérico tipo "corregir la historia".

### T3.4 — Golden set de historias para regresión del prompt
Armar y documentar un set de al menos 10 historias de prueba: completas,
incompletas en cada dimensión por separado, ambiguas, con dependencias
bloqueantes.
- **DoD:** set versionado en el repo (ej. `packages/quality-agent/fixtures`),
  usado como test de regresión cada vez que se ajusta el prompt.

---

## EPIC 4 — Motor de sizing: extracción de criterios
*Depende de EPIC 3 (reutiliza el mismo tipo de llamado a IA). Referencia: §7.1*

### T4.1 — Extracción de criterios para sizing
Función que, dada una historia ya marcada `completa`, devuelve el JSON de
`criterios_extraidos` (complejidad técnica, integraciones, ambigüedades,
dependencias externas, cantidad de criterios de aceptación, alerta fuera de
matriz).
- **DoD:** output validado contra schema; test específico que verifica que
  `alerta_fuera_de_matriz` se completa cuando la historia menciona un
  aspecto no contemplado en la matriz de ejemplo de §7.2 (cubre el
  escenario "Alerta de criterio fuera de matriz" de §13).

---

## EPIC 5 — Motor de sizing: cálculo determinístico
*Depende de EPIC 4. Referencia: §7.2*

### T5.1 — Carga de matriz vigente
Función que devuelve la versión activa de `matriz_sizing` para un cliente.
- **DoD:** test con múltiples versiones cargadas, verifica que trae siempre
  la de `vigente_desde` más reciente.

### T5.2 — Algoritmo determinístico de cálculo
Implementar el pseudocódigo de §7.2 como función pura (sin llamadas a IA):
recibe `criterios_extraidos` + matriz, devuelve puntos y tamaño.
- **DoD:** test por cada combinación de pesos/umbrales del ejemplo de la
  spec, incluyendo casos límite (justo en el umbral de un tamaño, por
  encima del último umbral → `XL`). Ningún test de esta tarea llama a un LLM.

### T5.3 — Integración extracción + cálculo + persistencia
Orquestar T4.1 + T5.2 y persistir `criterios_extraidos`, `sizing_calculado`,
`puntos_calculados` y `matriz_sizing_id` en `historia_usuario`.
- **DoD:** test de integración end-to-end con la matriz de ejemplo; cubre
  el escenario "Sizing calculado de forma determinística" de §13.

---

## EPIC 6 — OCR
*Puede arrancar en paralelo con EPIC 4/5. Referencia: §9*

### T6.1 — Subida a Storage + extracción de texto con Tesseract.js
Función que recibe una o más imágenes adjuntas, las sube a Supabase Storage
(bucket `historias-imagenes`, `[NUEVO v1.1]`) guardando las URLs en
`imagenes_urls`, corre OCR sobre cada una y concatena el resultado en
`texto_ocr`, marcando `contiene_contenido_ocr = true`.
- **DoD:** test con al menos una imagen de texto simple y una de baja
  calidad, documentando explícitamente que la precisión no está garantizada;
  test que verifica que `imagenes_urls` queda persistido con una URL por
  imagen subida.

### T6.2 — Derivación obligatoria a revisión manual con contenido OCR
Regla de negocio: si `contiene_contenido_ocr = true`, la historia nunca pasa
directo a `EN_SIZING` sin antes pasar por el líder, aunque el agente de
calidad la marque como `completa`.
- **DoD:** cubre el escenario "Historia con contenido proveniente de OCR" de
  §13 — test que verifica que el flujo se detiene en validación manual
  incluso con `completa = true`.

---

## EPIC 7 — Endpoints de API
*Depende de EPIC 2, 3, 5 y 6. Referencia: §8. Cada endpoint es independiente
entre sí una vez cerradas sus dependencias — pueden paralelizarse.*

### T7.1 — `POST /api/historias`
Crea la historia en `BORRADOR`, acepta `multipart/form-data` con
`imagenes[]` opcional `[NUEVO v1.1]`, dispara análisis de completitud (T3.1 +
T6.1 si hay imágenes).
- **DoD:** contrato de request/response exacto de §8; test de integración
  que cubre "Historia incompleta" de §13; test que verifica `401` sin token
  de Authorization (T1.3).

### T7.2 — `GET /api/historias/:id`
- **DoD:** devuelve la historia completa con estado actual; 404 si no existe.

### T7.3 — `POST /api/historias/:id/reenviar`
Solo válido si estado == `INCOMPLETA`. Acepta `imagenes[]` opcional, mismo
tratamiento que T7.1 `[NUEVO v1.1]`.
- **DoD:** 409 si el estado no es válido; vuelve a disparar T3.1.

### T7.4 — `POST /api/historias/:id/calcular-sizing`
Solo válido si estado == `COMPLETA`.
- **DoD:** dispara T5.3; pasa a `SIZING_CALCULADO → PENDIENTE_VALIDACION_LIDER`.

### T7.5 — `POST /api/historias/:id/validar`
Solo accesible por un usuario con `rol == 'lider'`, resuelto vía T1.3 — el
body ya no lleva un campo `lider` de texto libre `[NUEVO v1.1]`.
- **DoD:** cubre "Validación obligatoria del líder" de §13; permite aprobar
  o corregir el sizing; test que verifica `403` si el token resuelve un rol
  distinto de `lider`.

### T7.6 — `POST /api/historias/:id/aceptar`
El descuento de línea base ocurre **solo** acá. Solo accesible por un
usuario con `rol == 'cliente'` cuyo `cliente_id` coincida con el de la
historia `[NUEVO v1.1]`. Si no existe `consumo_mensual` para el período
vigente del cliente, se crea antes de descontar (§5).
- **DoD:** cubre "Descuento de línea base solo tras aceptación" de §13; test
  que verifica que ningún otro endpoint modifica `consumo_mensual`; test de
  `403` si el `cliente_id` del token no coincide con el de la historia; test
  de creación perezosa de `consumo_mensual` cuando no existe aún para el
  período.

### T7.7 — `POST /api/historias/:id/entregar`
- **DoD:** solo válido en `ACEPTADA`/`EN_EJECUCION`; registra `fecha_entrega`.

### T7.8 — `GET /api/clientes/:id/consumo`
Accesible por `cliente` (solo su propio `cliente_id`) o `lider`
`[NUEVO v1.1]`.
- **DoD:** devuelve línea base, consumido, disponible e historial de
  historias del período solicitado; `403` si un `cliente` pide el consumo de
  otro `cliente_id`.

---

## EPIC 8 — Frontend / consola
*Depende de EPIC 7. Puede empezarse en paralelo si se mockean los endpoints.
Referencia de estilo: §16 y `ESTILO_TSOFT.md`.*

### T8.0 — Login `[NUEVO v1.1]`
Pantalla de login (Supabase Auth) para los roles `cliente` y `lider`; el
resto de las vistas requieren sesión activa.
- **DoD:** sin sesión, cualquier vista protegida redirige a login; el token
  de sesión se adjunta automáticamente en cada llamada a la API (T1.3).

### T8.1 — Tokens de diseño `[NUEVO v1.2]`
Definir la paleta de colores y tipografía de §16 como tokens reutilizables
(ej. variables CSS o config de Tailwind): colores principales, de soporte,
semánticos (mapeados a estados de §6) y escala tipográfica.
- **DoD:** ningún componente de T8.2–T8.6 usa un valor de color/tipografía
  hardcodeado fuera de estos tokens; los 5 estados con color semántico de la
  tabla de §16 están cubiertos.

### T8.2 — Formulario de carga de historia
Texto + adjuntar imágenes (dispara OCR), enviado como `multipart/form-data`
contra T7.1 `[NUEVO v1.1]`.

### T8.3 — Vista de resultado de completitud
Muestra `sugerencias_mejora` y `feedback_resumen` cuando la historia es
incompleta, dimensión por dimensión, en cards (no bullets genéricos —
regla de §16).

### T8.4 — Vista de sizing + aceptar/rechazar
Muestra el tamaño calculado y los botones de aceptación del cliente.

### T8.5 — Panel del líder
Cola de historias pendientes de validación; muestra `texto_original` y
`texto_ocr` por separado cuando `contiene_contenido_ocr = true`, junto con
las imágenes de `imagenes_urls` para verificar contra la fuente
`[NUEVO v1.1]`.

### T8.6 — Panel de consumo
Línea base, consumido, disponible, historial — consume T7.8.

*(DoD de todo EPIC 8: cada vista consume el endpoint real correspondiente,
sin datos mockeados en el build final, y usa los tokens de T8.1 en vez de
valores de color/tipografía sueltos.)*

---

## EPIC 9 — Calibración y pre-producción
*No es una épica de código. Depende de que EPIC 5 esté cerrada. Referencia: §10*

### T9.1 — Set de historias históricas
Reunir al menos 20 historias reales ya estimadas por el equipo (sin IA), con
su tamaño/tiempo real conocido.

### T9.2 — Medición de dispersión
Correr cada historia del set 3 veces por el motor de sizing (T5.3) y
registrar la variación de resultados.

### T9.3 — Definición del umbral aceptable
Partir del default propuesto en §10 `[NUEVO v1.3]` (variación de tamaño en
más de un nivel en no más del 20% de corridas, error promedio ≤ ±30%
contra el histórico real) y someterlo a validación/ajuste del líder del
servicio — decisión de negocio, no técnica.

### T9.4 — Comparación contra resultado histórico real
Medir error promedio del sizing calculado contra el tiempo/costo real
histórico de cada historia del set.

### T9.5 — Gate de aprobación
No habilitar el flujo con un cliente/caso de uso real hasta que T9.2–T9.4
estén dentro del margen aceptado por el líder del servicio.

---

## Resumen de dependencias entre épicas

```
EPIC 0 (setup)
  └── EPIC 1 (datos)
        └── EPIC 2 (máquina de estados) ──┐
        └── EPIC 3 (agente de calidad) ───┼── EPIC 7 (API)
              └── EPIC 4 (extracción) ────┤        └── EPIC 8 (frontend)
                    └── EPIC 5 (cálculo) ─┤
        └── EPIC 6 (OCR) ─────────────────┘
                    └── EPIC 9 (calibración, al final)
```
