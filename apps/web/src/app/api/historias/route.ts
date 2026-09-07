import { crearHistoria } from "../../../server/use-cases/crear-historia";
import { appContext, resolveAppIdentity } from "../../../server/app-context";
import { errorResponse, json } from "../../../server/http/response";
import { invalid } from "../../../server/http/errors";
import { parseMultipartFormData } from "../../../server/http/parse-form-data";

export async function POST(request: Request) {
  try {
    const identity = await resolveAppIdentity(request);
    const body = await parseMultipartFormData(request);

    if (!body.clienteId || !body.textoOriginal) {
      throw invalid("clienteId y textoOriginal son requeridos");
    }

    const historia = await crearHistoria(
      {
        clienteId: body.clienteId,
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

    return json(historia, { status: 201 });
  } catch (error) {
    if (error instanceof Error && "status" in error) {
      const status = Number((error as { status: number }).status);
      return errorResponse(status, error.message);
    }

    return errorResponse(500, error instanceof Error ? error.message : "Unexpected error");
  }
}
