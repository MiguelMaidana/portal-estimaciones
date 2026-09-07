import { appContext, resolveAppIdentity } from "../../../../../server/app-context";
import { forbidden, notFound } from "../../../../../server/http/errors";
import { errorResponse, json } from "../../../../../server/http/response";

function periodoActual() {
  return new Date().toISOString().slice(0, 7);
}

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const identity = await resolveAppIdentity(request);
    const { id } = await params;

    if (identity.rol !== "lider" && identity.clienteId !== id) {
      throw forbidden("No autorizado para ver consumo");
    }

    const periodo = new URL(request.url).searchParams.get("periodo") ?? periodoActual();
    const consumo = await appContext.consumo.obtener(id, periodo);

    if (!consumo) {
      throw notFound("Consumo no encontrado para el periodo solicitado");
    }

    return json({
      lineaBase: consumo.lineaBase,
      consumido: consumo.consumido,
      disponible: consumo.lineaBase - consumo.consumido,
      historias: []
    });
  } catch (error) {
    if (error instanceof Error && "status" in error) {
      return errorResponse(Number((error as { status: number }).status), error.message);
    }

    return errorResponse(500, error instanceof Error ? error.message : "Unexpected error");
  }
}
