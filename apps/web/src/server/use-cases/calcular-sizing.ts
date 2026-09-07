import { calcularPuntos, calcularTamano } from "@portal-estimaciones/sizing-engine";
import { forbidden, conflict, notFound } from "../http/errors";
import type {
  HistoriaRepository,
  MatrizRepository,
  RepositorioAuditoria,
  SessionIdentity,
  SizingPort
} from "./contracts";

export interface CalcularSizingInput {
  historiaId: string;
}

export interface CalcularSizingDeps {
  identity: SessionIdentity;
  historias: HistoriaRepository;
  matrices: MatrizRepository;
  sizing: SizingPort;
  auditoria: RepositorioAuditoria;
}

export async function calcularSizing(
  input: CalcularSizingInput,
  deps: CalcularSizingDeps
): Promise<void> {
  const historia = await deps.historias.obtenerPorId(input.historiaId);
  if (!historia) {
    throw notFound("Historia no encontrada");
  }

  if (deps.identity.rol !== "lider" && deps.identity.clienteId !== historia.clienteId) {
    throw forbidden("No autorizado para calcular sizing");
  }

  if (historia.estado !== "COMPLETA") {
    throw conflict("La historia debe estar completa para calcular sizing");
  }

  const matriz = await deps.matrices.obtenerVigente(historia.clienteId);
  const criterios = await deps.sizing.extraerCriterios({
    historiaTexto: historia.textoOcr ? `${historia.textoOriginal}\n${historia.textoOcr}` : historia.textoOriginal,
    contieneContenidoOcr: historia.contieneContenidoOcr
  });

  const puntos = calcularPuntos(criterios, matriz.matriz);
  const tamano = calcularTamano(puntos, matriz.matriz);

  await deps.historias.actualizar(historia.id, {
    estado: "PENDIENTE_VALIDACION_LIDER",
    criteriosExtraidos: criterios,
    sizingCalculado: tamano,
    puntosCalculados: puntos,
    matrizSizingId: matriz.id
  });

  await deps.auditoria.registrar({
    historiaId: historia.id,
    evento: "sizing_calculado",
    actor: deps.identity.userId,
    detalle: { tamano, puntos, matrizSizingId: matriz.id }
  });
}
