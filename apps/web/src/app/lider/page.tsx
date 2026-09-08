import Link from "next/link";
import { Card } from "../../components/ui/Card";
import { resolveIdentityFromCurrentSession } from "../../server/auth/resolve-identity";
import { appContext } from "../../server/app-context";

export const dynamic = "force-dynamic";
export const revalidate = 0;

type HistoriaEstado = Awaited<ReturnType<typeof appContext.historias.listar>>[number]["estado"];

function etiquetaEstado(estado: HistoriaEstado) {
  if (estado === "PENDIENTE_VALIDACION_LIDER") return "pill pill-amber";
  if (estado === "ACEPTADA" || estado === "ENTREGADA" || estado === "SIZING_VALIDADO") return "pill pill-green";
  return "pill pill-blue";
}

function ordenEstado(estado: HistoriaEstado) {
  const orden: Record<HistoriaEstado, number> = {
    BORRADOR: 1,
    EN_ANALISIS_COMPLETITUD: 2,
    INCOMPLETA: 3,
    COMPLETA: 4,
    EN_SIZING: 5,
    SIZING_CALCULADO: 6,
    PENDIENTE_VALIDACION_LIDER: 0,
    SIZING_VALIDADO: 7,
    PENDIENTE_ACEPTACION_CLIENTE: 8,
    RECHAZADA_POR_CLIENTE: 9,
    ACEPTADA: 10,
    EN_EJECUCION: 11,
    ENTREGADA: 12,
    PENDIENTE_REVISION_OCR: 2.5
  };

  return orden[estado];
}

function formatState(estado: HistoriaEstado) {
  if (estado === "PENDIENTE_VALIDACION_LIDER") return "Listo para revisar";
  if (estado === "SIZING_VALIDADO") return "Validado";
  if (estado === "COMPLETA") return "Listo para sizing";
  if (estado === "EN_SIZING") return "Calculando sizing";
  return estado;
}

function semaforoLider(pendientes: number, completas: number, aceptadas: number) {
  if (pendientes > 0) {
    return {
      tone: "amber",
      titulo: "Hay historias listas para revisar",
      descripcion: "La cola ya tiene items que pueden pasar por validacion humana."
    };
  }

  if (completas > 0 || aceptadas > 0) {
    return {
      tone: "blue",
      titulo: "Flujo activo sin cola urgente",
      descripcion: "Todavia hay trabajo, pero no hay historias esperando revision inmediata."
    };
  }

  return {
    tone: "green",
    titulo: "Panel limpio",
    descripcion: "No hay pendientes y el flujo esta estable."
  };
}

export default async function LiderPage() {
  const identity = await resolveIdentityFromCurrentSession().catch(() => null);

  if (identity?.rol === "cliente") {
    return (
      <main>
        <section className="page-hero">
          <span className="pill pill-blue">Acceso</span>
          <h1>Panel del lider</h1>
          <p>Esta vista esta reservada para lideres. Tu sesion corresponde a un cliente, por eso redirigimos el foco a la carga de historias.</p>
        </section>
        <Card>
          <p>
            <Link href="/historias/nueva">Ir a nueva historia</Link>
          </p>
        </Card>
      </main>
    );
  }

  const historias = await appContext.historias.listar();
  const pendientes = historias
    .filter((historia) => historia.estado === "PENDIENTE_VALIDACION_LIDER")
    .sort((a, b) => ordenEstado(a.estado) - ordenEstado(b.estado));
  const listaOrdenada = [...historias].sort((a, b) => ordenEstado(a.estado) - ordenEstado(b.estado));
  const demoMode = !identity;

  const total = historias.length;
  const listas = {
    pendientes: pendientes.length,
    completas: historias.filter((historia) => historia.estado === "COMPLETA").length,
    aceptadas: historias.filter((historia) => historia.estado === "ACEPTADA").length
  };

  const semaforo = semaforoLider(listas.pendientes, listas.completas, listas.aceptadas);

  return (
    <main>
      <section className="page-hero">
        <span className="pill pill-amber">{demoMode ? "Demo" : "Lider"}</span>
        <h1>Panel del lider</h1>
        <p>Revisa sizing, aprueba o corrige y controla la cola antes de publicar al cliente.</p>
      </section>

      <div className="review-layout">
        <div className="review-main">
          <Card className="card--accent">
            <div className="section-heading">
              <h2>Resumen operativo</h2>
              <p>Vista compacta del panel con los indicadores que importan para decidir el siguiente paso.</p>
            </div>

            <div className="review-summary-grid">
              <div className="review-metric">
                <div className="metric-label">Historias</div>
                <div className="metric-value">{total}</div>
              </div>
              <div className="review-metric">
                <div className="metric-label">Pendientes de validacion</div>
                <div className="metric-value">{listas.pendientes}</div>
              </div>
              <div className="review-metric">
                <div className="metric-label">Aceptadas</div>
                <div className="metric-value">{listas.aceptadas}</div>
              </div>
            </div>

            <div className={`signal-banner signal-banner--${semaforo.tone}`}>
              <div className="signal-dot" />
              <div>
                <strong>{semaforo.titulo}</strong>
                <span>{semaforo.descripcion}</span>
              </div>
            </div>
          </Card>

          <Card className="card--accent">
            <div className="section-heading">
              <h2>Cola de validacion</h2>
              <p>Las historias que llegan aqui ya deberian tener calidad suficiente para que el lider solo decida.</p>
            </div>
            {pendientes.length ? (
              <div className="queue-list">
                {pendientes.map((historia, index) => (
                  <article key={historia.id} className="queue-item">
                    <div className="queue-index">{String(index + 1).padStart(2, "0")}</div>
                    <div className="queue-content">
                      <div className="queue-title">
                        <strong>{historia.id}</strong>
                        <span className={etiquetaEstado(historia.estado)}>{formatState(historia.estado)}</span>
                      </div>
                      <p>{historia.clienteId}</p>
                    </div>
                    <div className="queue-action">
                      <Link href={`/historias/${historia.id}${demoMode ? "?demo=1" : ""}`}>Abrir detalle</Link>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="empty-state empty-state--focus">
                <strong>No hay historias pendientes de validacion</strong>
                <span>Cuando una historia llegue a PENDIENTE_VALIDACION_LIDER aparecera aqui para revision.</span>
              </div>
            )}
          </Card>

          <Card>
            <div className="section-heading">
              <h2>Historial</h2>
              <p>Vista compacta del flujo completo, ordenada por etapa.</p>
            </div>
            {listaOrdenada.length ? (
              <div className="history-list">
                {listaOrdenada.map((historia) => (
                  <div key={historia.id} className="history-item">
                    <div>
                      <strong>{historia.id}</strong>
                      <p>{historia.clienteId}</p>
                    </div>
                    <div className="history-meta">
                      <span className={etiquetaEstado(historia.estado)}>{formatState(historia.estado)}</span>
                      <span className="pill pill-blue">{historia.sizingCalculado ? `Sizing ${historia.sizingCalculado}` : "Sin sizing"}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <strong>Aun no hay historias cargadas</strong>
                <span>Cuando uses el formulario de nueva historia, esta lista comenzara a llenarse.</span>
              </div>
            )}
          </Card>
        </div>

        <aside className="review-side">
          <Card className="card--accent">
            <div className="section-heading">
              <h2>Checklist y dictamen</h2>
              <p>Resumen operativo del panel para decidir rapido si algo sigue o vuelve atras.</p>
            </div>
            <div className="signal-grid signal-grid--compact">
              <div className="signal-card">
                <span>Calidad</span>
                <strong>{listas.completas > 0 ? "Hay historias listas" : "Sin historias listas"}</strong>
                <p>La cola solo deberia recibir historias que ya pasaron calidad.</p>
              </div>
              <div className="signal-card">
                <span>Estado activo</span>
                <strong>{demoMode ? "Demo local" : identity?.userId ?? "Sin sesion"}</strong>
                <p>El contexto actual define quien puede aprobar y validar.</p>
              </div>
              <div className="signal-card">
                <span>Cola</span>
                <strong>{pendientes.length ? "Con trabajo pendiente" : "Sin pendientes"}</strong>
                <p>Si aparece trabajo, entra por esta cola antes de publicar al cliente.</p>
              </div>
              <div className="signal-card signal-card--amber">
                <span>Dictamen</span>
                <strong>{pendientes.length ? "Hay revision pendiente" : "No hay acciones urgentes"}</strong>
                <p>{pendientes.length ? "Conviene revisar la cola antes de mover historias hacia el cliente." : "El panel esta estable y sin bloqueos."}</p>
              </div>
            </div>
          </Card>

          <Card>
            <div className="section-heading">
              <h2>Guia rapida</h2>
              <p>El lider solo entra cuando la historia ya tiene forma tecnica suficiente.</p>
            </div>
            <div className="flow-mini">
              <div className="flow-mini-step">
                <span>01</span>
                <div>
                  <strong>Revisar cola</strong>
                  <p>Prioriza lo que esta en PENDIENTE_VALIDACION_LIDER.</p>
                </div>
              </div>
              <div className="flow-mini-step">
                <span>02</span>
                <div>
                  <strong>Validar sizing</strong>
                  <p>Si hace falta, corrige antes de publicar al cliente.</p>
                </div>
              </div>
              <div className="flow-mini-step">
                <span>03</span>
                <div>
                  <strong>Seguir el flujo</strong>
                  <p>La historia avanza hacia aceptacion, ejecucion y entrega.</p>
                </div>
              </div>
            </div>
          </Card>
        </aside>
      </div>
    </main>
  );
}
