import { redirect } from "next/navigation";
import { appContext } from "../../server/app-context";
import { Card } from "../../components/ui/Card";
import { resolveIdentityFromCurrentSession } from "../../server/auth/resolve-identity";
import { DEMO_CLIENT_ID } from "../../server/demo";

function periodoActual() {
  return new Date().toISOString().slice(0, 7);
}

export default async function ConsumoPage() {
  const identity = await resolveIdentityFromCurrentSession().catch(() => null);

  if (!identity && process.env.NODE_ENV === "production") {
    redirect("/login");
  }

  const clienteId = identity?.clienteId ?? DEMO_CLIENT_ID;
  const periodo = periodoActual();
  const consumo = await appContext.consumo.obtener(clienteId, periodo);
  const lineaBase = consumo?.lineaBase ?? Number(process.env.DEMO_LINEA_BASE_PUNTOS ?? "100");
  const consumido = consumo?.consumido ?? 0;
  const disponible = lineaBase - consumido;

  return (
    <main>
      <section className="page-hero">
        <span className="pill pill-blue">Consumo</span>
        <h1>Linea base mensual</h1>
        <p>La visualizacion del consumo resume cuanto queda disponible para el cliente activo en el periodo seleccionado.</p>
      </section>
      <div className="page-grid">
        <Card>
          <div className="metric-grid">
            <div className="metric">
              <div className="metric-label">Linea base</div>
              <div className="metric-value">{lineaBase}</div>
            </div>
            <div className="metric">
              <div className="metric-label">Consumido</div>
              <div className="metric-value">{consumido}</div>
            </div>
            <div className="metric">
              <div className="metric-label">Disponible</div>
              <div className="metric-value">{disponible}</div>
            </div>
          </div>
        </Card>
        <div className="section-stack">
          <Card>
            <h2>Contexto</h2>
            <div className="summary-list">
              <div className="summary-row">
                <span>Cliente</span>
                <strong>{clienteId}</strong>
              </div>
              <div className="summary-row">
                <span>Periodo</span>
                <strong>{periodo}</strong>
              </div>
            </div>
          </Card>
          <Card>
            <div className="info-banner">
              El descuento de linea base ocurre solo cuando una historia se acepta.
            </div>
          </Card>
        </div>
      </div>
    </main>
  );
}
