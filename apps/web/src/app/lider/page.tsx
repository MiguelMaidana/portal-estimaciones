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

export default async function LiderPage() {
  const identity = await resolveIdentityFromCurrentSession().catch(() => null);

  if (identity?.rol === "cliente") {
    return (
      <main>
        <section className="page-hero">
          <span className="pill pill-blue">Acceso</span>
          <h1>Panel del lider</h1>
          <p>Esta vista está reservada para lideres. Tu sesión corresponde a un cliente, por eso redirigimos el foco a la carga de historias.</p>
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
        <span className="pill pill-amber">{demoMode ? "Demo" : "Lider"}</span>
        <h1>Panel del lider</h1>
        <p>Valida sizing, corrige cuando haga falta y sigue de cerca el flujo de historias antes de la aceptacion del cliente.</p>
      </section>

      <div className="metric-grid" style={{ marginBottom: 20 }}>
        <Card>
          <div className="metric-label">Historias</div>
          <div className="metric-value">{total}</div>
        </Card>
        <Card>
          <div className="metric-label">Pendientes de validacion</div>
          <div className="metric-value">{listas.pendientes}</div>
        </Card>
        <Card>
          <div className="metric-label">Aceptadas</div>
          <div className="metric-value">{listas.aceptadas}</div>
        </Card>
      </div>

      <div className="page-grid">
        <Card>
          <h2>Cola de validacion</h2>
          {pendientes.length ? (
            <div className="summary-list">
              {pendientes.map((historia) => (
                <div key={historia.id} className="summary-row">
                  <span>
                    <strong>{historia.id}</strong>
                    <br />
                    {historia.clienteId}
                  </span>
                  <strong>
                    <span className={etiquetaEstado(historia.estado)}>{historia.estado}</span>
                    <br />
                    <Link href={`/historias/${historia.id}${demoMode ? "?demo=1" : ""}`}>Abrir detalle</Link>
                  </strong>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <strong>No hay historias pendientes de validacion</strong>
              <span>Cuando una historia llegue a PENDIENTE_VALIDACION_LIDER aparecera aqui para su revision.</span>
            </div>
          )}
        </Card>

        <div className="section-stack">
          <Card>
            <h2>Resumen operativo</h2>
            <div className="summary-list">
              <div className="summary-row">
                <span>Completas</span>
                <strong>{listas.completas}</strong>
              </div>
              <div className="summary-row">
                <span>Estado activo</span>
                <strong>{demoMode ? "Demo local" : identity?.userId ?? "Sin sesion"}</strong>
              </div>
            </div>
          </Card>
          <Card>
            <h2>Historial</h2>
            {listaOrdenada.length ? (
              <div className="summary-list">
                {listaOrdenada.map((historia) => (
                  <div key={historia.id} className="summary-row">
                    <span>
                      {historia.id}
                      <br />
                      {historia.clienteId}
                    </span>
                    <strong>
                      <span className={etiquetaEstado(historia.estado)}>{historia.estado}</span>
                    </strong>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <strong>Aun no hay historias cargadas</strong>
                <span>Cuando uses el formulario de nueva historia, esta cola comenzara a llenarse.</span>
              </div>
            )}
          </Card>
        </div>
      </div>
    </main>
  );
}
