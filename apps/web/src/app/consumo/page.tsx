import { redirect } from "next/navigation";
import { appContext } from "../../server/app-context";
import { Card } from "../../components/ui/Card";
import { resolveIdentityFromCurrentSession } from "../../server/auth/resolve-identity";
import { DEMO_CLIENT_ID } from "../../server/demo";

export const dynamic = "force-dynamic";
export const revalidate = 0;

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
  const uso = lineaBase > 0 ? Math.max(0, Math.min(100, Math.round((consumido / lineaBase) * 100))) : 0;

  return (
    <main>
      <section className="page-hero">
        <span className="pill pill-blue">Consumo</span>
        <h1>Linea base mensual</h1>
        <p>La visualizacion del consumo resume cuanto queda disponible para el cliente activo en el periodo seleccionado.</p>
      </section>

      <div className="review-layout">
        <Card className="card--accent">
          <div className="section-heading">
            <h2>Resumen de puntos</h2>
            <p>Vista compacta del consumo actual para entender el margen disponible.</p>
          </div>

          <div className="review-summary-grid">
            <div className="review-metric">
              <div className="metric-label">Linea base</div>
              <div className="metric-value">{lineaBase}</div>
            </div>
            <div className="review-metric">
              <div className="metric-label">Consumido</div>
              <div className="metric-value">{consumido}</div>
            </div>
            <div className="review-metric">
              <div className="metric-label">Disponible</div>
              <div className="metric-value">{disponible}</div>
            </div>
          </div>

          <div className="signal-banner signal-banner--blue">
            <div className="signal-dot" />
            <div>
              <strong>{uso}% de uso</strong>
              <span>El consumo se descuenta solo cuando la historia se acepta.</span>
            </div>
          </div>
        </Card>

        <div className="review-side">
          <Card>
            <div className="section-heading">
              <h2>Contexto</h2>
              <p>Estos valores definen el periodo y el cliente que se esta mirando ahora.</p>
            </div>
            <div className="summary-list summary-list--tight">
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

          <Card className="card--accent">
            <div className="section-heading">
              <span className="pill pill-amber">Regla de negocio</span>
              <h2>Cuando impacta</h2>
              <p>El descuento de linea base ocurre solo cuando una historia se acepta.</p>
            </div>
            <div className="callout callout-warning">
              <strong>Impacto directo</strong>
              <span>Si la historia no fue aceptada, el consumo no cambia.</span>
            </div>
          </Card>
        </div>
      </div>
    </main>
  );
}
