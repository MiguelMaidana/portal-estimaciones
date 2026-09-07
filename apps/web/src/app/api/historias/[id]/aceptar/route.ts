import { appContext, resolveAppIdentity } from "../../../../../server/app-context";
import { errorResponse, json } from "../../../../../server/http/response";
import { aceptarSizing } from "../../../../../server/use-cases/aceptar-sizing";

function periodoActual() {
  return new Date().toISOString().slice(0, 7);
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const identity = await resolveAppIdentity(request);
    const { id } = await params;
    const body = await request.json().catch(() => ({}));

    await aceptarSizing(
      {
        historiaId: id,
        aceptado: Boolean(body.aceptado),
        periodo: typeof body.periodo === "string" && body.periodo ? body.periodo : periodoActual()
      },
      {
        identity,
        historias: appContext.historias,
        consumo: appContext.consumo,
        auditoria: appContext.auditoria,
        lineaBasePuntos: Number(process.env.DEMO_LINEA_BASE_PUNTOS ?? "100")
      }
    );

    const historia = await appContext.historias.obtenerPorId(id);
    return json(historia);
  } catch (error) {
    if (error instanceof Error && "status" in error) {
      return errorResponse(Number((error as { status: number }).status), error.message);
    }

    return errorResponse(500, error instanceof Error ? error.message : "Unexpected error");
  }
}
