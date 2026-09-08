import { notFound } from "next/navigation";
import { HistoriaActions } from "../../../components/historias/HistoriaActions";
import { Card } from "../../../components/ui/Card";
import { resolveIdentityFromCurrentSession } from "../../../server/auth/resolve-identity";
import { appContext } from "../../../server/app-context";

export const dynamic = "force-dynamic";
export const revalidate = 0;

type HistoriaEstado = Awaited<ReturnType<typeof appContext.historias.listar>>[number]["estado"];

type FlowStage = {
  title: string;
  states: HistoriaEstado[];
  hint: string;
  action: string;
};

const FLOW_STAGES: FlowStage[] = [
  {
    title: "Carga",
    states: ["BORRADOR", "EN_ANALISIS_COMPLETITUD", "INCOMPLETA"],
    hint: "Captura de texto y revision de calidad.",
    action: "Completar o reenviar la historia."
  },
  {
    title: "Calidad",
    states: ["COMPLETA"],
    hint: "La historia ya cumple el umbral minimo.",
    action: "Ir a calcular sizing."
  },
  {
    title: "Sizing",
    states: ["EN_SIZING", "SIZING_CALCULADO"],
    hint: "Extraccion de criterios y calculo deterministico.",
    action: "Validacion del lider."
  },
  {
    title: "Lider",
    states: ["PENDIENTE_VALIDACION_LIDER", "SIZING_VALIDADO"],
    hint: "Aprobacion o correccion del sizing.",
    action: "Publicar al cliente."
  },
  {
    title: "Cliente",
    states: ["PENDIENTE_ACEPTACION_CLIENTE", "RECHAZADA_POR_CLIENTE", "ACEPTADA", "EN_EJECUCION", "ENTREGADA"],
    hint: "Aceptacion final, ejecucion y entrega.",
    action: "Aceptar y descontar consumo."
  }
];

function estadoActual(indicado: HistoriaEstado) {
  const index = FLOW_STAGES.findIndex((stage) => stage.states.includes(indicado));
  return index === -1 ? 0 : index;
}

function siguientePaso(estado: HistoriaEstado) {
  if (estado === "BORRADOR" || estado === "EN_ANALISIS_COMPLETITUD") {
    return {
      title: "Esperando evaluacion de calidad",
      description: "La historia todavia no quedo lista para sizing.",
      cta: "Volver a la carga"
    };
  }

  if (estado === "INCOMPLETA") {
    return {
      title: "Reenviar historia",
      description: "La calidad no paso el umbral minimo. Corrige el texto y vuelve a enviar.",
      cta: "Reenviar historia"
    };
  }

  if (estado === "COMPLETA") {
    return {
      title: "Calcular sizing",
      description: "La historia esta lista para extraer criterios y calcular tamano.",
      cta: "Ir a acciones"
    };
  }

  if (estado === "EN_SIZING" || estado === "SIZING_CALCULADO") {
    return {
      title: "Validacion del lider",
      description: "El sizing ya fue calculado. Falta la revision humana obligatoria.",
      cta: "Abrir acciones"
    };
  }

  if (estado === "PENDIENTE_VALIDACION_LIDER") {
    return {
      title: "Revision del lider",
      description: "La historia espera aprobacion o correccion antes de mostrarse al cliente.",
      cta: "Validar sizing"
    };
  }

  if (estado === "SIZING_VALIDADO" || estado === "PENDIENTE_ACEPTACION_CLIENTE") {
    return {
      title: "Aceptar por cliente",
      description: "El resultado ya puede ser publicado para aceptacion final.",
      cta: "Aceptar o rechazar"
    };
  }

  if (estado === "ACEPTADA" || estado === "EN_EJECUCION") {
    return {
      title: "Cerrar entrega",
      description: "La historia ya fue aceptada y solo resta la entrega operativa.",
      cta: "Entregar"
    };
  }

  return {
    title: "Estado final",
    description: "No hay una accion inmediata pendiente para este registro.",
    cta: "Volver al inicio"
  };
}

function resumenSemaforo(estado: HistoriaEstado) {
  if (estado === "INCOMPLETA" || estado === "BORRADOR" || estado === "EN_ANALISIS_COMPLETITUD") {
    return {
      tone: "rojo",
      titulo: "Aun no pasa el filtro de calidad",
      descripcion: "Primero hay que completar la historia y resolver observaciones."
    };
  }

  if (estado === "COMPLETA" || estado === "EN_SIZING") {
    return {
      tone: "amber",
      titulo: "Lista para sizing",
      descripcion: "La compuerta de calidad ya quedo abierta y ahora entra el calculo deterministico."
    };
  }

  if (estado === "SIZING_CALCULADO" || estado === "PENDIENTE_VALIDACION_LIDER" || estado === "SIZING_VALIDADO") {
    return {
      tone: "blue",
      titulo: "Sizing calculado y en revision",
      descripcion: "Ya existe una estimacion, pero aun falta aprobacion o ajuste del lider."
    };
  }

  return {
    tone: "green",
    titulo: "Flujo encaminado",
    descripcion: "La historia ya paso la etapa tecnica y avanza a aceptacion o cierre."
  };
}

function etiquetaEstado(estado: HistoriaEstado) {
  if (estado === "PENDIENTE_VALIDACION_LIDER") return "pill pill-amber";
  if (estado === "ACEPTADA" || estado === "ENTREGADA" || estado === "SIZING_VALIDADO") return "pill pill-green";
  return "pill pill-blue";
}

function formatState(estado: HistoriaEstado) {
  if (estado === "PENDIENTE_VALIDACION_LIDER") {
    return "Listo para revisar";
  }

  if (estado === "SIZING_VALIDADO") {
    return "Validado";
  }

  if (estado === "COMPLETA") {
    return "Listo para sizing";
  }

  if (estado === "EN_SIZING") {
    return "Calculando sizing";
  }

  return estado;
}

export default async function HistoriaDetallePage({
  params,
  searchParams
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ demo?: string }>;
}) {
  const { id } = await params;
  const { demo } = await searchParams;
  const identity = await resolveIdentityFromCurrentSession().catch(() => null);
  const historia = await appContext.historias.obtenerPorId(id);
  const demoRequested = demo === "1";

  if (!historia) {
    notFound();
  }

  if (!identity && process.env.NODE_ENV === "production" && !demoRequested) {
    notFound();
  }

  const puedeVer =
    demoRequested || !identity || identity.rol === "lider" || identity.clienteId === historia.clienteId;

  if (!puedeVer) {
    notFound();
  }

  const pasoActual = estadoActual(historia.estado);
  const pasoSiguiente = siguientePaso(historia.estado);
  const semaforo = resumenSemaforo(historia.estado);

  return (
    <main>
      <section className="page-hero">
        <span className="pill pill-amber">Historia</span>
        <h1>Detalle de historia</h1>
        <p>Revisa el estado, mira el recorrido del flujo y ejecuta la siguiente accion disponible.</p>
      </section>

      <div className="review-layout">
        <div className="review-main">
          <Card className="card--accent">
            <div className="section-heading">
              <h2>Resumen operativo</h2>
              <p>Vista compacta de la historia, su semaforo tecnico y la posicion real en el flujo.</p>
            </div>

            <div className="review-summary-grid">
              <div className="review-metric">
                <div className="metric-label">Estado</div>
                <div className="metric-value">{historia.estado}</div>
              </div>
              <div className="review-metric">
                <div className="metric-label">Cliente</div>
                <div className="metric-value">{historia.clienteId}</div>
              </div>
              <div className="review-metric">
                <div className="metric-label">ID</div>
                <div className="metric-value review-id">{historia.id}</div>
              </div>
            </div>

            <div className={`signal-banner signal-banner--${semaforo.tone}`}>
              <div className="signal-dot" />
              <div>
                <strong>{semaforo.titulo}</strong>
                <span>{semaforo.descripcion}</span>
              </div>
            </div>

            <div className="summary-list summary-list--tight">
              <div className="summary-row">
                <span>Sizing calculado</span>
                <strong>{historia.sizingCalculado ?? "Pendiente"}</strong>
              </div>
              <div className="summary-row">
                <span>Puntos</span>
                <strong>{historia.puntosCalculados ?? "Pendiente"}</strong>
              </div>
              <div className="summary-row">
                <span>Revision tecnica</span>
                <strong>{formatState(historia.estado)}</strong>
              </div>
            </div>
          </Card>

          <Card>
            <div className="section-heading">
              <h2>Progreso por etapas</h2>
              <p>La fase activa queda resaltada. Si el sizing aparece, ya se paso por la compuerta de calidad.</p>
            </div>
            <div className="status-flow">
              {FLOW_STAGES.map((stage, index) => {
                const activo = index === pasoActual;
                const completado = index < pasoActual;
                return (
                  <div
                    key={stage.title}
                    className="status-step"
                    data-active={activo ? "true" : "false"}
                    data-complete={completado ? "true" : "false"}
                  >
                    <div className="status-step-header">
                      <span className="status-step-index">{String(index + 1).padStart(2, "0")}</span>
                      <strong>{stage.title}</strong>
                    </div>
                    <span>{stage.hint}</span>
                    <em>{stage.action}</em>
                  </div>
                );
              })}
            </div>
          </Card>

          <Card>
            <div className="section-heading">
              <h2>Historia y evidencia</h2>
              <p>El texto original y el OCR quedan separados para mantener la trazabilidad.</p>
            </div>
            <div className="detail-copy-grid">
              <div className="detail-copy">
                <span>Texto original</span>
                <p>{historia.textoOriginal}</p>
              </div>
              {historia.textoOcr ? (
                <div className="detail-copy">
                  <span>Texto OCR</span>
                  <p>{historia.textoOcr}</p>
                </div>
              ) : null}
            </div>
          </Card>
        </div>

        <aside className="review-side">
          <Card className="card--accent">
            <div className="section-heading">
              <h2>Semaforo de calidad</h2>
              <p>Este panel resume si la historia ya tiene forma suficiente para seguir el flujo.</p>
            </div>
            <div className="signal-grid signal-grid--compact">
              <div className={`signal-card signal-card--${semaforo.tone}`}>
                <span>Calidad</span>
                <strong>{semaforo.titulo}</strong>
                <p>{semaforo.descripcion}</p>
              </div>
              <div className="signal-card">
                <span>OCR</span>
                <strong>{historia.textoOcr ? "Disponible" : "Sin OCR"}</strong>
                <p>{historia.contieneContenidoOcr ? "La historia fue marcada con contenido OCR." : "El OCR no se marco como presente."}</p>
              </div>
              <div className="signal-card">
                <span>Sizing</span>
                <strong>{historia.sizingCalculado ? `Listo: ${historia.sizingCalculado}` : "Bloqueado"}</strong>
                <p>{historia.sizingCalculado ? "Ya existe una estimacion calculada." : "Solo se habilita cuando la historia esta completa."}</p>
              </div>
              <div className="signal-card">
                <span>Flujo</span>
                <strong>{FLOW_STAGES[pasoActual].title}</strong>
                <p>{FLOW_STAGES[pasoActual].hint}</p>
              </div>
            </div>
          </Card>

          <Card className="card--accent">
            <div className="section-heading">
              <h2>Proximo paso</h2>
              <p>Esto te indica que accion tiene sentido hacer ahora mismo.</p>
            </div>
            <div className="callout callout-info">
              <strong>{pasoSiguiente.title}</strong>
              <span>{pasoSiguiente.description}</span>
            </div>
            <div className="summary-list summary-list--tight">
              <div className="summary-row">
                <span>Accion sugerida</span>
                <strong>{pasoSiguiente.cta}</strong>
              </div>
              <div className="summary-row">
                <span>Acceso rapido</span>
                <strong>
                  <a href="#acciones">Ir a acciones</a>
                </strong>
              </div>
            </div>
          </Card>

          <Card>
            <HistoriaActions historiaId={historia.id} estado={historia.estado} demoMode={demoRequested || !identity} />
          </Card>

          <Card>
            <div className="section-heading">
              <h2>Guia rapida</h2>
              <p>La vista sigue una secuencia simple: calidad, sizing, validacion y cierre.</p>
            </div>
            <div className="summary-list summary-list--tight">
              <div className="summary-row">
                <span>Etapa activa</span>
                <strong>{FLOW_STAGES[pasoActual].title}</strong>
              </div>
              <div className="summary-row">
                <span>Calcular</span>
                <strong>Solo desde COMPLETA</strong>
              </div>
              <div className="summary-row">
                <span>Validar</span>
                <strong>Solo lider</strong>
              </div>
              <div className="summary-row">
                <span>Aceptar</span>
                <strong>Solo cliente propietario</strong>
              </div>
            </div>
          </Card>
        </aside>
      </div>
    </main>
  );
}
