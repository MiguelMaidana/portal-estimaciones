# Scope validado — estimaciones

## Qué se va a construir
Un POC standalone de consola web para cargar una historia de usuario a la vez, evaluarla con un agente de calidad, extraer criterios con IA, calcular el sizing de forma determinística y pasar por validación de líder antes de que el cliente acepte o rechace. Si la historia trae imágenes, se agrega OCR best-effort y esa historia queda forzada a revisión manual.

El primer tramo que hay que construir es la base del sistema: monorepo, esquema de datos, autenticación/resolución de identidad, schemas compartidos y máquina de estados. Sin esos contratos no conviene avanzar con API, sizing, OCR ni frontend.

## Actores involucrados
- Cliente: carga historias, ve el sizing validado, acepta o rechaza y consulta consumo.
- Líder del servicio: valida o corrige el sizing antes de que llegue al cliente.
- Equipo de delivery: define y versiona la matriz de sizing.
- Sistema: Supabase Auth, Supabase Postgres, Supabase Storage, Anthropic y Tesseract.js.

## Flujo principal
1. Se crea la base del monorepo con `apps/web`, `packages/shared`, `packages/quality-agent`, `packages/sizing-engine` y `supabase/migrations`.
2. Se modelan `cliente`, `usuario`, `matriz_sizing`, `historia_usuario`, `consumo_mensual` y `log_auditoria`, más los contratos compartidos de entrada/salida.
3. Se resuelve identidad server-side desde Supabase Auth y se aplican las reglas de autorización por rol y cliente.
4. Se implementa la máquina de estados y la auditoría para cada transición.
5. Se construye el agente de calidad con sus 5 dimensiones; si una sola falla, la historia queda fuera de sizing.
6. Se extraen criterios con IA y se calcula el tamaño con el motor determinístico contra la matriz vigente.
7. Si hay imágenes, se suben a Storage, se corre OCR y la historia queda obligada a revisión manual del líder.
8. Se exponen los endpoints de API y después se arma la UI para carga, validación, sizing y consumo.

## Casos borde identificados
- Una historia con una sola dimensión fallida no puede avanzar a sizing.
- Si hay OCR, la historia nunca debe saltar la revisión manual del líder aunque el agente de calidad la marque completa.
- El `consumo_mensual` puede no existir todavía para el período; en ese caso se crea de forma perezosa.
- La matriz de sizing es versionada: una versión nueva no debe pisar ni romper el cálculo de historias viejas.
- El sizing final no lo puede devolver una IA: solo la extracción de criterios.
- La historia no puede aceptarse con un cliente distinto del dueño real del registro.

## Lo que está fuera de scope
- Integración con TAI.
- Multi-tenant simultáneo dentro de una misma instancia.
- Automatización del desarrollo/certificación desde la consola.
- Panel administrativo completo para clientes, matriz y períodos.
- Calibración de producción con datos reales como parte del primer build.
- Cualquier camino que intente usar IA para devolver el sizing final.

## Decisiones cerradas por IA Maker
- La primera matriz de sizing del POC usa la estructura y los valores de ejemplo de la spec como base inicial.
- El primer tenant o cliente de prueba será `DEMO`.
- Todavía no están disponibles las credenciales de Supabase ni de Anthropic.

## Prerrequisito bloqueante
- Hasta que lleguen las credenciales de Supabase y Anthropic, no se puede avanzar con el setup técnico real, la conexión a servicios externos, ni con ninguna tarea que dependa de autenticación, persistencia remota, Storage o llamadas a IA.
- Igual se puede avanzar offline/localmente con la estructura del monorepo, los schemas compartidos, la máquina de estados, la lógica determinística de sizing, la documentación y los tests puros o con mocks.
