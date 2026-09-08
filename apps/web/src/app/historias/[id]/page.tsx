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
    hint: "Captura de texto y revisión de calidad.",
    action: "Completar o reenviar la historia."
  },
  {
    title: "Calidad",
    states: ["COMPLETA"],
    hint: "La historia ya cumple el umbral mínimo.",
    action: "Ir a calcular sizing."
  },
  {
    title: "Sizing",
    states: ["EN_SIZING", "SIZING_CALCULADO"],
    hint: "Extracción de criterios y cálculo determinístico.",
    action: "Validación del líder."
  },
  {
    title: "Líder",
    states: ["PENDIENTE_VALIDACION_LIDER", "SIZING_VALIDADO"],
    hint: "Aprobación o corrección del sizing.",
    action: "Publicar al cliente."
  },
  {
    title: "Cliente",
    states: ["PENDIENTE_ACEPTACION_CLIENTE", "RECHAZADA_POR_CLIENTE", "ACEPTADA", "EN_EJECUCION", "ENTREGADA"],
    hint: "Aceptación final, ejecución y entrega.",
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
      title: "Esperando evaluación de calidad",
      description: "La historia todavía no quedó lista para sizing.",
      cta: "Volver a la carga"
    };
  }

  if (estado === "INCOMPLETA") {
    return {
      title: "Reenviar historia",
      description: "La calidad no pasó el umbral mínimo. Corrige el texto y vuelve a enviar.",
      cta: "Reenviar historia"
    };
  }

  if (estado === "COMPLETA") {
    return {
      title: "Calcular sizing",
      description: "La historia está lista para extraer criterios y calcular tamaño.",
      cta: "Ir a acciones"
    };
  }

  if (estado === "EN_SIZING" || estado === "SIZING_CALCULADO") {
    return {
      title: "Validación del líder",
      description: "El sizing ya fue calculado. Falta la revisión humana obligatoria.",
      cta: "Abrir acciones"
    };
  }

  if (estado === "PENDIENTE_VALIDACION_LIDER") {
    return {
      title: "Revisión del líder",
      description: "La historia espera aprobación o corrección antes de mostrarse al cliente.",
      cta: "Validar sizing"
    };
  }

  if (estado === "SIZING_VALIDADO" || estado === "PENDIENTE_ACEPTACION_CLIENTE") {
    return {
      title: "Aceptar por cliente",
      description: "El resultado ya puede ser publicado para aceptación final.",
      cta: "Aceptar o rechazar"
    };
  }

  if (estado === "ACEPTADA" || estado === "EN_EJECUCION") {
    return {
      title: "Cerrar entrega",
      description: "La historia ya fue aceptada y sólo resta la entrega operativa.",
      cta: "Entregar"
    };
  }

  return {
    title: "Estado final",
    description: "No hay una acción inmediata pendiente para este registro.",
    cta: "Volver al inicio"
  };
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

  return (
    <main>
      <section className="page-hero">
        <span className="pill pill-amber">Historia</span>
        <h1>Detalle de historia</h1>
        <p>Revisa el estado, mira el recorrido del flujo y ejecuta la siguiente acción disponible.</p>
      </section>

      <div className="page-grid">
        <div className="section-stack">
          <Card className="card--accent">
            <div className="section-heading">
              <h2>Resumen operativo</h2>
              <p>Vista compacta del estado actual y su posición en el flujo.</p>
            </div>
            <div className="metric-grid">
              <div className="metric">
                <div className="metric-label">Estado</div>
                <div className="metric-value">{historia.estado}</div>
              </div>
              <div className="metric">
                <div className="metric-label">Cliente</div>
                <div className="metric-value">{historia.clienteId}</div>
              </div>
              <div className="metric">
                <div className="metric-label">ID</div>
                <div className="metric-value" style={{ fontSize: "1rem" }}>
                  {historia.id}
                </div>
              </div>
            </div>
          </Card>

          <Card>
            <div className="section-heading">
              <h2>Progreso</h2>
              <p>El portal está organizado por etapas. La fase activa aparece resaltada.</p>
            </div>
            <div className="status-flow">
              {FLOW_STAGES.map((stage, index) => {
                const activo = index === pasoActual;
                const completado = index < pasoActual;
                return (
                  <div key={stage.title} className="status-step" data-active={activo ? "true" : "false"} data-complete={completado ? "true" : "false"}>
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
              <h2>Texto y trazabilidad</h2>
              <p>El texto original siempre queda separado del OCR para auditar el flujo.</p>
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

        <div className="section-stack">
          <Card className="card--accent">
            <div className="section-heading">
              <h2>Próximo paso</h2>
              <p>Esto te indica qué acción tiene sentido hacer ahora mismo.</p>
            </div>
            <div className="callout callout-info">
              <strong>{pasoSiguiente.title}</strong>
              <span>{pasoSiguiente.description}</span>
            </div>
            <div className="summary-list">
              <div className="summary-row">
                <span>Acción sugerida</span>
                <strong>{pasoSiguiente.cta}</strong>
              </div>
              <div className="summary-row">
                <span>Acceso rápido</span>
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
            <h2>Guía rápida</h2>
            <div className="summary-list">
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
                <strong>Solo líder</strong>
              </div>
              <div className="summary-row">
                <span>Aceptar</span>
                <strong>Solo cliente propietario</strong>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </main>
  );
}
