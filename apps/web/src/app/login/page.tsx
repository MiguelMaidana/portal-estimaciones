import { redirect } from "next/navigation";
import Link from "next/link";
import { LoginForm } from "../../components/auth/LoginForm";
import { resolveIdentityFromCurrentSession } from "../../server/auth/resolve-identity";

export default async function LoginPage() {
  const identity = await resolveIdentityFromCurrentSession().catch(() => null);

  if (identity) {
    redirect(identity.rol === "lider" ? "/lider" : "/historias/nueva");
  }

  return (
    <main>
      <h1>Ingresar</h1>
      <p>Recibí un enlace por correo para ingresar al portal.</p>
      <LoginForm />
      <p>
        <Link href="/historias/nueva">Entrar en modo demo</Link>
      </p>
    </main>
  );
}
