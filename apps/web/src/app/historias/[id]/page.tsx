import { notFound } from "next/navigation";
import { HistoriaActions } from "../../../components/historias/HistoriaActions";
import { Card } from "../../../components/ui/Card";
import { resolveIdentityFromCurrentSession } from "../../../server/auth/resolve-identity";
import { appContext } from "../../../server/app-context";

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

  return (
    <main>
      <section className="page-hero">
        <span className="pill pill-amber">Historia</span>
        <h1>Detalle de historia</h1>
        <p>Revisa el estado actual, el texto original y las acciones permitidas para el rol activo.</p>
      </section>
      <div className="page-grid">
        <Card>
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
          <div className="summary-list" style={{ marginTop: 16 }}>
            <div className="summary-row">
              <span>Texto original</span>
              <strong>{historia.textoOriginal}</strong>
            </div>
            {historia.textoOcr ? (
              <div className="summary-row">
                <span>Texto OCR</span>
                <strong>{historia.textoOcr}</strong>
              </div>
            ) : null}
          </div>
        </Card>
        <div className="section-stack">
          <Card>
            <HistoriaActions historiaId={historia.id} estado={historia.estado} demoMode={demoRequested || !identity} />
          </Card>
          <Card>
            <h2>Guia rapida</h2>
            <div className="summary-list">
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
        </div>
      </div>
    </main>
  );
}
