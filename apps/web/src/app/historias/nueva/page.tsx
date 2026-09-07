import { redirect } from "next/navigation";
import { NuevaHistoriaForm } from "../../../components/historias/NuevaHistoriaForm";
import { Card } from "../../../components/ui/Card";
import { resolveIdentityFromCurrentSession } from "../../../server/auth/resolve-identity";

export default async function NuevaHistoriaPage({
  searchParams
}: {
  searchParams: Promise<{ demo?: string }>;
}) {
  const { demo } = await searchParams;
  const identity = await resolveIdentityFromCurrentSession().catch(() => null);
  const demoRequested = demo === "1";

  if (!identity && process.env.NODE_ENV === "production" && !demoRequested) {
    redirect("/login");
  }

  if (identity?.rol === "lider") {
    redirect("/lider");
  }

  const demoMode = demoRequested || !identity;
  const clienteId = identity?.clienteId ?? "demo-cliente";

  return (
    <main>
      <section className="page-hero">
        <span className="pill pill-green">{demoMode ? "Demo" : "Sesion activa"}</span>
        <h1>Nueva historia</h1>
        <p>Redacta una historia, adjunta imagenes si hace falta y deja que el flujo la lleve a calidad, sizing y validacion.</p>
      </section>
      <div className="page-grid">
        <Card>
          <NuevaHistoriaForm demoMode={demoMode} clienteId={clienteId} />
        </Card>
        <div className="section-stack">
          <Card>
            <h2>Reglas de la carga</h2>
            <div className="summary-list">
              <div className="summary-row">
                <span>Entrada</span>
                <strong>Una historia a la vez</strong>
              </div>
              <div className="summary-row">
                <span>OCR</span>
                <strong>Best effort con revision manual</strong>
              </div>
              <div className="summary-row">
                <span>Salida</span>
                <strong>Estado inicial del analisis</strong>
              </div>
            </div>
          </Card>
          <Card>
            <h2>Estados clave</h2>
            <div className="summary-list">
              <div className="summary-row">
                <span>Calidad</span>
                <strong>Completa o incompleta</strong>
              </div>
              <div className="summary-row">
                <span>Sizing</span>
                <strong>Solo si la historia está completa</strong>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </main>
  );
}
