import { appContext, resolveAppIdentity } from "../../../../../server/app-context";
import { errorResponse, json } from "../../../../../server/http/response";
import { revisarOcr } from "../../../../../server/use-cases/revisar-ocr";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const identity = await resolveAppIdentity(request);
    const { id } = await params;
    const body = await request.json().catch(() => ({}));

    await revisarOcr(
      {
        historiaId: id,
        aprobado: Boolean(body.aprobado)
      },
      {
        identity,
        historias: appContext.historias,
        auditoria: appContext.auditoria
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
