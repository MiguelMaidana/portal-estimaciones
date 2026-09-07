import { redirect } from "next/navigation";
import { NuevaHistoriaForm } from "../../../components/historias/NuevaHistoriaForm";
import { resolveIdentityFromCurrentSession } from "../../../server/auth/resolve-identity";

export default async function NuevaHistoriaPage() {
  const identity = await resolveIdentityFromCurrentSession().catch(() => null);

  if (!identity && process.env.NODE_ENV === "production") {
    redirect("/login");
  }

  if (identity?.rol === "lider") {
    redirect("/lider");
  }

  const demoMode = !identity;
  const clienteId = identity?.clienteId ?? "demo-cliente";

  return (
    <main>
      <h1>Nueva historia</h1>
      <p>{demoMode ? "Modo demo activo." : "Sesion activa con Supabase."}</p>
      <NuevaHistoriaForm demoMode={demoMode} clienteId={clienteId} />
    </main>
  );
}
