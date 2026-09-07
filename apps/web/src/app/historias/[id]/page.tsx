import { notFound } from "next/navigation";
import { HistoriaActions } from "../../../components/historias/HistoriaActions";
import { resolveIdentityFromCurrentSession } from "../../../server/auth/resolve-identity";
import { appContext } from "../../../server/app-context";

export default async function HistoriaDetallePage({
  params
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const identity = await resolveIdentityFromCurrentSession().catch(() => null);
  const historia = await appContext.historias.obtenerPorId(id);

  if (!historia) {
    notFound();
  }

  if (!identity && process.env.NODE_ENV === "production") {
    notFound();
  }

  const puedeVer =
    !identity || identity.rol === "lider" || identity.clienteId === historia.clienteId;

  if (!puedeVer) {
    notFound();
  }

  return (
    <main>
      <h1>Detalle de historia</h1>
      <p>ID: {historia.id}</p>
      <p>Estado: {historia.estado}</p>
      <p>Cliente: {historia.clienteId}</p>
      <p>Texto original: {historia.textoOriginal}</p>
      {historia.textoOcr ? <p>Texto OCR: {historia.textoOcr}</p> : null}
      <HistoriaActions historiaId={historia.id} estado={historia.estado} demoMode={!identity} />
    </main>
  );
}
