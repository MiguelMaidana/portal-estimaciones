import { transicionarEstado } from "../domain/transitions";
import { conflict, forbidden, notFound } from "../http/errors";
import type { HistoriaRepository, RepositorioAuditoria, SessionIdentity } from "./contracts";

export interface RevisarOcrInput {
  historiaId: string;
  aprobado: boolean;
}

export interface RevisarOcrDeps {
  identity: SessionIdentity;
  historias: HistoriaRepository;
  auditoria: RepositorioAuditoria;
}

export async function revisarOcr(input: RevisarOcrInput, deps: RevisarOcrDeps): Promise<void> {
  const historia = await deps.historias.obtenerPorId(input.historiaId);
  if (!historia) {
    throw notFound("Historia no encontrada");
  }

  if (deps.identity.rol !== "lider") {
    throw forbidden("Solo lider puede revisar OCR");
  }

  if (historia.estado !== "PENDIENTE_REVISION_OCR") {
    throw conflict("La historia no esta pendiente de revision OCR");
  }

  const siguienteEstado = input.aprobado
    ? transicionarEstado(historia.estado, "OCR_APROBADO")
    : transicionarEstado(historia.estado, "OCR_RECHAZADO");

  await deps.auditoria.registrar({
    historiaId: historia.id,
    evento: input.aprobado ? "ocr_aprobado" : "ocr_rechazado",
    actor: deps.identity.userId,
    detalle: { estadoAnterior: historia.estado, estadoPosterior: siguienteEstado }
  });

  await deps.historias.actualizar(historia.id, {
    estado: siguienteEstado
  });
}
