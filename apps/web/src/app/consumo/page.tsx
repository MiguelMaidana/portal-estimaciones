import { redirect } from "next/navigation";
import { appContext } from "../../server/app-context";
import { resolveIdentityFromCurrentSession } from "../../server/auth/resolve-identity";

function periodoActual() {
  return new Date().toISOString().slice(0, 7);
}

export default async function ConsumoPage() {
  const identity = await resolveIdentityFromCurrentSession().catch(() => null);

  if (!identity && process.env.NODE_ENV === "production") {
    redirect("/login");
  }

  const clienteId = identity?.clienteId ?? "demo-cliente";
  const periodo = periodoActual();
  const consumo = await appContext.consumo.obtener(clienteId, periodo);
  const lineaBase = consumo?.lineaBase ?? Number(process.env.DEMO_LINEA_BASE_PUNTOS ?? "100");
  const consumido = consumo?.consumido ?? 0;
  const disponible = lineaBase - consumido;

  return (
    <main>
      <h1>Consumo</h1>
      <p>Cliente: {clienteId}</p>
      <p>Periodo: {periodo}</p>
      <p>Linea base: {lineaBase}</p>
      <p>Consumido: {consumido}</p>
      <p>Disponible: {disponible}</p>
    </main>
  );
}
