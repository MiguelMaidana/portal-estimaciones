import { transicionarEstado } from "../domain/transitions";
import { forbidden } from "../http/errors";
import type { CalidadPort, HistoriaRecord, HistoriaRepository, RepositorioAuditoria, SessionIdentity } from "./contracts";

export interface CrearHistoriaInput {
  clienteId: string;
  textoOriginal: string;
  textoOcr?: string | null;
  contieneContenidoOcr?: boolean;
}

export interface CrearHistoriaDeps {
  identity: SessionIdentity;
  historias: HistoriaRepository;
  calidad: CalidadPort;
  auditoria: RepositorioAuditoria;
}

export async function crearHistoria(input: CrearHistoriaInput, deps: CrearHistoriaDeps): Promise<HistoriaRecord> {
  if (deps.identity.rol !== "cliente") {
    throw forbidden("Solo cliente puede crear historias");
  }

  if (deps.identity.clienteId !== input.clienteId) {
    throw forbidden("La historia no pertenece al cliente autenticado");
  }

  const base: HistoriaRecord = {
    id: crypto.randomUUID(),
    clienteId: input.clienteId,
    textoOriginal: input.textoOriginal,
    textoOcr: input.textoOcr ?? null,
    contieneContenidoOcr: input.contieneContenidoOcr ?? false,
    estado: "BORRADOR",
    resultadoCompletitud: null,
    feedbackCompletitud: null,
    sugerenciasMejora: null,
    criteriosExtraidos: null,
    sizingCalculado: null,
    puntosCalculados: null,
    matrizSizingId: null
  };

  const creada = await deps.historias.crear(base);
  await deps.auditoria.registrar({
    historiaId: creada.id,
    evento: "cargada",
    actor: deps.identity.userId,
    detalle: { estadoAnterior: "BORRADOR", estadoPosterior: "BORRADOR" }
  });

  const estadoAnalisis = transicionarEstado(creada.estado, "ENVIAR_A_ANALISIS");
  const evaluacion = await deps.calidad.evaluar({
    historiaTexto: input.textoOcr ? `${input.textoOriginal}\n${input.textoOcr}` : input.textoOriginal,
    contieneContenidoOcr: input.contieneContenidoOcr ?? false
  });

  const siguienteEstado = evaluacion.completa ? transicionarEstado(estadoAnalisis, "CALIDAD_COMPLETA") : transicionarEstado(estadoAnalisis, "CALIDAD_INCOMPLETA");

  return deps.historias.actualizar(creada.id, {
    estado: siguienteEstado,
    resultadoCompletitud: evaluacion.completa ? "completa" : "incompleta",
    feedbackCompletitud: evaluacion.feedbackResumen,
    sugerenciasMejora: evaluacion.sugerenciasMejora
  });
}
