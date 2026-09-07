import { transicionarEstado } from "../domain/transitions";
import { conflict, forbidden, notFound } from "../http/errors";
import type { CalidadPort, HistoriaRecord, HistoriaRepository, RepositorioAuditoria, SessionIdentity } from "./contracts";

export interface ReenviarHistoriaInput {
  historiaId: string;
  textoOriginal: string;
  textoOcr?: string | null;
  contieneContenidoOcr?: boolean;
}

export interface ReenviarHistoriaDeps {
  identity: SessionIdentity;
  historias: HistoriaRepository;
  calidad: CalidadPort;
  auditoria: RepositorioAuditoria;
}

export async function reenviarHistoria(
  input: ReenviarHistoriaInput,
  deps: ReenviarHistoriaDeps
): Promise<HistoriaRecord> {
  const historia = await deps.historias.obtenerPorId(input.historiaId);
  if (!historia) {
    throw notFound("Historia no encontrada");
  }

  if (deps.identity.rol !== "cliente" || deps.identity.clienteId !== historia.clienteId) {
    throw forbidden("No autorizado para reenviar la historia");
  }

  if (historia.estado !== "INCOMPLETA") {
    throw conflict("Solo se puede reenviar una historia incompleta");
  }

  const estadoBase = transicionarEstado(historia.estado, "REENVIAR");
  const evaluacion = await deps.calidad.evaluar({
    historiaTexto: input.textoOcr ? `${input.textoOriginal}\n${input.textoOcr}` : input.textoOriginal,
    contieneContenidoOcr: input.contieneContenidoOcr ?? false
  });

  const siguienteEstado = evaluacion.completa
    ? transicionarEstado(estadoBase, "CALIDAD_COMPLETA")
    : transicionarEstado(estadoBase, "CALIDAD_INCOMPLETA");

  await deps.auditoria.registrar({
    historiaId: historia.id,
    evento: "reenviada",
    actor: deps.identity.userId,
    detalle: { estadoAnterior: historia.estado, estadoPosterior: siguienteEstado }
  });

  return deps.historias.actualizar(historia.id, {
    textoOriginal: input.textoOriginal,
    textoOcr: input.textoOcr ?? null,
    contieneContenidoOcr: input.contieneContenidoOcr ?? false,
    estado: siguienteEstado,
    resultadoCompletitud: evaluacion.completa ? "completa" : "incompleta",
    feedbackCompletitud: evaluacion.feedbackResumen,
    sugerenciasMejora: evaluacion.sugerenciasMejora
  });
}
