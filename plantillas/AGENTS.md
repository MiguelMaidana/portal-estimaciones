<!--
╔══════════════════════════════════════════════════════════════╗
║           TSOFT AI Dev Kit — AGENTS.md                      ║
║                                                              ║
║  Este archivo es el contexto global del proyecto para        ║
║  todos los agentes del kit. Completalo antes de invocar      ║
║  cualquier agente por primera vez.                           ║
║                                                              ║
║  CÓMO LLENARLO — hay tres formas:                            ║
║                                                              ║
║  1. Pedile a Codex que lo genere automáticamente:            ║
║     "Analizá la estructura de este repositorio y completá    ║
║      el AGENTS.md con lo que encontrés"                      ║
║     Funciona bien en proyectos con código existente.         ║
║                                                              ║
║  2. Completarlo a mano usando las secciones de abajo         ║
║     como guía. Recomendado para proyectos nuevos o cuando    ║
║     querés más control sobre el contexto que leen los        ║
║     agentes.                                                 ║
║                                                              ║
║  3. Combinado: Codex genera el borrador, vos lo revisás      ║
║     y ajustás. Es la mejor práctica en la mayoría de         ║
║     los casos.                                               ║
║                                                              ║
║  REGLAS:                                                     ║
║  - Sé específico. "Usamos buenas prácticas" no ayuda.        ║
║    "Todas las funciones async usan try/catch con logs        ║
║    en el catch" sí ayuda.                                    ║
║  - Actualizalo cuando el proyecto cambie. Si cambia la       ║
║    arquitectura o se agrega una convención nueva, este       ║
║    archivo debe reflejarlo.                                  ║
║  - No pongas información sensible (tokens, passwords,        ║
║    datos de producción).                                     ║
║  - La sección "Convención de features" viene completa y      ║
║    es igual en todos los proyectos: no la edites.            ║
╚══════════════════════════════════════════════════════════════╝
-->

# AGENTS.md — [Nombre del proyecto]

> Contexto global del proyecto para el TSOFT AI Dev Kit.
> Leído por todos los agentes antes de ejecutar cualquier tarea.
> Última actualización: [fecha]

---

## Convención de features — estándar del kit, no editar

Toda feature usa **un único nombre** en los tres lugares donde aparece:

```
docs/[feature]/          material de la feature (uno o varios archivos)
tsoft-dev/[feature]/     archivos de trabajo del kit
$orquestador [feature]   invocación, con el nombre pelado
```

Ejemplo correcto:

```
docs/cambio-de-color/brief.md
docs/cambio-de-color/mockup.png
tsoft-dev/cambio-de-color/
$orquestador cambio-de-color
```

Reglas:

- La carpeta de `docs/` **es** el nombre de la feature. Puede contener varios
  archivos; el Explorador los lee todos.
- Al invocar se escribe el nombre pelado: **sin** `docs/`, **sin** barra final
  y **sin** extensión.
- El nombre no se traduce, ni se abrevia, ni se "corrige" entre pasos, ni se
  cambia a mitad del trabajo.

Por qué importa: la medición de consumo registra literalmente el texto que
sigue a `$orquestador`, y busca el estado del flujo en
`tsoft-dev/[feature]/orquestador-estado.md`. Si el nombre tipeado no coincide
con la carpeta, esa feature aparece partida en varias filas del reporte y sin
estado. El reconciliador normaliza rutas como red de seguridad, pero no puede
adivinar un nombre mal escrito.

---

## Descripción del proyecto

<!-- Qué hace este proyecto, para qué cliente, cuál es su propósito.
     2-4 oraciones. -->

[Completar]

---

## Stack tecnológico

<!-- Listá las tecnologías principales con sus versiones.
     Ejemplo:
     - Next.js 15.2
     - TypeScript 5.4
     - PostgreSQL 16 (via Prisma 5.x)
     - Tailwind CSS 3.4
-->

- [tecnología y versión]
- [tecnología y versión]

---

## Estructura de carpetas

<!-- Describí las carpetas principales y qué responsabilidad tiene cada una.
     No hace falta listar todo — solo lo que no es obvio.
     Ejemplo:
     /src/app          → rutas y páginas (Next.js App Router)
     /src/components   → componentes reutilizables
     /src/lib          → utilidades y helpers
     /src/services     → lógica de negocio y llamadas a APIs externas
     /src/types        → tipos TypeScript compartidos
-->

[Completar]

---

## Convenciones de código

<!-- Las reglas que todos los archivos deben seguir.
     Sé específico — estas son las instrucciones que el Desarrollador
     va a respetar al pie de la letra.

     Ejemplos de lo que va acá:
     - Nombres de archivos: kebab-case para componentes, camelCase para utils
     - Nombres de funciones: verbos en infinitivo (getUser, createOrder)
     - Manejo de errores: siempre try/catch con log en el catch
     - Imports: absolutos desde /src, nunca relativos de más de un nivel
     - Tipado: strict mode activo, no usar any
-->

[Completar]

---

## Patrones de arquitectura

<!-- Cómo está organizado el código a nivel lógico.
     Ejemplos de lo que va acá:
     - Separación de responsabilidades: controllers → services → repositories
     - Cómo se manejan los estados (Redux, Zustand, Context, etc.)
     - Cómo se hacen las llamadas a APIs externas
     - Cómo se validan los datos de entrada
     - Cómo se manejan las respuestas de error hacia el cliente
-->

[Completar]

---

## Convenciones de base de datos

<!-- Solo si el proyecto tiene base de datos.
     Ejemplos:
     - ORM: Prisma con migraciones versionadas
     - Nombres de tablas: snake_case en plural (users, order_items)
     - Nunca modificar datos directamente — siempre via repository
     - Campos de auditoría obligatorios: created_at, updated_at
-->

[Completar o eliminar esta sección si no aplica]

---

## Testing

<!-- Cómo se testea este proyecto.
     Ejemplos:
     - Framework: Vitest + Testing Library
     - Los tests van en __tests__/ dentro de cada módulo
     - Nomenclatura: [nombre-del-archivo].test.ts
     - Mocks: se generan con vi.mock(), no con datos hardcodeados
-->

[Completar o eliminar esta sección si no aplica]

---

## Lo que nunca se debe hacer

<!-- Prohibiciones explícitas. Las cosas que si el agente hace
     van a romper algo o violar una política del cliente.
     Ejemplos:
     - No commitear archivos .env
     - No modificar archivos en /legacy sin aprobación explícita
     - No usar fetch directo — siempre usar el wrapper en /src/lib/api
     - No agregar dependencias nuevas sin aprobación del IA Maker
-->

- No commitear `tsoft-dev/metrics/` ni `tsoft-dev/reportes/`: contienen los
  prompts, rutas y comandos reales de las sesiones.
- [Completar con las prohibiciones propias del proyecto]

---

## Skills disponibles

<!-- Lista de skills activas en .codex/skills/ que los agentes pueden usar.
     Se actualiza cada vez que se agrega una skill nueva al proyecto.
     Para ver las skills cargadas escribí /skills en el chat de Codex.
     Ejemplo:
     - backend-api         → convenciones para crear endpoints REST
     - frontend-components → cómo construir componentes React
     - db-queries          → patrones para queries con el ORM del proyecto
-->

- `orquestador` → flujo principal del kit para ejecutar una feature con Human
  in the Loop
- `reporte-ejecucion` → genera los reportes de consumo
- [Completar a medida que se agregan skills al proyecto]

---

*TSOFT AI Dev Kit · Codex · v1.0*
