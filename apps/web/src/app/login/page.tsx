import { redirect } from "next/navigation";
import Link from "next/link";
import { LoginForm } from "../../components/auth/LoginForm";
import { Card } from "../../components/ui/Card";
import { resolveIdentityFromCurrentSession } from "../../server/auth/resolve-identity";

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
        <p>Usa el enlace por correo si quieres entrar con Supabase, o sigue en modo demo para probar el flujo sin sesión.</p>
      </section>
      <div className="split-grid">
        <Card>
          <LoginForm />
        </Card>
        <div className="section-stack">
          <Card>
            <h2>Modo demo</h2>
            <p>Abre el circuito de carga sin autenticacion real para validar la experiencia visual y el flujo base.</p>
            <p>
              <Link href="/historias/nueva?demo=1">Entrar en modo demo</Link>
            </p>
          </Card>
          <Card>
            <h2>Que veras despues</h2>
            <div className="summary-list">
              <div className="summary-row">
                <span>Alta</span>
                <strong>Historia, OCR y adjuntos</strong>
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
