import { redirect } from "next/navigation";
import Link from "next/link";
import { LoginForm } from "../../components/auth/LoginForm";
import { Card } from "../../components/ui/Card";
import { resolveIdentityFromCurrentSession } from "../../server/auth/resolve-identity";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function LoginPage() {
  const identity = await resolveIdentityFromCurrentSession().catch(() => null);

  if (identity) {
    redirect(identity.rol === "lider" ? "/lider" : "/historias/nueva");
  }

  return (
    <main>
      <section className="page-hero">
        <span className="pill pill-blue">Acceso</span>
        <h1>Ingresar</h1>
        <p>Usa el enlace por correo si quieres entrar con Supabase, o sigue en modo demo para probar el flujo sin sesion.</p>
      </section>

      <div className="review-layout">
        <Card className="card--accent">
          <LoginForm />
        </Card>

        <div className="review-side">
          <Card className="card--accent">
            <div className="section-heading">
              <span className="pill pill-amber">Modo demo</span>
              <h2>Entrada rapida</h2>
              <p>Abre el circuito de carga sin autenticacion real para validar la experiencia visual y el flujo base.</p>
            </div>
            <div className="signal-banner signal-banner--amber">
              <div className="signal-dot" />
              <div>
                <strong>Sin bloqueo de acceso</strong>
                <span>Ideal para revisar el portal antes de conectar la cuenta real.</span>
              </div>
            </div>
            <p style={{ marginTop: 12 }}>
              <Link href="/historias/nueva?demo=1">Entrar en modo demo</Link>
            </p>
          </Card>

          <Card>
            <div className="section-heading">
              <h2>Que veras despues</h2>
              <p>La entrada al portal lleva directo a las vistas que sostienen el flujo.</p>
            </div>
            <div className="summary-list summary-list--tight">
              <div className="summary-row">
                <span>Alta</span>
                <strong>Historia y evaluacion</strong>
              </div>
              <div className="summary-row">
                <span>Detalle</span>
                <strong>Sizing, validacion y entrega</strong>
              </div>
              <div className="summary-row">
                <span>Consumo</span>
                <strong>Linea base mensual</strong>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </main>
  );
}
