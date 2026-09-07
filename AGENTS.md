# AGENTS.md - Portal Estimaciones

> Contexto global del proyecto para todos los agentes.
> Fuente principal: `docs/estimaciones/SPEC_estimador-historias-poc.md`
> Ultima actualizacion: 2026-09-07

---

## Convencion de features

Toda feature usa un unico nombre en los tres lugares donde aparece:

```text
docs/[feature]/          material de la feature (uno o varios archivos)
tsoft-dev/[feature]/     artefactos de trabajo del flujo
$orquestador [feature]   invocacion con el nombre pelado
```

Reglas:

- La carpeta dentro de `docs/` es el nombre de la feature.
- Al invocar se escribe el nombre pelado, sin `docs/`, sin barra final y sin extension.
- El nombre no se traduce, no se abrevia y no se cambia entre etapas.

---

## Descripcion del proyecto

Este proyecto es un POC de una consola web para estimar historias de usuario asistida por IA.

El flujo previsto es:

1. El cliente carga una historia de usuario, opcionalmente con imagenes.
2. Un agente valida completitud, ambiguedad, buenas practicas, INVEST y dependencias.
3. Si la historia es valida, otro componente extrae criterios.
4. Un motor deterministico calcula el sizing final.
5. Un lider valida o corrige el resultado.
6. El cliente acepta o rechaza la estimacion.
7. El sistema descuenta puntos de la linea base mensual y registra auditoria.

El POC es standalone, sin integracion con TAI en esta etapa, y corre con un solo tenant por instancia.

---

## Alcance funcional

- Una historia de usuario por vez.
- Soporte de texto e imagenes con OCR best-effort.
- Validacion humana obligatoria antes de responder al cliente.
- Panel de consumo contra linea base mensual.
- Trazabilidad completa por auditoria.
- Preparado para un solo cliente/servicio por instancia, pero con modelo apto para futuro multi-tenant.

---

## Stack tecnologico objetivo

- Next.js 15 con App Router.
- TypeScript.
- Supabase Postgres.
- Supabase Auth.
- Supabase Storage para imagenes adjuntas.
- SDK oficial de Anthropic para las llamadas a IA.
- Tesseract.js para OCR.
- Vercel como hosting del frontend y API.
- Monorepo con workspaces.

---

## Estructura esperada

- `apps/web/` -> frontend y API routes.
- `packages/shared/` -> tipos y schemas compartidos.
- `packages/quality-agent/` -> prompt y logica del agente de calidad.
- `packages/sizing-engine/` -> extraccion de criterios y calculo deterministico.
- `supabase/migrations/` -> esquema SQL versionado.

---

## Dominio y reglas de negocio

- La maquina de estados de una historia es:
  `BORRADOR -> EN_ANALISIS_COMPLETITUD -> INCOMPLETA | COMPLETA -> EN_SIZING -> SIZING_CALCULADO -> PENDIENTE_VALIDACION_LIDER -> SIZING_VALIDADO -> PENDIENTE_ACEPTACION_CLIENTE -> RECHAZADA_POR_CLIENTE | ACEPTADA -> EN_EJECUCION -> ENTREGADA`
- El descuento de linea base ocurre solo al aceptar la historia.
- Si hay OCR, la historia siempre requiere revision manual del lider antes de sizing.
- El sizing final nunca lo devuelve la IA: la IA solo extrae criterios.
- Si la historia falla una sola dimension de calidad, no puede avanzar a sizing.
- El proyecto no usa framework agential pesado; la IA se consume directo via SDK.
- La app debe ser standalone y exponer su propia API REST.

---

## Modelo de datos objetivo

Entidades principales:

- `cliente`
- `usuario`
- `matriz_sizing`
- `historia_usuario`
- `consumo_mensual`
- `log_auditoria`

Reglas clave:

- `usuario` se resuelve desde autenticacion, no desde campos libres del body.
- `consumo_mensual` se crea de forma perezosa cuando falta el periodo.
- `matriz_sizing` queda versionada y nunca se pisa.
- `historia_usuario` guarda texto original, texto OCR, imagenes, criterios extraidos, sizing, validacion y estado.

---

## Contratos y API

- Los endpoints requieren autenticacion salvo indicacion contraria.
- `POST /api/historias` crea una historia y acepta `multipart/form-data`.
- `POST /api/historias/:id/reenviar` solo vale si la historia esta incompleta.
- `POST /api/historias/:id/calcular-sizing` solo vale si la historia esta completa.
- `POST /api/historias/:id/validar` solo lo puede usar un lider.
- `POST /api/historias/:id/aceptar` solo lo puede usar el cliente correcto.
- `POST /api/historias/:id/entregar` marca la entrega final.
- `GET /api/clientes/:id/consumo` muestra linea base, consumido y disponible.

---

## Convenciones de implementacion

- Usar TypeScript estricto.
- Definir schemas compartidos con validacion explicita.
- Mantener logica pura en el motor de sizing y en las transiciones de estado.
- No hardcodear secretos, tokens ni rutas de entorno.
- No confiar en identidad o rol enviados desde el cliente.
- Mantener la separacion entre extraccion con IA y calculo deterministico.
- Los componentes de OCR, validacion y sizing deben ser testeables por separado.
- Las reglas visuales del portal deben seguir `ESTILO_TSOFT.md`.

---

## Testing

- La validacion debe cubrir:
  - maquina de estados,
  - validacion de calidad,
  - extraccion de criterios,
  - calculo deterministico,
  - OCR,
  - endpoints de API,
  - frontend/pantallas principales.
- Los tests deterministas no deben depender de llamadas reales a LLM.
- Los casos de calidad deben apoyarse en un golden set versionado.
- El OCR se considera best-effort, pero el flujo debe verificar la derivacion manual cuando hay imagenes.

---

## Lo que nunca se debe hacer

- No integrar con TAI en esta etapa.
- No responder sizing final con un modelo generativo.
- No permitir validacion o aceptacion sin autenticacion.
- No confiar en roles enviados en el body.
- No borrar versiones historicas de la matriz de sizing.
- No omitir auditoria de cambios de estado.
- No usar `tsoft-dev/metrics/` ni `tsoft-dev/reportes/` como fuente manual de verdad si luego se regeneran.
- No agregar dependencias externas sin justificacion clara.

---

## Skills utiles

- `orquestador` -> flujo de trabajo con aprobacion humana por etapa.
- `reporte-ejecucion` -> reporte de consumo y ejecuciones.

