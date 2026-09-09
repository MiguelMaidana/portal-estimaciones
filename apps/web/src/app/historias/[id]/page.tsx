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
};

const FLOW_STAGES: FlowStage[] = [
  { title: "Carga", states: ["BORRADOR", "EN_ANALISIS_COMPLETITUD", "INCOMPLETA"] },
  { title: "Calidad", states: ["COMPLETA"] },
  { title: "Sizing", states: ["EN_SIZING", "SIZING_CALCULADO"] },
  { title: "Lider", states: ["PENDIENTE_VALIDACION_LIDER", "SIZING_VALIDADO"] },
  {
    title: "Cliente",
    states: ["PENDIENTE_ACEPTACION_CLIENTE", "RECHAZADA_POR_CLIENTE", "ACEPTADA", "EN_EJECUCION", "ENTREGADA"]
  }
];

function stageIndex(estado: HistoriaEstado) {
  const index = FLOW_STAGES.findIndex((stage) => stage.states.includes(estado));
  return index < 0 ? 0 : index;
}

function estadoLegible(estado: HistoriaEstado) {
  const labels: Partial<Record<HistoriaEstado, string>> = {
    BORRADOR: "Borrador",
    EN_ANALISIS_COMPLETITUD: "Analizando calidad",
    INCOMPLETA: "Requiere ajustes",
    COMPLETA: "Calidad aprobada",
    EN_SIZING: "Calculando sizing",
    SIZING_CALCULADO: "Sizing calculado",
    PENDIENTE_VALIDACION_LIDER: "Revision del lider",
    SIZING_VALIDADO: "Sizing validado",
    PENDIENTE_ACEPTACION_CLIENTE: "Esperando al cliente",
    RECHAZADA_POR_CLIENTE: "Rechazada por cliente",
    ACEPTADA: "Aceptada",
    EN_EJECUCION: "En ejecucion",
    ENTREGADA: "Entregada"
  };

  return labels[estado] ?? estado;
}

function estadoVisual(estado: HistoriaEstado) {
  if (["BORRADOR", "EN_ANALISIS_COMPLETITUD", "INCOMPLETA"].includes(estado)) {
    return {
      tone: "rojo",
      title: "La historia necesita trabajo",
      description: "Todavia no supero el control de calidad y el sizing sigue bloqueado."
    };
  }

  if (estado === "COMPLETA" || estado === "EN_SIZING") {
    return {
      tone: "amber",
      title: "Calidad aprobada",
      description: "La historia ya puede pasar al calculo deterministico de sizing."
    };
  }

  if (["SIZING_CALCULADO", "PENDIENTE_VALIDACION_LIDER", "SIZING_VALIDADO"].includes(estado)) {
    return {
      tone: "blue",
      title: "Estimacion calculada",
      description: "El resultado existe y esta en la instancia de revision humana."
    };
  }

  return {
    tone: "green",
    title: "Estimacion encaminada",
    description: "La etapa tecnica termino y la historia avanza hacia aceptacion o entrega."
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

  if (!historia) notFound();
  if (!identity && process.env.NODE_ENV === "production" && !demoRequested) notFound();

  const puedeVer = demoRequested || !identity || identity.rol === "lider" || identity.clienteId === historia.clienteId;
  if (!puedeVer) notFound();

  const currentStage = stageIndex(historia.estado);
  const visual = estadoVisual(historia.estado);
  const calidad =
    historia.resultadoCompletitud === "completa"
      ? "Apta"
      : historia.resultadoCompletitud === "incompleta"
        ? "Con observaciones"
        : "En analisis";

  return (
    <main>
      <section className="page-hero detail-hero">
        <div>
          <span className="pill pill-amber">Evaluacion</span>
          <h1>Resultado de la historia</h1>
          <p>Calidad, sizing y proxima decision en una sola vista.</p>
        </div>
        <span className={`pill ${visual.tone === "green" ? "pill-green" : visual.tone === "amber" ? "pill-amber" : "pill-blue"}`}>
          {estadoLegible(historia.estado)}
        </span>
      </section>

      <Card className="card--accent result-overview">
        <div className={`result-verdict result-verdict--${visual.tone}`}>
          <span className="result-kicker">Evaluador de calidad</span>
          <h2>{visual.title}</h2>
          <p>{historia.feedbackCompletitud || visual.description}</p>
        </div>
        <div className="result-stat">
          <span>Calidad</span>
          <strong>{calidad}</strong>
          <small>{historia.resultadoCompletitud ? "Analisis finalizado" : "Todavia sin dictamen"}</small>
        </div>
        <div className="result-stat result-stat--sizing">
          <span>Sizing</span>
          <strong>{historia.sizingCalculado ?? "-"}</strong>
          <small>{historia.sizingCalculado ? `${historia.puntosCalculados ?? 0} puntos calculados` : "Bloqueado hasta aprobar calidad"}</small>
        </div>
      </Card>

      <div className="detail-layout">
        <div className="detail-main">
          <Card>
            <div className="section-heading">
              <span className="pill pill-blue">Historia de usuario</span>
              <h2>Contenido evaluado</h2>
            </div>
            <div className="story-content">
              <p>{historia.textoOriginal}</p>
            </div>

            {historia.sugerenciasMejora?.length ? (
              <div className="improvement-block">
                <strong>Que conviene mejorar</strong>
                <div className="improvement-list">
                  {historia.sugerenciasMejora.map((sugerencia) => (
                    <div key={sugerencia} className="improvement-item">
                      <span>!</span>
                      <p>{sugerencia}</p>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </Card>

          {historia.criteriosExtraidos ? (
            <Card>
              <div className="section-heading">
                <span className="pill pill-green">Base del calculo</span>
                <h2>Criterios extraidos</h2>
                <p>Estos datos alimentan el motor deterministico; la IA no decide el tamano final.</p>
              </div>
              <div className="criteria-grid">
                <div className="signal-card">
                  <span>Complejidad tecnica</span>
                  <strong>{historia.criteriosExtraidos.complejidad_tecnica}</strong>
                </div>
                <div className="signal-card">
                  <span>Integraciones</span>
                  <strong>{historia.criteriosExtraidos.integraciones_detectadas.length}</strong>
                </div>
                <div className="signal-card">
                  <span>Dependencias</span>
                  <strong>{historia.criteriosExtraidos.dependencias_externas.length}</strong>
                </div>
                <div className="signal-card">
                  <span>Criterios de aceptacion</span>
                  <strong>{historia.criteriosExtraidos.cantidad_criterios_aceptacion_estimados}</strong>
                </div>
              </div>
            </Card>
          ) : null}

          <Card>
            <div className="section-heading section-heading--row">
              <div>
                <h2>Recorrido</h2>
                <p>La etapa activa esta resaltada.</p>
              </div>
              <span className="pill pill-blue">{FLOW_STAGES[currentStage].title}</span>
            </div>
            <div className="status-track">
              {FLOW_STAGES.map((stage, index) => (
                <div key={stage.title} className="status-track-item" data-active={index === currentStage ? "true" : "false"} data-complete={index < currentStage ? "true" : "false"}>
                  <span>{index < currentStage ? "OK" : String(index + 1).padStart(2, "0")}</span>
                  <strong>{stage.title}</strong>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <aside className="detail-side">
          <Card className="card--accent detail-actions-card">
            <HistoriaActions historiaId={historia.id} estado={historia.estado} demoMode={demoRequested || !identity} />
          </Card>

          <Card className="record-meta">
            <div className="section-heading">
              <h2>Datos del registro</h2>
            </div>
            <dl>
              <div>
                <dt>Cliente</dt>
                <dd>{historia.clienteId}</dd>
              </div>
              <div>
                <dt>Identificador</dt>
                <dd>{historia.id}</dd>
              </div>
            </dl>
          </Card>
        </aside>
      </div>
    </main>
  );
}
