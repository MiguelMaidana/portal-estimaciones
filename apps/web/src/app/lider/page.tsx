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
  if (estado === "PENDIENTE_VALIDACION_LIDER") {
    return "Listo para revisar";
  }

  if (estado === "SIZING_VALIDADO") {
    return "Validado";
  }

  if (estado === "COMPLETA") {
    return "Listo para sizing";
  }

  return estado;
}

export default async function LiderPage() {
  const identity = await resolveIdentityFromCurrentSession().catch(() => null);

  if (identity?.rol === "cliente") {
    return (
      <main>
        <section className="page-hero">
          <span className="pill pill-blue">Acceso</span>
          <h1>Panel del lider</h1>
          <p>Esta vista está reservada para líderes. Tu sesión corresponde a un cliente, por eso redirigimos el foco a la carga de historias.</p>
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

  return (
    <main>
      <section className="page-hero">
        <span className="pill pill-amber">{demoMode ? "Demo" : "Líder"}</span>
        <h1>Panel del líder</h1>
        <p>Revisa sizing, aprueba o corrige y controla la cola antes de publicar al cliente.</p>
      </section>

      <div className="leader-layout">
        <div className="leader-main">
          <div className="metric-grid" style={{ marginBottom: 20 }}>
            <Card className="metric-card">
              <div className="metric-label">Historias</div>
              <div className="metric-value">{total}</div>
            </Card>
            <Card className="metric-card">
              <div className="metric-label">Pendientes de validación</div>
              <div className="metric-value">{listas.pendientes}</div>
            </Card>
            <Card className="metric-card">
              <div className="metric-label">Aceptadas</div>
              <div className="metric-value">{listas.aceptadas}</div>
            </Card>
          </div>

          <Card className="card--accent">
            <div className="section-heading">
              <h2>Cola de validación</h2>
              <p>La cola funciona como checklist de revisión. Aquí deben aparecer solo historias listas para la decisión del líder.</p>
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
                <strong>No hay historias pendientes de validación</strong>
                <span>Cuando una historia llegue a PENDIENTE_VALIDACION_LIDER aparecerá aquí para su revisión.</span>
              </div>
            )}
          </Card>
        </div>

        <aside className="leader-side">
          <Card className="card--accent">
            <div className="section-heading">
              <h2>Checklist y dictamen</h2>
              <p>Resumen operativo del panel para decidir rápido si algo sigue o vuelve atrás.</p>
            </div>
            <div className="checklist">
              <div className="check-item">
                <span>Calidad</span>
                <strong>{listas.completas > 0 ? "Hay historias listas" : "Sin historias listas"}</strong>
              </div>
              <div className="check-item">
                <span>Estado activo</span>
                <strong>{demoMode ? "Demo local" : identity?.userId ?? "Sin sesión"}</strong>
              </div>
              <div className="check-item">
                <span>Cola</span>
                <strong>{pendientes.length ? "Con trabajo pendiente" : "Sin pendientes"}</strong>
              </div>
            </div>
            <div className="callout callout-warning">
              <strong>Dictamen</strong>
              <span>{pendientes.length ? "Hay revisión pendiente." : "No hay acciones urgentes."}</span>
            </div>
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
                    <span className={etiquetaEstado(historia.estado)}>{formatState(historia.estado)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <strong>Aún no hay historias cargadas</strong>
                <span>Cuando uses el formulario de nueva historia, esta lista comenzará a llenarse.</span>
              </div>
            )}
          </Card>
        </aside>
      </div>
    </main>
  );
}
