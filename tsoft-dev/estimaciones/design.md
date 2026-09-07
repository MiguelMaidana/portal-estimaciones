# Diseño de construcción — estimaciones (POC)

**Feature:** `estimaciones`  
**Estado:** listo para iniciar el tramo base local; integración remota condicionada a credenciales.  
**Fuentes:** `docs/estimaciones/SPEC_estimador-historias-poc.md` v1.3, `docs/estimaciones/TASKS_estimador-historias-poc.md`, `tsoft-dev/estimaciones/explorador-output.md` y `AGENTS.md`.

## 1. Resultado y límites del primer tramo

Se construirá la base de un POC standalone para que un cliente cargue una única historia, el sistema evalúe su calidad con IA, extraiga criterios, calcule el sizing de forma determinística, obligue la validación humana y registre consumo y auditoría. La instancia inicial queda configurada para el tenant `DEMO`.

El primer tramo entrega un repositorio ejecutable localmente, contratos tipados, dominio puro testeado, migración y seeds versionados, adaptadores intercambiables para Supabase/Anthropic/OCR, API REST y las pantallas necesarias. No incluye TAI, multitenancy simultáneo, un panel administrativo, desarrollo/certificación automática ni calibración productiva.

La IA se limita a evaluar calidad y extraer criterios estructurados. La determinación de `completa`, las transiciones de estado, el tamaño, los puntos y el descuento de consumo son siempre código determinístico del servidor.

## 2. Decisiones aplicadas y supuestos acotados

| Tema | Decisión de implementación |
|---|---|
| Workspace | `pnpm` workspaces, con Next.js 15/App Router y TypeScript estricto. Es una elección de setup permitida por la spec; no agrega capacidades funcionales. |
| Matriz inicial | Se versiona en `packages/sizing-engine/matrices/DEMO.json` con la estructura y los valores de ejemplo de §7.2 de la spec. Nunca se actualiza una fila existente de `matriz_sizing`. |
| Puntos fraccionarios | **Supuesto A-01:** `puntos_calculados`, `consumido`, `disponible` y `linea_base` se persistirán como `numeric(10,1)`, no `INT`. El peso inicial `por_criterio_aceptacion: 0.5` hace necesario conservar medios puntos; redondear alteraría la matriz cerrada. |
| Acceso a datos | La UI usa Supabase solo para sesión. Todas las lecturas y escrituras de negocio pasan por las rutas de Next.js; el servidor valida el token y resuelve `usuario` en la tabla propia. La service-role key nunca llega al navegador. |
| `cliente_id` en creación | Se conserva el campo del contrato `multipart/form-data`, pero no otorga identidad: debe coincidir con el `cliente_id` resuelto desde el token del usuario cliente; ante diferencia se responde `403`. |
| Estado OCR | **Prerrequisito P-01:** antes de implementar la parte OCR de T6/T7 se debe ratificar una extensión mínima de la máquina de estados para revisar OCR antes de sizing: `COMPLETA -> PENDIENTE_REVISION_OCR -> COMPLETA`. Sin ese hito, la regla de `AGENTS.md`/§9 (revisión del líder antes de sizing) contradice el diagrama de §6, que solo ubica al líder después del cálculo. No se implementará un atajo ni un estado implícito. |
| Límites de imágenes | La spec acepta JPG/PNG pero no define tamaño, cantidad ni retención. **Riesgo R-01:** hasta que se fijen esos valores, el handler validará formato y usará fixtures pequeñas; no debe introducir un límite de producto arbitrario. |

## 3. Prerrequisitos y qué se puede hacer sin credenciales

### Disponible offline/localmente

- Crear el monorepo, configuración TypeScript, linting y suite de pruebas.
- Implementar schemas Zod, tipos, matriz `DEMO`, máquina de estados, autorización pura, agregación de calidad, cálculo de sizing y sus tests con doubles.
- Redactar prompt, golden set y contratos de adaptadores de Anthropic, Supabase y Tesseract.
- Escribir migración SQL, seed y script de carga de matriz, sin aplicarlos a un proyecto remoto.
- Construir API y UI contra repositorios/adaptadores en memoria únicamente para desarrollo y pruebas; los mocks no se habilitan en el build de despliegue.

### Bloqueado hasta recibir credenciales/configuración

| Bloqueo | Requerido para desbloquearlo | Impacto |
|---|---|---|
| Supabase | URL, anon key, service-role key, project ref y acceso al proyecto | Aplicar migraciones, Auth real, Storage, seed remoto, pruebas de integración y deploy conectado. |
| Anthropic | `ANTHROPIC_API_KEY` y modelo aprobado en `ANTHROPIC_MODEL` | Ejecutar agente de calidad/extractor reales y correr el golden set contra el modelo. |
| Datos DEMO | Servicio y línea base mensual de `DEMO` | Ejecutar el seed de cliente y habilitar pruebas reales de consumo. |
| Usuarios de prueba | Una cuenta cliente DEMO y una cuenta líder, con sus filas `usuario` | Pruebas E2E de roles y autorización. |
| P-01 | Aprobación de la transición de revisión OCR previa a sizing | Implementar OCR y sus rutas sin incumplir el flujo. |

Los bloqueos anteriores son prerrequisitos de integración, no impiden completar el núcleo local. Si hubiese Docker y Supabase CLI disponibles, las migraciones también podrán verificarse contra Supabase local; no se lo presupone.

## 4. Arquitectura y límites entre módulos

```text
apps/web
  UI (App Router) ──> route handlers ──> casos de uso
                                      ├─ repositorios Supabase
                                      ├─ adaptador Anthropic
                                      ├─ adaptador OCR/Storage
                                      └─ paquetes puros
packages/shared
  schemas, tipos de dominio, eventos y contratos API
packages/quality-agent
  prompt, validación de respuesta, agregación y golden set
packages/sizing-engine
  schema de matriz, matriz DEMO y cálculo puro
supabase
  migraciones y seed auditable
```

- `packages/shared` no depende de Next.js, Supabase, Anthropic ni Tesseract.
- `packages/quality-agent` recibe un puerto `QualityModel`; el adaptador Anthropic vive en `apps/web` para que las claves no circulen por paquetes reutilizables.
- `packages/sizing-engine` recibe criterios y matriz ya validados; no llama a una IA ni a la base.
- Los casos de uso de `apps/web/src/server` orquestan transiciones, persistencia y auditoría dentro de operaciones atómicas.
- La UI no decide permisos ni estados. Solo muestra los datos que devuelve la API y presenta acciones habilitadas por estado/rol recibidos.

## 5. Estructura y archivos concretos

Los siguientes son archivos a crear en el tramo. No se modifican archivos fuera de esta lista durante la implementación de la feature, salvo que una tarea posterior aprobada requiera registrar una dependencia ya justificada.

```text
package.json                                  # workspaces y scripts raíz
pnpm-workspace.yaml
tsconfig.base.json
.env.example                                  # sin secretos

apps/web/package.json
apps/web/next.config.ts
apps/web/tsconfig.json
apps/web/vitest.config.ts
apps/web/src/app/layout.tsx
apps/web/src/app/page.tsx                     # redirección según sesión/rol
apps/web/src/app/login/page.tsx
apps/web/src/app/historias/nueva/page.tsx
apps/web/src/app/historias/[id]/page.tsx
apps/web/src/app/lider/page.tsx
apps/web/src/app/consumo/page.tsx
apps/web/src/app/api/historias/route.ts
apps/web/src/app/api/historias/[id]/route.ts
apps/web/src/app/api/historias/[id]/reenviar/route.ts
apps/web/src/app/api/historias/[id]/calcular-sizing/route.ts
apps/web/src/app/api/historias/[id]/validar/route.ts
apps/web/src/app/api/historias/[id]/aceptar/route.ts
apps/web/src/app/api/historias/[id]/entregar/route.ts
apps/web/src/app/api/clientes/[id]/consumo/route.ts
apps/web/src/app/api/historias/[id]/revisar-ocr/route.ts # solo después de P-01
apps/web/src/components/historias/*.tsx
apps/web/src/components/consumo/*.tsx
apps/web/src/components/ui/*.tsx
apps/web/src/styles/tokens.css
apps/web/src/styles/globals.css
apps/web/src/lib/supabase/browser.ts
apps/web/src/server/auth/resolve-identity.ts
apps/web/src/server/auth/authorize.ts
apps/web/src/server/data/{historias,matrices,consumo,auditoria,usuarios}.ts
apps/web/src/server/services/{quality,sizing,ocr,storage}.ts
apps/web/src/server/use-cases/{crear-historia,reenviar-historia,calcular-sizing,validar-sizing,aceptar-sizing,entregar-historia,revisar-ocr}.ts
apps/web/src/server/http/{errors,response,parse-form-data}.ts
apps/web/src/test/**/*.test.ts

packages/shared/package.json
packages/shared/tsconfig.json
packages/shared/src/{index,domain,events,api}.ts
packages/shared/src/schemas/{auth,historia,calidad,criterios,matriz,consumo}.ts

packages/quality-agent/package.json
packages/quality-agent/tsconfig.json
packages/quality-agent/src/{index,prompt,aggregate,ports}.ts
packages/quality-agent/fixtures/golden-set.json
packages/quality-agent/src/**/*.test.ts

packages/sizing-engine/package.json
packages/sizing-engine/tsconfig.json
packages/sizing-engine/src/{index,calculate,matrix-schema}.ts
packages/sizing-engine/matrices/DEMO.json
packages/sizing-engine/src/**/*.test.ts

supabase/migrations/0001_estimaciones.sql
supabase/seed/cliente.ts
scripts/cargar-matriz.ts
```

`revisar-ocr` y su caso de uso quedan excluidos de la construcción hasta aprobar P-01. El resto se puede desarrollar con el puerto de OCR mockeado.

## 6. Diseño de dominio, persistencia y seguridad

### 6.1 Tipos y schemas compartidos

`packages/shared` define los enums `RolUsuario`, `EstadoHistoria`, `EventoHistoria` y `TamanoSizing`, además de schemas Zod para:

- datos persistidos de las seis entidades de la spec;
- salida cruda del agente de calidad, sin `completa`;
- resultado persistible de calidad, que agrega `completa` de forma determinística;
- criterios extraídos, matriz, resultado de cálculo, consumo y payloads de API;
- formularios `multipart/form-data` y cuerpos JSON (`validar`, `aceptar`).

El schema de criterios exige que `menciona_integraciones` sea coherente con `integraciones_detectadas` (lista no vacía si es `true`), y el de matriz exige pesos no negativos, umbrales ordenados y un único último umbral `XL` con `puntos_max: null`. Es validación de contrato, no una nueva regla de negocio.

### 6.2 Migración `0001_estimaciones.sql`

La migración crea exactamente `cliente`, `usuario`, `matriz_sizing`, `historia_usuario`, `consumo_mensual` y `log_auditoria`, usando UUIDs generados por base de datos y las columnas de §5. Además debe incluir:

- `CHECK` para roles, estados, tamaños, resultados de completitud y puntos no negativos;
- unicidad de `(cliente_id, version)` en `matriz_sizing` y `(cliente_id, periodo)` en `consumo_mensual`;
- índice para historia por `(cliente_id, estado, fecha_carga desc)`, matriz por `(cliente_id, vigente_desde desc)`, consumo por `(cliente_id, periodo)` y auditoría por `(historia_id, timestamp)`;
- `periodo` normalizado al primer día del mes;
- columnas de puntos como `numeric(10,1)` según A-01;
- RLS habilitada sin políticas de datos para clientes directos: el navegador no consulta las tablas; el acceso de negocio se realiza exclusivamente mediante la API autenticada y service role del servidor.

La aceptación descuenta consumo mediante una función SQL transaccional o una actualización condicional equivalente: bloquea/actualiza el único registro del período, crea el consumo perezosamente con la línea base vigente del cliente si falta, incrementa una única vez por transición a `ACEPTADA`, actualiza historia y agrega auditoría. Un reintento HTTP no puede duplicar el descuento porque el caso de uso rechaza estados distintos de `PENDIENTE_ACEPTACION_CLIENTE`.

### 6.3 Seed y matriz DEMO

`supabase/seed/cliente.ts` crea o verifica el cliente `DEMO`; recibe `DEMO_SERVICIO` y `DEMO_LINEA_BASE_PUNTOS` por entorno para no inventar valores de negocio. `scripts/cargar-matriz.ts` valida `DEMO.json`, lee la versión vigente, inserta la siguiente versión con `vigente_desde = now()` y nunca hace `UPDATE`/`DELETE` de matrices históricas.

El archivo `DEMO.json` contiene los pesos `1/3/5`, `2`, `1`, `2`, `0.5` y los umbrales `XS=3`, `S=6`, `M=10`, `L=16`, `XL=null` definidos en la spec. Es la base inicial cerrada para el POC, no una calibración comercial.

### 6.4 Identidad y autorización

`resolve-identity.ts` obtiene el bearer token, valida la sesión contra Supabase Auth y busca la fila activa de `usuario` por `auth.users.id`. Devuelve `{ userId, rol, clienteId }` o un error `401`; una fila inexistente/inactiva también se considera no autorizada (`403` tras token válido).

Las guardas se centralizan en `authorize.ts`:

| Acción | Regla |
|---|---|
| Crear/reenviar historia | `rol=cliente` y cliente de la historia igual a `clienteId` de sesión. |
| Ver historia | Cliente propietario o líder del servicio; la proyección para cliente oculta criterios, puntos y tamaño hasta `PENDIENTE_ACEPTACION_CLIENTE`. |
| Calcular sizing | Cliente propietario o líder del servicio, con historia `COMPLETA`; el resultado solo queda visible para el líder hasta su validación. |
| Revisar OCR / validar sizing | Solo líder. |
| Aceptar/rechazar | Solo cliente propietario. |
| Entregar | Solo líder. |
| Consultar consumo | Cliente únicamente propio; líder para DEMO. |

`equipo_delivery` no recibe una pantalla ni endpoint administrativo en el POC: usa los scripts de datos maestros fuera de la app. Ningún handler acepta `rol`, `usuario`, `lider` ni identidad como autoridad desde el body.

## 7. Máquina de estados y auditoría

El módulo puro `transitions.ts` representa cada flecha permitida como `(estado, evento) -> estado`. Las transiciones normales son:

```text
BORRADOR --ENVIAR_A_ANALISIS--> EN_ANALISIS_COMPLETITUD
EN_ANALISIS_COMPLETITUD --CALIDAD_INCOMPLETA--> INCOMPLETA
EN_ANALISIS_COMPLETITUD --CALIDAD_COMPLETA--> COMPLETA
INCOMPLETA --REENVIAR--> BORRADOR
COMPLETA --INICIAR_SIZING--> EN_SIZING
EN_SIZING --SIZING_OBTENIDO--> SIZING_CALCULADO
SIZING_CALCULADO --SOLICITAR_VALIDACION--> PENDIENTE_VALIDACION_LIDER
PENDIENTE_VALIDACION_LIDER --APROBAR_SIZING--> SIZING_VALIDADO
PENDIENTE_VALIDACION_LIDER --CORREGIR_SIZING--> EN_SIZING
SIZING_VALIDADO --PUBLICAR_AL_CLIENTE--> PENDIENTE_ACEPTACION_CLIENTE
PENDIENTE_ACEPTACION_CLIENTE --ACEPTAR--> ACEPTADA
PENDIENTE_ACEPTACION_CLIENTE --RECHAZAR--> RECHAZADA_POR_CLIENTE
ACEPTADA --INICIAR_EJECUCION--> EN_EJECUCION
EN_EJECUCION --ENTREGAR--> ENTREGADA
```

Tras P-01 se agregan solamente `COMPLETA --REQUIERE_REVISION_OCR--> PENDIENTE_REVISION_OCR` y `PENDIENTE_REVISION_OCR --OCR_APROBADO--> COMPLETA`; `OCR_RECHAZADO` devuelve a `INCOMPLETA` con feedback del líder. Esto conserva todas las transiciones de la spec y hace verificable la condición previa al sizing.

Cada caso de uso ejecuta la transición y escribe exactamente un `log_auditoria` atómico con evento, actor (`id` de usuario o `sistema`) y detalle mínimo (estado anterior/posterior, matriz usada y corrección si aplica). Un estado o evento desconocido falla explícitamente con conflicto `409` y nunca se corrige silenciosamente.

## 8. Calidad, sizing y OCR

### 8.1 Agente de calidad

`packages/quality-agent/src/prompt.ts` toma como punto de partida literal el prompt v1 de §7.3: evalúa completitud, ambigüedad, redacción, los seis criterios INVEST y dependencias; exige JSON sin markdown ni `completa`; no menciona sizing. Cuando existe OCR, concatena `texto_original` y `texto_ocr` para el modelo con una marca que advierte su carácter best-effort, sin perder ambos textos por separado.

El adaptador Anthropic debe solicitar salida JSON estructurada y validar la respuesta con Zod. Si la respuesta no pasa el schema, no se persiste una decisión parcial: el caso de uso registra el fallo técnico y devuelve un error controlado. `aggregate.ts` calcula `completa = true` únicamente si las cuatro claves `cumple` y los seis booleanos INVEST son verdaderos; genera/persiste `feedback_resumen` y `sugerencias_mejora` del resultado validado.

El golden set tiene como mínimo diez casos versionados: una historia completa, una incompleta por cada dimensión, una ambigua, una con dependencia bloqueante, una atómica fallida y una con texto OCR corrupto. En local se ejecuta contra un doble determinista que devuelve fixtures; al tener `ANTHROPIC_API_KEY`, se corre como suite separada no bloqueante para iterar el prompt y registrar discrepancias.

### 8.2 Sizing determinístico

`calculate.ts` implementa exactamente:

```text
puntos = peso(complejidad_tecnica)
       + integraciones * por_integracion_detectada
       + ambiguedades * por_ambiguedad_detectada
       + dependencias * por_dependencia_externa
       + criterios_aceptacion * por_criterio_aceptacion
tamano = primer umbral con puntos <= puntos_max; si no existe, XL
```

El caso de uso solo se habilita desde `COMPLETA` (y, tras P-01, nunca desde `PENDIENTE_REVISION_OCR`). Obtiene la matriz vigente, llama al extractor Anthropic mediante un puerto, valida criterios, calcula puntos localmente y persiste criterios, puntos, tamaño y `matriz_sizing_id`. La respuesta del modelo no tiene campo de tamaño y cualquier campo extra se descarta/rechaza por schema.

El líder ve la alerta `alerta_fuera_de_matriz`. Si corrige el sizing, se conserva el cálculo original, la corrección y el motivo en auditoría; el diseño detallado de una columna adicional para el motivo solo se incorpora en una migración posterior aprobada si el contrato de UI lo necesita, pues la spec no la modela.

### 8.3 OCR y Storage

El adaptador OCR acepta solamente archivos JPEG/PNG válidos, sube primero a `historias-imagenes` usando una ruta aislada por `cliente_id/historia_id/uuid`, persiste una URL por archivo y ejecuta Tesseract.js por imagen. Concatena el resultado etiquetando el origen; `texto_ocr` y `texto_original` nunca se mezclan en almacenamiento. Fallos de OCR se exponen como resultado best-effort y se auditan; no habilitan un sizing sin revisión humana.

La UI del líder muestra imagen fuente, texto original y OCR en paneles separados. La implementación definitiva de la transición previa a sizing queda bloqueada por P-01, no sustituida por una revisión posterior.

## 9. API REST y casos de uso

Todos los handlers siguen el flujo: validar token -> resolver identidad -> validar payload -> cargar recurso -> autorizar -> ejecutar caso de uso/transacción -> responder schema tipado. Los errores se normalizan como `401` token ausente/inválido, `403` rol o cliente incorrecto, `404` recurso inexistente, `409` estado inválido/concurrencia y `422` payload inválido.

| Ruta | Caso de uso y precondiciones | Respuesta/efecto comprobable |
|---|---|---|
| `POST /api/historias` | Cliente propietario; parsea `multipart/form-data`; crea borrador, procesa imágenes si existen y analiza calidad. | `{ id, estado, resultado_completitud, feedback_completitud, contiene_contenido_ocr }`; deja `INCOMPLETA`, `COMPLETA` o `PENDIENTE_REVISION_OCR` tras P-01. |
| `GET /api/historias/:id` | Cliente propietario o líder. | Proyección por rol: el líder recibe trazabilidad completa; el cliente no recibe sizing/criterios antes de la validación. |
| `POST /api/historias/:id/reenviar` | Cliente propietario y `INCOMPLETA`; reemplaza texto/adjuntos según contrato y reinicia análisis. | `409` fuera de estado; nueva auditoría y resultado de calidad. |
| `POST /api/historias/:id/revisar-ocr` | Solo líder, `PENDIENTE_REVISION_OCR`; requiere P-01. | Aprueba para volver a `COMPLETA` o devuelve a `INCOMPLETA` con feedback. |
| `POST /api/historias/:id/calcular-sizing` | Cliente propietario o líder, `COMPLETA`. | Persiste extracción/matriz/cálculo y deriva obligatoriamente a `PENDIENTE_VALIDACION_LIDER`, sin exponer el resultado al cliente. |
| `POST /api/historias/:id/validar` | Solo líder, `PENDIENTE_VALIDACION_LIDER`; body `{ aprobado, sizing_corregido? }`. | Aprobado: publica tras `SIZING_VALIDADO`; corrección: vuelve a `EN_SIZING`. |
| `POST /api/historias/:id/aceptar` | Cliente propietario, `PENDIENTE_ACEPTACION_CLIENTE`; body `{ aceptado }`. | Acepta: descuenta una sola vez y queda `ACEPTADA`; rechaza: `RECHAZADA_POR_CLIENTE`, sin consumo. |
| `POST /api/historias/:id/entregar` | Líder y `ACEPTADA`/`EN_EJECUCION`. | Marca fecha y `ENTREGADA`; si parte de `ACEPTADA`, registra primero inicio manual de ejecución. |
| `GET /api/clientes/:id/consumo?periodo=YYYY-MM` | Cliente propio o líder. | `linea_base`, `consumido`, `disponible` e historias del período. |

La única desviación a resolver antes de código de endpoints es P-01; no se agregará una ruta OCR si no se aprueba la transición correspondiente. La aceptación y el consumo usan transacción; el resto registra auditoría en la misma operación que su cambio de estado.

## 10. UI mínima y estilo

Se crean pantallas de login, carga/reenvío, detalle de historia, cola de líder y consumo. La carga usa `multipart/form-data`; el detalle enseña cards por dimensión (no bullets genéricos), estado, feedback y sizing únicamente después de validación. El panel líder incluye criterios extraídos, alerta fuera de matriz y, para OCR, imagen/original/OCR separados.

`tokens.css` centraliza Calibri/Inter para UI y JetBrains Mono/Consolas para JSON/auditoría, además de los colores semánticos de §16: azul `#2C5282`, amarillo `#F5A524`, verde `#16A37A`, rojo oscuro `#A11820` y rojo TSOFT `#E30613` solo como acento. Ningún componente introduce colores o tipografías hardcodeadas fuera de los tokens.

Antes de integración remota, las vistas se prueban con el servidor local mockeado; antes de deploy se eliminan esos datos de fixture de rutas de producción y cada vista consume el endpoint real.

## 11. Orden de ejecución, dependencias y validación

| Orden | Trabajo | Depende de | Ejecutable sin credenciales | Criterio de salida |
|---:|---|---|---|---|
| 0 | Crear workspace, app vacía, paquetes, scripts, `.env.example` y CI local. | Ninguno. | Sí. | `pnpm install`, typecheck, lint y test pasan sin secretos. |
| 1 | Definir schemas/tipos, matriz DEMO, cálculo puro y fixtures. | 0. | Sí. | Cada umbral, borde y medio punto se prueba; no hay llamadas de red. |
| 2 | Implementar estados, eventos, auditoría abstracta y autorización pura. | 1. | Sí. | Un test por flecha; toda transición ilegal falla; no se confía en body. |
| 3 | Escribir migración, seed y cargador de matriz. | 1. | Sí, sin aplicar. | SQL revisado, schema/matriz validan y cargar dos veces modela dos versiones. |
| 4 | Implementar prompt, agregación, golden set y adaptador Anthropic con doble. | 1. | Sí. | Una dimensión falsa da `completa=false`; fixtures validan; el modelo no entrega tamaño. |
| 5 | Implementar repositorios, casos de uso y handlers API con doubles. | 2, 3, 4. | Sí. | Tests de contrato cubren 401/403/404/409/422 y los escenarios Given/When/Then. |
| 6 | Construir login, carga, detalle, líder y consumo contra API. | 5. | Sí, con doubles de desarrollo. | Pruebas de componentes y flujo de rol; no hay datos mockeados en build final. |
| 7 | Resolver P-01 e implementar Storage/OCR/revisión previa a sizing. | 2, 5, P-01. | Parcial; OCR puro sí, Storage real no. | OCR persiste separadamente y no permite sizing sin aprobación líder. |
| 8 | Configurar Supabase/Anthropic, aplicar migración, seed DEMO y pruebas de integración/E2E. | Credenciales, datos DEMO, usuarios de prueba; 3–7. | No. | Auth, RLS, Storage, auditoría, consumo idempotente y llamadas IA se verifican en entorno de prueba. |

Las pruebas mínimas obligatorias son: schemas; cálculo de tamaño para todos los umbrales; cada transición; calidad con una dimensión fallida; detección de criterio fuera de matriz; autorización por token/rol/cliente; consumo solo al aceptar e idempotencia de reintento; OCR con imagen legible y degradada; contratos API; y pantallas principales. Las suites unitarias no realizan llamadas reales a LLM.

## 12. Riesgos de salida del tramo

- La matriz DEMO es una base operativa inicial, no habilita facturación ni producción sin la calibración con al menos 20 historias y la aprobación del líder establecida en la spec.
- Tesseract es best-effort, especialmente con diagramas; por eso la revisión OCR es una regla de flujo, no una métrica que se intente garantizar.
- El prompt v1 es un punto de partida: debe versionarse y ajustarse contra el golden set, sin cambiar la regla determinística de agregación.
- No se despliega ni se activa el flujo para un cliente real hasta contar con datos históricos, umbral de calibración aceptado y credenciales configuradas de forma segura.

Con credenciales de Supabase y Anthropic quedan bloqueadas la integración real, Auth/Storage, migraciones aplicadas y evaluación LLM; ya queda listo para avanzar localmente el monorepo, dominio, tests puros, contratos, matriz DEMO, API/UI con doubles y la preparación de migraciones.
Aprobado por IA Maker: SI
