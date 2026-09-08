import { redirect } from "next/navigation";
import { NuevaHistoriaForm } from "../../../components/historias/NuevaHistoriaForm";
import { resolveIdentityFromCurrentSession } from "../../../server/auth/resolve-identity";
import { DEMO_CLIENT_ID } from "../../../server/demo";

export const dynamic = "force-dynamic";
export const revalidate = 0;

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
  const clienteId = identity?.clienteId ?? DEMO_CLIENT_ID;

  return (
    <main>
      <section className="page-hero">
        <span className="pill pill-green">{demoMode ? "Demo" : "Sesion activa"}</span>
        <h1>Nueva historia</h1>
        <p>Redacta una historia, adjunta imagenes si hace falta y deja que el flujo la lleve a calidad, sizing y validacion.</p>
      </section>
      <NuevaHistoriaForm demoMode={demoMode} clienteId={clienteId} />
    </main>
  );
}
