# Manual del TSOFT AI Dev Kit

Guía completa para desarrolladores del Programa de Adopción IA.

Este kit hace dos cosas: te da un **flujo de desarrollo con agentes** donde vos
mantenés el control en cada paso, y **mide cuánto consumió cada feature** para
que el equipo entienda qué cuesta construir cada cosa.

Herramienta: **Codex**, en la extensión de VS Code o en la terminal. Funciona
igual en las dos.

---

## Índice

1. [Instalación](#1-instalación)
2. [Medición en vivo desde la terminal (opcional)](#2-medición-en-vivo-desde-la-terminal-opcional)
3. [Los agentes](#3-los-agentes)
4. [Trabajar una feature](#4-trabajar-una-feature)
5. [Generar tu reporte](#5-generar-tu-reporte)
6. [Qué se mide](#6-qué-se-mide)
7. [Una sesión típica de punta a punta](#7-una-sesión-típica-de-punta-a-punta)
8. [Problemas frecuentes](#8-problemas-frecuentes)
9. [Estructura del kit](#9-estructura-del-kit)
10. [Las reglas cortas](#10-las-reglas-cortas)

---

## 1. Instalación

### 1.1 Requisitos

| Qué | Cómo verificar |
| --- | --- |
| Codex instalado | Extensión de VS Code, o `codex --version` en la terminal |
| Python 3 | `py --version` en Windows, `python3 --version` en Linux/Mac |

El kit no usa librerías externas: solo la biblioteca estándar de Python. No hay
que instalar nada con `pip`.

### 1.2 Descomprimir el kit

Descomprimí el ZIP del kit **en la raíz de tu proyecto**, de modo que quede
así:

```
tu-proyecto/
├─ src/                  (tu código, lo que ya tenías)
├─ instalar.ps1          ← del kit
├─ plantillas/           ← del kit (plantilla de AGENTS.md)
├─ .codex/               ← del kit
└─ tsoft-dev/            ← del kit
```

`AGENTS.md` todavía no está — lo crea el instalador en el paso siguiente, a
partir de la plantilla. Si tu proyecto ya tiene uno propio, el instalador
**no lo pisa**: lo deja como está y solo avisa.

### 1.3 Correr el instalador

**Windows:**

```powershell
powershell -ExecutionPolicy Bypass -File .\instalar.ps1
```

**Linux / macOS:**

```bash
bash ./instalar.sh
```

El instalador verifica que exista Python y crea las carpetas de métricas. Al
terminar te imprime los pasos manuales que faltan.

> **Sobre las rutas de los hooks.** Codex ejecuta los hooks desde la raíz del
> repositorio, así que `hooks.json` usa rutas **relativas**
> (`.codex\hooks\turn_stop.py`). Eso significa que podés mover el proyecto,
> renombrar carpetas o tener acentos en la ruta sin que la medición se rompa.
>
> Si tu `hooks.json` todavía tiene rutas absolutas del tipo
> `C:\Users\...\.codex\hooks\`, conviene pasarlo a relativas: las rutas
> absolutas se rompen al mover el proyecto, y si la ruta tiene acentos y algún
> editor la guarda mal, **los siete hooks fallan a la vez**.

### 1.4 Marcar el proyecto como confiable

**Este paso es obligatorio.** Codex solo carga los agentes y skills de un
proyecto si está marcado como confiable.

#### La forma fácil: dejá que lo haga Codex

Abrí Codex en la carpeta del proyecto. La primera vez te va a preguntar:

```
Do you trust the contents of this directory?

› 1. Yes, continue
  2. No, quit
```

Respondé **`1. Yes, continue`** y listo: Codex registra la confianza solo, en
el archivo correcto y con el formato correcto. No tenés que editar nada.

#### Si preferís hacerlo a mano

⚠️ **Acá se equivoca casi todo el mundo la primera vez.** Hay **dos archivos
distintos con el mismo nombre**:

| Archivo | Para qué es |
| --- | --- |
| `C:\Users\<tu-usuario>\.codex\config.toml` | **Global del usuario.** Acá va `trust_level` |
| `<tu-proyecto>\.codex\config.toml` | Del proyecto. Configura los subagentes. **Acá NO va** |

En el **global**, al final del archivo:

```toml
[projects.'C:\ruta\completa\a\tu-proyecto']
trust_level = "trusted"
```

Fijate que `trust_level` va **dentro de su propia sección `[projects...]`**, no
suelto ni bajo otra sección.

**Si te equivocás, Codex no arranca** y da este error, que no dice nada sobre
el archivo equivocado:

```
Error loading configuration: ...\.codex\config.toml:21:16:
invalid type: string "trusted", expected a boolean
```

Eso significa que `trust_level` quedó dentro de `[features]`, que solo acepta
`true` o `false`. La solución es borrarlo de ahí y ponerlo donde va — o mejor,
borrarlo y dejar que Codex lo registre respondiendo el prompt de confianza.

Guardá y **reiniciá Codex**.

### 1.5 Completar el AGENTS.md

**Sin esto los agentes trabajan a ciegas.** El `AGENTS.md` es el contexto que
todos leen antes de tocar nada: stack, convenciones de código, arquitectura y
prohibiciones de tu proyecto.

Viene como plantilla con secciones `[Completar]`. Tenés tres formas de
llenarlo:

1. **Que lo genere Codex.** Abrí Codex en el proyecto y pedile:

   > *Analizá la estructura de este repositorio y completá el AGENTS.md con lo
   > que encuentres.*

   Funciona bien en proyectos con código existente.
2. **A mano**, usando las secciones como guía. Mejor para proyectos nuevos o
   cuando querés control fino.
3. **Combinado**: Codex genera el borrador, vos lo revisás y ajustás. Es lo
   recomendado en la mayoría de los casos.

Dos advertencias:

- **Sé específico.** "Usamos buenas prácticas" no le sirve a nadie. "Todas las
  funciones async usan try/catch con log en el catch" sí.
- **No toques la sección "Convención de features"**. Viene completa y es igual
  en todos los proyectos: de ella depende que la medición funcione.

### 1.6 Revisar la configuración

El kit viene con valores por defecto que **no sirven igual para todos los
proyectos**. Están en `tsoft-dev/config/` y conviene mirarlos antes de empezar.

**`baselines.json`** — cómo se clasifica el tipo y la complejidad de cada tarea.
No hay cálculo de horas ahorradas: el kit no lo tiene (ver
[sección 6](#6-qué-se-mide)).

| Valor | Por defecto | Cuándo cambiarlo |
| --- | --- | --- |
| `tipo_default` | `evolutivo-frontend` | Si tu servicio es backend, mobile o datos, poné el que corresponda |
| `tipos_validos` | Los nueve tipos del kit | Normalmente no hace falta tocarlo |
| `umbrales_complejidad` | `media: 4`, `alta: 12` ediciones | Si tu equipo declara siempre `#complejidad:`, esto casi no se usa |

**`celula.json`** — precios y conversiones.

| Valor | Por defecto | Cuándo cambiarlo |
| --- | --- | --- |
| `precios_usd_por_millon` | Precios de lista de OpenAI | Cuando cambien, o si usás otro modelo |
| `moneda_local` | `ARS` | Poné la de tu país: `CLP`, `PEN`, `MXN`, la que sea |
| `usd_a_moneda_local` | `1500` | **Verificalo siempre.** Es el tipo de cambio y queda desactualizado rápido |

Si dejás `usd_a_moneda_local` en `0`, los reportes muestran solo dólares y no
convierten nada. Es preferible eso a mostrar una conversión vieja.

Ante la duda, consultá con el responsable del kit en tu servicio antes de
cambiar valores: si cada uno usa una vara distinta, los reportes dejan de ser
comparables entre equipos.

### 1.7 Verificar que quedó todo bien

Tres chequeos rápidos:

**El kit responde.** Abrí Codex en la carpeta del proyecto y escribí `$`. Tiene
que aparecerte `orquestador` en la lista.

Si al abrir Codex ves este aviso **antes del banner**, el skill no cargó:

```
⚠ Skipped loading 1 skill(s) due to invalid SKILL.md files.
```

Es fácil pasarlo por alto porque aparece una línea arriba de todo. Ver
[sección 9](#9-problemas-frecuentes).

**La medición funciona.** Corré la suite completa del kit:

```powershell
py -m unittest discover -s tsoft-dev/scripts/tests
```

La corrida tiene que cerrar en `OK`.

**El reporte se genera.** Todavía sin datos, pero debe correr sin errores:

```powershell
py tsoft-dev/scripts/reconciliador.py
```

Si algo falla, mirá la [sección 9](#9-problemas-frecuentes).

---

## 2. Medición en vivo desde la terminal (opcional)

El kit tiene **dos formas de medir** que conviven.

> ### La regla, en una línea
>
> **El reporte del equipo sale siempre del reconciliador**, trabajes en VS Code
> o en la terminal. Los hooks son una herramienta personal del que usa CLI: le
> dan medición en vivo y horas estimadas para su propio seguimiento, pero **no
> alimentan el reporte que se junta**.
>
> Es a propósito. Si cada dev reportara con la vía de su entorno, los números no
> serían comparables: agrupan distinto —el reconciliador por feature, los hooks
> por sesión— y solo una trae la cuota semanal. Con dos varas distintas, el
> reporte del equipo no se puede sumar ni comparar.

| | Reconciliador | Hooks |
| --- | --- | --- |
| Cómo se activa | Solo. No configurás nada | Hay que confiarlos con `/hooks` |
| Dónde funciona | VS Code y terminal | Confiable solo en terminal |
| Sirve para el reporte del equipo | **Sí, siempre** | No: uso personal |
| Cuándo ves los datos | Cuando corrés el reporte | En vivo, al cerrar cada turno |
| Qué mide | Tokens, tiempo, costo, feature, evidencia | Lo mismo, **más cuota semanal** |
| Salida | `tsoft-dev/reportes/features.md` | `tsoft-dev/reportes/ejecuciones/` y `consolidado.md` |

**Si trabajás en VS Code:** no hagas nada. El reconciliador te cubre. Los hooks
en la extensión no disparan de forma confiable — es un problema conocido de la
integración, y justamente por eso existe el reconciliador.

**Si trabajás en la terminal:** activarlos es opcional y solo para vos. Ganás la
medición en vivo y la cuota semanal. Para el reporte del equipo seguís
corriendo el reconciliador igual que todos.

```
codex
/hooks
```

Revisá y confiá los **siete hooks** del kit:

| Hook | Qué hace |
| --- | --- |
| `SessionStart` | Abre el registro de la sesión |
| `UserPromptSubmit` | Captura las etiquetas `#tarea:`, `#complejidad:`, `#ticket:` |
| `PostToolUse` | Registra archivos tocados y comandos ejecutados |
| `SubagentStart` | Abre el registro de un subagente |
| `SubagentStop` | Escribe el consumo propio de ese subagente |
| `Stop` | Cierra el turno y genera el reporte de ejecución |
| `SessionEnd` | Cierre final de la sesión |

> **Sobre la confianza de los hooks.** Codex registra la confianza contra la
> **definición** de cada hook en `hooks.json` — el comando, el evento, el
> timeout— y no contra el contenido del script `.py`.
>
> Traducido: **editar un `.py` no te obliga a volver a confiar**. Cambiar una
> ruta o un timeout en `hooks.json`, sí.

### Si usás las dos: nunca las sumes

Las dos formas no se pisan —escriben en archivos distintos y podés tenerlas
activas a la vez— pero **miden lo mismo desde la misma fuente**. Son dos vistas
del mismo consumo, no dos consumos.

- ✅ `features.md` para reportar; `consolidado.md` para tu seguimiento
- ❌ Nunca sumes el total de uno con el total del otro

Los totales no van a coincidir, y es esperable: el reconciliador lee **todos**
tus rollouts de Codex, mientras que el ledger solo tiene las sesiones donde los
hooks dispararon.

---

## 3. Los agentes

### La idea: vos decidís, ellos ejecutan

El kit se organiza alrededor de un **orquestador** que coordina cinco agentes
especializados. La regla que gobierna todo es simple: **nada avanza sin tu
aprobación explícita**.

Después de cada etapa el orquestador te muestra un resumen y se detiene. Podés
aprobar, pedir ajustes, pausar o saltar a otra etapa. No hay piloto automático.

Hay una pausa que no se puede saltear bajo ninguna circunstancia: **antes de
que el Desarrollador escriba una sola línea de código**, el orquestador te
muestra el plan completo y espera tu visto bueno.

### Los cinco agentes

| Agente | Qué hace | Produce |
| --- | --- | --- |
| **Explorador** | Lee tu material y arma el scope. Convierte lo ambiguo en preguntas concretas | `explorador-output.md` |
| **Planificador** | Diseña el plan técnico: qué archivos, en qué orden, con qué complejidad | `design.md` |
| **Desarrollador** | Ejecuta el plan aprobado, archivo por archivo | El código, y actualiza `design.md` |
| **Documentador** | Documenta lo construido para el que venga después | `feature-doc.md` |
| **QA** | Genera casos de prueba y los corre si hay framework | `qa.md` |

Todos usan el mismo modelo. El Documentador corre en esfuerzo de
razonamiento medio; los otros cuatro —Explorador, Planificador,
Desarrollador y QA— en high, porque deciden arquitectura, ejecutan pasos
donde un error sale caro, o ambas cosas.

Todo lo que producen queda en `tsoft-dev/[feature]/`.

> ### ⚠️ Sobre los permisos de los agentes — leelo
>
> Los cinco `.codex/agents/*.toml` declaran `sandbox_mode = "workspace-write"`
> — cada uno puede escribir en todo el proyecto, no solo en su propio
> artefacto.
>
> En Codex, un subagente **hereda la política de sandbox de la sesión padre**,
> así que la restricción real nunca vino del `sandbox_mode` declarado: viene
> de que cada agente tiene instrucción explícita de tocar solo su propio
> archivo (`explorador-output.md`, `design.md`, el código del plan, etc.).
>
> **La separación de roles del kit es una convención del prompt, no un
> guardrail técnico.** Funciona porque los agentes tienen instrucciones claras
> y porque vos aprobás cada paso — no porque el sistema se lo impida.
>
> Consecuencia práctica: **el control real sos vos.** La pausa de aprobación
> antes del Desarrollador no es una formalidad; es el único punto donde algo
> puede frenarse antes de tocar tu código.

### Cómo te hablan los agentes

Los agentes especializados **no pueden hablar con vos directamente**. Corren de
punta a punta y devuelven un resultado; no pueden frenar a mitad de camino para
preguntarte algo.

Tampoco heredan la conversación: **un subagente arranca sin ver nada de lo que
hablaste con el orquestador**. Lo único que tiene es el prompt con el que lo
spawnearon y el acceso al repositorio. Por eso el orquestador le pasa el
contexto completo en cada invocación, incluidas tus respuestas anteriores.

Cuando el Explorador encuentra algo ambiguo, **no lo adivina**: lo deja escrito
como pregunta numerada, y el orquestador te la trae al chat:

```
El Explorador dejó 2 preguntas pendientes:

1. ¿El descuento del 10% aplica sobre el monto bruto o sobre el neto?
2. ¿Se permite pagar con más de una tarjeta?
```

Vos respondés y el orquestador lo reinvoca con tus respuestas incorporadas. Eso
se repite hasta que el scope queda sin ambigüedades.

**Los bloqueos funcionan parecido.** Si un agente encuentra algo que no puede
resolver —una decisión de arquitectura con varias opciones válidas, una
dependencia que falta— se detiene y lo reporta con ⚠️. El orquestador no invoca
al siguiente hasta que vos decidas cómo seguir.

### El Desarrollador no improvisa

Vale la pena saberlo porque cambia cómo trabajás con él: el Desarrollador
**ejecuta el plan y nada más**. Si encuentra algo que el plan no contempló, se
detiene y lo reporta en vez de resolverlo por su cuenta.

Eso es a propósito. Significa que la calidad de lo que construye depende de la
calidad del plan que aprobaste — vale la pena leer el `design.md` con atención
antes de darle el sí.

---

## 4. Trabajar una feature

### La convención — importante

Toda feature usa **el mismo nombre en tres lugares**:

```
docs/mi-feature/          el material: brief, notas, mockups, lo que tengas
tsoft-dev/mi-feature/     lo que genera el kit (no lo tocás vos)
$orquestador mi-feature   cómo lo invocás
```

El nombre se escribe **pelado**: sin `docs/`, sin barra final, sin `.md`.

Esto no es capricho: si el nombre no coincide, tu feature aparece partida en
varias filas del reporte y sin estado. Y si la renombrás a mitad del trabajo,
quedan dos features distintas.

### El flujo

**1. Poné el material.** Creá `docs/mi-feature/` y meté adentro lo que describa
la feature. Puede ser un archivo o varios:

```
docs/checkout-express/
├─ brief.md
├─ mockup.png
└─ notas-reunion.md
```

**2. Invocá al orquestador, declarando el tipo de tarea:**

```
$orquestador checkout-express #tarea:evolutivo-frontend #complejidad:media
```

Las etiquetas son opcionales pero **valen mucho**: sin ellas el kit tiene que
inferir el tipo de tarea, y de eso depende qué tan confiable es la
clasificación de consumo que ves en el reporte. Ver la [sección 6](#6-qué-se-mide).

**3. Elegí desde dónde arrancar.** Si es una feature nueva, el orquestador te
ofrece el menú de etapas. Lo normal es empezar por el Explorador.

**4. Seguí el ciclo.** Por cada agente: ves el resumen, resolvés las preguntas
si las hay, aprobás o pedís ajustes, y decidís si continuar.

**5. Pausá cuando quieras.** El estado queda guardado en
`tsoft-dev/[feature]/orquestador-estado.md`. Para retomar, escribís lo mismo:

```
$orquestador checkout-express
```

El orquestador te dice en qué etapa quedaste y te ofrece continuar.

### Si la feature es chica

No hace falta pasar por las cinco etapas. Si es un cambio de una línea o
puramente visual, decile al orquestador que arranque desde el Planificador o
directamente desde el Desarrollador.

Vale la pena: una feature trivial pasada por todo el flujo consume varias veces
más de lo necesario, sin que eso aporte nada.

**Y no te cuesta poder cerrarla.** Las etapas que salteás a propósito quedan
marcadas con ⏭ en el archivo de estado, y cuentan igual que las completadas:

| Símbolo | Significa |
| --- | --- |
| ✅ | Corrió y lo aprobaste |
| ⏭ | Salteada a propósito, por decisión tuya |
| ⏸ | Todavía no corrió y sigue pendiente |

Una feature se marca `completado` cuando **no queda ninguna etapa en ⏸**. Así
que ahorrar consumo salteando etapas no te deja la feature trabada en "en
curso" para siempre.

---

## 5. Generar tu reporte

**Este es el reporte del equipo, y lo corren todos** — trabajes en VS Code o en
la terminal. Sale del reconciliador, que lee los rollouts que Codex guarda por
su cuenta en los dos entornos.

Al final de la semana, corré estos dos comandos **en este orden**:

```powershell
py tsoft-dev/scripts/reconciliador.py               # procesa el consumo
py tsoft-dev/scripts/reporte_features.py --semana   # genera el reporte
```

Y compartí el archivo que se genera:

```
tsoft-dev/reportes/features.md
```

Podés correrlos las veces que quieras: el reconciliador regenera todo desde
cero, así que dos corridas seguidas dan exactamente lo mismo.

### El atajo, si estás en Windows

`generar-reportes.ps1` hace los dos pasos y además genera el HTML, en un solo
comando:

```powershell
.\generar-reportes.ps1              # semanal, lo que vas a usar el viernes
.\generar-reportes.ps1 diario
.\generar-reportes.ps1 acumulado    # todo lo registrado
.\generar-reportes.ps1 semanal 2026-08-10   # una semana pasada
```

Es exactamente lo mismo que los comandos de arriba, no un cálculo distinto.
Si trabajás en Linux o macOS no tenés este atajo: usá los dos comandos.

### Semanal o acumulado

`--semana` te da **los últimos 7 días**, que es el corte que se comparte cada
viernes. Sin el flag, el reporte es el **acumulado histórico**: todo lo
registrado desde que instalaste el kit.

| Comando | Qué contesta |
| --- | --- |
| `reporte_features.py --semana` | Qué pasó esta semana |
| `reporte_features.py` | Cuánto costó cada feature en total |

Las dos lecturas son útiles y ninguna reemplaza a la otra. El acumulado es el
que te dice el costo real de una feature; el semanal es el del reporte de
gestión.

Si una feature arrancó una semana y cerró la siguiente, el reporte semanal te
avisa que hay consumo fuera del período — ese número es la parte de esta
semana, no el total de la feature.

Otras variantes, si las necesitás:

```powershell
py tsoft-dev/scripts/reporte_features.py --semana --fecha 2026-08-15
py tsoft-dev/scripts/reporte_features.py --desde 2026-08-01 --hasta 2026-08-15
py tsoft-dev/scripts/reporte_features.py --diario
```

> **Antes del primer comando no hay ningún archivo de medición, y eso es
> normal.** `tsoft-dev/metrics/features.jsonl` no existe hasta que corrés
> `reconciliador.py` — no se va escribiendo mientras trabajás. Codex guarda el
> registro de tus conversaciones por su cuenta, y el reconciliador lo lee recién
> cuando se lo pedís. Si no ves la carpeta `metrics/` con contenido, no perdiste
> nada: falta correr el comando.

### Qué vas a ver

| Feature | Estado | Tokens | Tiempo activo | Turnos | Conversaciones | USD |
| --- | --- | --- | --- | --- | --- | --- |
| checkout-express | completado | 5.141.058 | 0,42 h | 17 | 3 | $2,31 |

- **Estado** sale del avance real del flujo: `en curso`, `pausado` o
  `completado` cuando no queda ninguna etapa pendiente (todas ✅ o ⏭).
- **Tiempo activo** descarta las pausas de más de 30 minutos. Si retomás una
  feature al otro día, no se cuentan las horas del medio.
- **Conversaciones** es en cuántas charlas de Codex trabajaste esa feature,
  incluyendo las de los agentes especializados.

### Si preferís un reporte visual

Agregá `--html` y sale el mismo reporte con el diseño TSOFT, presentable para
mandar por mail o mostrarle a tu líder:

```powershell
py tsoft-dev/scripts/reconciliador.py
py tsoft-dev/scripts/reporte_features.py --semana --html
```

Se genera en `tsoft-dev/reportes/features.html`, al lado del Markdown. Es un
archivo solo, con los estilos adentro: se abre en cualquier navegador y se
puede adjuntar sin que se despeine.

El Markdown se sigue generando igual, con o sin el flag. **No sumes los dos**:
es la misma información con otra presentación.

También podés pedirlo por la skill, sin acordarte de los comandos:

```
$reporte-html
```

Si querés cambiar los colores o la marca, dejá tu CSS en
`tsoft-dev/config/estilos-reporte.css` y ese reemplaza al que viene. No hay que
tocar código.

---

## 6. Qué se mide

| Dato | De dónde sale |
| --- | --- |
| Tokens | Los registros que Codex escribe por conversación |
| Costo USD | Los tokens al precio de lista del modelo. Es un valor de referencia, para comparar features entre sí |
| Tiempo activo | Las marcas de tiempo de cada intercambio, descartando las pausas de más de 30 minutos |
| Feature | Tu invocación `$orquestador`, o los archivos que tocó la conversación |
| Estado | El archivo de avance que mantiene el orquestador |
| Consumo por subagente | Los eventos `SubagentStart` / `SubagentStop`, con el transcript propio de cada uno |

### El consumo de los subagentes se suma, no se reemplaza

Cada subagente corre en su propia conversación y consume aparte del
orquestador. **No están incluidos en el total del padre.**

Y no es un detalle chico: en una sesión medida, el orquestador consumió 210.642
tokens y el subagente que despachó consumió 454.247 — más del doble.

Por eso el reporte de ejecución muestra las dos cosas por separado y un total
real:

```
| Consumo de la sesion | Tokens  | Costo USD |
| Orquestador          | 210.642 | $0.1854   |
| Subagentes (1)       | 454.247 | $0.3864   |
| Real                 | 664.889 | $0.5718   |
```

Si mirás solo el número del orquestador, estás subcontando todo lo que se
delegó.

### Declarar el tipo de tarea

El tipo y la complejidad son metadato descriptivo: sirven para agrupar consumo
y costo por tipo de trabajo (por ejemplo, cuántos tokens consume en promedio
una tarea `evolutivo-frontend` de complejidad `alta`), no para calcular un
ahorro en horas. El kit no tiene formula de horas-hombre — ver la nota más
abajo sobre por qué se descartó.

El kit resuelve la clasificación en tres niveles, de mejor a peor:

| Origen | Qué significa |
| --- | --- |
| `declarado` | Lo dijiste con `#tarea:` y `#complejidad:`. Es el bueno |
| `inferido` | El kit lo dedujo por los archivos tocados y la cantidad de ediciones |
| `default` | Nadie clasificó nada y cayó en `tipo_default` por descarte |

El reporte de ejecución te muestra el origen de cada dimensión por separado
—puede ser el tipo declarado y la complejidad inferida— así sabés cuánto confiar
en el dato.

**Los nueve tipos válidos son exactamente estos:**

`evolutivo-backend` · `evolutivo-frontend` · `evolutivo-fullstack` ·
`mantenimiento-correctivo` · `refactor` · `analisis` · `documentacion` ·
`devops` · `pruebas`

⚠️ **Escribilos completos.** Un tipo inventado —`evolutivo` a secas, por
ejemplo— no está en `tipos_validos` de `baselines.json`, y el reporte te avisa
cuando pasa.

### Por qué no hay horas-hombre ahorradas

Versiones anteriores del kit calculaban un "HH ahorradas" comparando una tabla
de horas manuales estimadas contra el tiempo de supervisión. Se descartó el
2026-08-27: no hay forma no sesgada de saber cuánto tardaría una tarea a mano
en un equipo que ya trabaja con el kit desde el día 0 del proyecto — no queda
material histórico comparable, y la única fuente que sobrevive con el tiempo
(preguntarle al dev que ya la hizo con el agente "¿cuánto habrías tardado
sin?") es la peor posible: doble sesgo, y el dev genuinamente no lo sabe.

Se prefirió sacar la métrica antes que reportar un número que nadie puede
defender. El kit mide lo que sí puede medir de forma honesta: tokens, costo
de referencia y duración real de la sesión.

### Una aclaración sobre los números

Más tokens no significa peor trabajo. Una feature compleja consume más que una
simple. Esto mide el tamaño del problema, no tu rendimiento.

---

## 7. Una sesión típica de punta a punta

```
Vos:  $orquestador checkout-express #tarea:evolutivo-frontend #complejidad:media

Kit:  🚀 Nueva feature: checkout-express
      ¿Desde dónde querés arrancar?
      1. Explorador  2. Planificador  3. Desarrollador  4. Documentador  5. QA

Vos:  1

Kit:  [spawnea el Explorador]
      Scope validado. Puntos clave:
      - Checkout en un paso para usuarios registrados
      - Reutiliza el carrito actual
      - Fuera de alcance: pago con múltiples tarjetas

      Dejó 2 preguntas pendientes:
      1. ¿El descuento del 10% aplica sobre el bruto o sobre el neto?
      2. ¿Se permite invitado sin registro?

Vos:  1 - sobre el neto.  2 - no, solo registrados.

Kit:  [spawnea el Explorador de nuevo, con tus respuestas en el prompt]
      ✅ Explorador completado y aprobado.
      ¿Continuar con Planificador?

Vos:  sí

Kit:  [spawnea el Planificador]
      Plan: 3 archivos nuevos, 2 modificados. Complejidad media.
      Decisión de arquitectura: el descuento se calcula en el service,
      no en el componente, para poder testearlo aislado.

      ⚠️ Antes de invocar al Desarrollador necesito tu aprobación
      explícita del design.md. Te lo muestro completo:
      [...]

Vos:  aprobado

Kit:  [spawnea el Desarrollador]
      ✅ src/services/checkout.ts — cálculo de descuento sobre neto
      ✅ src/components/CheckoutExpress.tsx — formulario de un paso
      ⚠️ src/api/orders.ts — el plan no contemplaba el caso de carrito
         vacío. Me detengo y te consulto.

Vos:  si el carrito está vacío, redirigí al catálogo

      ... y así hasta QA
```

Al cerrar, el orquestador marca la feature como completada y su consumo queda
como definitivo en el reporte.

---

## 8. Problemas frecuentes

### Instalación

| Síntoma | Causa probable |
| --- | --- |
| `$orquestador` no aparece al escribir `$` | El proyecto no está marcado como confiable, o abriste una subcarpeta en vez de la raíz |
| `Skipped loading 1 skill(s) due to invalid SKILL.md files` | El `SKILL.md` tiene un salto de línea o un BOM **antes** del primer `---`. Ver abajo |
| `invalid type: string "trusted", expected a boolean` | Pusiste `trust_level` en el `config.toml` del proyecto en vez del global, o quedó bajo `[features]`. Ver [1.4](#14-marcar-el-proyecto-como-confiable) |
| El instalador dice que no encuentra `hooks.json` | Descomprimiste el ZIP parcialmente. Volvé a extraerlo completo |
| `failed to parse hooks config ... expected value at line 1 column 1` | El `hooks.json` quedó con un BOM al principio |
| `py` no se reconoce como comando | Falta Python 3. En Linux/Mac probá `python3` |
| Cambié un agente o el AGENTS.md y no se aplica | Reiniciá Codex: esos archivos se cargan al iniciar la sesión |

**El skill no carga por el frontmatter.** El `SKILL.md` tiene que empezar
**exactamente** con `---`, sin ningún byte antes. Un salto de línea o un BOM
que agregó el editor lo desactiva entero, y el aviso aparece una línea arriba
del banner, fácil de pasar por alto. Verificá:

```powershell
[System.IO.File]::ReadAllBytes('.codex\skills\orquestador\SKILL.md')[0..3] -join ','
```

Tiene que dar `45,45,45,10`. Si empieza con `10` (salto de línea) o `239`
(BOM), corregilo:

```powershell
$p='.codex\skills\orquestador\SKILL.md'
$t=[System.IO.File]::ReadAllText($p).TrimStart([char]10,[char]13,[char]65279)
[System.IO.File]::WriteAllText($p,$t,[System.Text.UTF8Encoding]::new($false))
```

### Hooks

| Síntoma | Causa probable |
| --- | --- |
| `hook (failed) — error: hook exited with code 1` | Casi siempre la ruta del `hooks.json` no existe. Ver abajo |
| Los hooks no corren y no dice nada | No los confiaste. Corré `/hooks` dentro de Codex |
| Pide confiar los hooks después de tocar un `.py` | No debería. Si pasa, cambió también `hooks.json` |
| El reporte no muestra subagentes | Faltan `SubagentStart` / `SubagentStop` en `hooks.json` |

**Verificar que las rutas de los hooks existen:**

```powershell
$j=Get-Content ".codex\hooks.json" -Raw -Encoding UTF8|ConvertFrom-Json
foreach($e in $j.hooks.PSObject.Properties.Name){
  foreach($g in $j.hooks.$e){ foreach($h in $g.hooks){
    if($h.commandWindows -match '([a-z_]+\.py)'){
      "$e -> $(Test-Path ".codex\hooks\$($Matches[1])")" } } } }
```

Todos tienen que dar `True`.

### ⚠️ Nunca uses `Set-Content -Encoding UTF8`

En PowerShell 5.1, `Set-Content -Encoding UTF8` escribe un **BOM** al principio
del archivo. Los scripts Python del kit rechazan esa línea, y en un `.jsonl` te
hace perder el primer registro en silencio.

Para cualquier archivo que lea Python —`hooks.json`, `SKILL.md`,
`ledger.jsonl`, los `.json` de config— usá siempre:

```powershell
[System.IO.File]::WriteAllText($ruta, $texto, [System.Text.UTF8Encoding]::new($false))
```

Y si el archivo tiene acentos en la ruta o en el contenido, leelo con
`-Encoding UTF8` explícito: `Get-Content` en PowerShell 5.1 asume ANSI por
defecto y corrompe los acentos al reescribir.

### Uso

| Síntoma | Causa probable |
| --- | --- |
| El Explorador dice que no encuentra el material | La carpeta `docs/[feature]/` no existe o el nombre no coincide |
| Los agentes proponen cosas que no van con el proyecto | El `AGENTS.md` está sin completar o es muy vago |
| El Desarrollador se detiene seguido | El plan tenía huecos. Revisá el `design.md` con más detalle |
| El orquestador escribe él mismo el output de una etapa | No debería: tiene que spawnear el subagente. Pedíselo explícitamente |
| `py -3 -m unittest discover` falla con `PermissionError [WinError 5]` o `FileNotFoundError [WinError 3]` | Ver "Carpeta temporal restringida" abajo |

### Carpeta temporal restringida (Windows corporativo)

En una máquina con `%TEMP%` bloqueada por política de la empresa, la suite
de tests puede fallar en decenas de casos al crear o limpiar carpetas
temporales, aunque el kit en sí funcione bien (visto en una migración real
con Codex). Los tests ya toleran bloqueos transitorios (reintentan con
backoff antes de fallar), así que si todavía falla:

- Confirmá que la ruta de `%TEMP%`/`%TMP%` existe y es escribible:
  `Test-Path $env:TEMP` tiene que dar `True`.
- Si redirigís `TEMP`/`TMP` a una carpeta propia del proyecto, **creala
  primero** — `New-Item -ItemType Directory -Force .tmp-tests` antes de
  `$env:TEMP = (Resolve-Path .tmp-tests)`. Apuntar la variable a una
  carpeta que no existe todavía produce el mismo `WinError 3`.
- Si el problema persiste, es un antivirus/EDR escaneando archivos recién
  creados, no un bug del kit: probá desactivar el escaneo en tiempo real
  para esa carpeta o correr la suite fuera de la política restrictiva.

### Reportes

| Síntoma | Causa probable |
| --- | --- |
| El reporte sale vacío | Corriste `reporte_features.py` sin correr antes `reconciliador.py` |
| `reconciliador.py` dice `Registros: 0` pese a haber trabajado mucho | Estás corriendo Codex con `CODEX_HOME` seteada a otra ruta (algunas herramientas de orquestación lo hacen para poder leer la transcripción). El reconciliador ya respeta esa variable; si igual da 0, confirmá con `echo $env:CODEX_HOME` que apunta a donde Codex realmente guarda los rollouts |
| `ATENCION: el tipo de tarea X no existe` | Escribiste mal la etiqueta `#tarea:`. Ver los nueve tipos válidos |
| `aviso: N linea(s) ilegibles en ledger.jsonl` | Una línea del ledger quedó rota. El reporte sale igual, sin esos registros |
| Tu feature aparece dos veces | La invocaste con nombres distintos, o la renombraste a mitad |
| Trabajás en terminal y todo cae en `sin-feature` | Versión vieja de `metrics_lib.py`. Los rollouts de CLI guardan el prompt en otro formato y el parser no lo leía. Actualizá el kit |
| Trabajás en terminal y los turnos dan 0 | Misma causa que el anterior |
| La feature dice "estado desconocido" | No existe `tsoft-dev/[feature]/orquestador-estado.md` |
| Una feature dice "sin tarifar" | Usó un modelo sin precio cargado |
| Aparece consumo en `sin-feature` | Normal: consultas sueltas fuera del flujo de una feature |
| Los totales de `features.md` y `consolidado.md` no coinciden | Es esperable. No los sumes |

---

## 9. Estructura del kit

```
tu-proyecto/
├─ AGENTS.md                     contrato operativo: lo leen todos los agentes
│                                 (lo crea el instalador desde plantillas/)
├─ MANUAL-DEV.md                 este archivo
├─ instalar.ps1 / instalar.sh    instaladores
├─ generar-reportes.ps1          atajo: procesa el consumo y genera los reportes
├─ plantillas/AGENTS.md          plantilla del kit, con la Convención de features
├─ docs/[feature]/               tu material por feature
├─ .codex/
│  ├─ config.toml                configuración de subagentes
│  ├─ hooks.json                 los 7 hooks, con rutas relativas
│  ├─ agents/                    los 5 agentes especializados
│  ├─ hooks/                     los 7 hooks de medición
│  └─ skills/orquestador/        el flujo Human in the Loop
└─ tsoft-dev/
   ├─ [feature]/                 lo que genera el kit por feature
   ├─ config/                    precios y clasificación de tareas
   ├─ scripts/                   la medición y sus pruebas
   ├─ metrics/                   datos procesados (no se versiona)
   └─ reportes/features.md       tu reporte
```

**No subas al repositorio** `tsoft-dev/metrics/` ni `tsoft-dev/reportes/`:
contienen los prompts y comandos reales de tus sesiones.

El instalador **no toca el `.gitignore` del proyecto** — no es su lugar,
esas reglas son del cliente. Solo avisa y te deja el comando exacto para
correr vos.

**Caso 1 — proyecto nuevo, todavía no versionaste nada de esto.** Alcanza con
excluirlo. Elegí `.gitignore` si el equipo quiere compartir la regla, o
`.git/info/exclude` si preferís mantenerla solo en tu copia local (esta
segunda no se comitea):

```powershell
# PowerShell
Add-Content .git\info\exclude "tsoft-dev/metrics/"
Add-Content .git\info\exclude "tsoft-dev/reportes/"
```

```bash
# Bash
printf 'tsoft-dev/metrics/\ntsoft-dev/reportes/\n' >> .git/info/exclude
```

**Caso 2 — las carpetas ya quedaron trackeadas** (por ejemplo, alguien corrió
`git add -A` antes de instalar el kit). Acá excluirlas **no alcanza**: Git ya
las tiene en el índice y las sigue versionando aunque aparezcan en
`.gitignore`. Hay que sacarlas del índice explícitamente:

```bash
git rm -r --cached tsoft-dev/metrics tsoft-dev/reportes
```

Este comando es el mismo en PowerShell y en Bash. **`--cached` saca los
archivos del índice de Git, pero no los borra de tu disco** — seguís
teniendo tus datos locales, solo dejan de subirse en el próximo commit.
Después de correrlo, agregá también la exclusión del Caso 1 para que no
vuelvan a trackearse.

El instalador detecta este caso automáticamente y te avisa si hace falta.

> **El `ledger.jsonl` no está versionado y no se recupera.** Es el único
> archivo del kit sin red de seguridad en git. Si te importa el histórico de
> medición, copialo a algún lado cada tanto.

---

## 10. Las reglas cortas

1. Completá el `AGENTS.md` antes de usar el kit. Sin eso los agentes trabajan
   a ciegas.
2. Una feature = un nombre = tres lugares (`docs/`, `tsoft-dev/`, invocación).
3. El nombre se invoca pelado: `$orquestador mi-feature`.
4. **Declará el tipo de tarea**: `#tarea:` y `#complejidad:` en la invocación.
   Es la diferencia entre una clasificación declarada y una inferida — afecta
   qué tan confiable es el reporte.
5. Usá los nueve tipos exactos. Un tipo inventado no entra en `tipos_validos`
   y el reporte te avisa.
6. No renombres una feature a mitad del trabajo.
7. Leé el `design.md` con atención antes de aprobarlo: el Desarrollador lo
   sigue al pie de la letra.
8. Si el cambio es trivial, arrancá desde una etapa más avanzada. Las etapas
   salteadas quedan en ⏭ y la feature se cierra igual.
9. Al final de la semana: los dos comandos del reconciliador y compartís
    `features.md`. **Eso vale para todos**, uses VS Code o terminal.
10. Los hooks son para tu seguimiento personal, no para el reporte del equipo.
    Nunca sumes sus totales con los de `features.md`.
11. El consumo de los subagentes **se suma** al del orquestador, no lo
    reemplaza.
12. Nunca uses `Set-Content -Encoding UTF8` sobre archivos que lee el kit.

---

*TSOFT AI Dev Kit · Codex · Human in the Loop*
