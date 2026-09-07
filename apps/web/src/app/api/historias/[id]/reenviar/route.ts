import { appContext, resolveAppIdentity } from "../../../../../server/app-context";
import { errorResponse, json } from "../../../../../server/http/response";
import { parseMultipartFormData } from "../../../../../server/http/parse-form-data";
import { reenviarHistoria } from "../../../../../server/use-cases/reenviar-historia";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const identity = await resolveAppIdentity(request);
    const { id } = await params;
    const body = await parseMultipartFormData(request);

    const historia = await reenviarHistoria(
      {
        historiaId: id,
        textoOriginal: body.textoOriginal,
        textoOcr: body.textoOcr,
        contieneContenidoOcr: body.contieneContenidoOcr
      },
      {
        identity,
        historias: appContext.historias,
        calidad: appContext.calidad,
        auditoria: appContext.auditoria
      }
    );

    return json(historia);
  } catch (error) {
    if (error instanceof Error && "status" in error) {
      return errorResponse(Number((error as { status: number }).status), error.message);
    }

    return errorResponse(500, error instanceof Error ? error.message : "Unexpected error");
  }
}
