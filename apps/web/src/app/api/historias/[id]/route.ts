import { appContext, resolveAppIdentity } from "../../../../server/app-context";
import { forbidden, notFound } from "../../../../server/http/errors";
import { errorResponse, json } from "../../../../server/http/response";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const identity = await resolveAppIdentity(request);
    const { id } = await params;
    const historia = await appContext.historias.obtenerPorId(id);

    if (!historia) {
      throw notFound("Historia no encontrada");
    }

    if (identity.rol !== "lider" && identity.clienteId !== historia.clienteId) {
      throw forbidden("No autorizado para ver la historia");
    }

    return json(historia);
  } catch (error) {
    if (error instanceof Error && "status" in error) {
      return errorResponse(Number((error as { status: number }).status), error.message);
    }

    return errorResponse(500, error instanceof Error ? error.message : "Unexpected error");
  }
}
