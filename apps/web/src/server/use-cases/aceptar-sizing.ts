import { transicionarEstado } from "../domain/transitions";
import { conflict, forbidden, notFound } from "../http/errors";
import type { HistoriaRepository, RepositorioAuditoria, SessionIdentity } from "./contracts";
import type { ConsumoMemoryRepository } from "../data/consumo";

export interface AceptarSizingInput {
  historiaId: string;
  aceptado: boolean;
  periodo: string;
}

export interface AceptarSizingDeps {
  identity: SessionIdentity;
  historias: HistoriaRepository;
  consumo: ConsumoMemoryRepository;
  auditoria: RepositorioAuditoria;
  lineaBasePuntos: number;
}

export async function aceptarSizing(input: AceptarSizingInput, deps: AceptarSizingDeps): Promise<void> {
  const historia = await deps.historias.obtenerPorId(input.historiaId);
  if (!historia) {
    throw notFound("Historia no encontrada");
  }

  if (deps.identity.rol !== "cliente" || deps.identity.clienteId !== historia.clienteId) {
    throw forbidden("No autorizado para aceptar sizing");
  }

  if (historia.estado !== "PENDIENTE_ACEPTACION_CLIENTE") {
    throw conflict("La historia no esta pendiente de aceptacion");
  }

  const siguienteEstado = input.aceptado
    ? transicionarEstado(historia.estado, "ACEPTAR")
    : transicionarEstado(historia.estado, "RECHAZAR");

  if (input.aceptado) {
    await deps.consumo.ajustar(
      historia.clienteId,
      input.periodo,
      deps.lineaBasePuntos,
      historia.puntosCalculados ?? 0
    );
  }

  await deps.auditoria.registrar({
    historiaId: historia.id,
    evento: input.aceptado ? "aceptada" : "rechazada",
    actor: deps.identity.userId,
    detalle: { estadoAnterior: historia.estado, estadoPosterior: siguienteEstado, periodo: input.periodo }
  });

  await deps.historias.actualizar(historia.id, {
    estado: siguienteEstado,
    aceptadaPorCliente: input.aceptado
  });
}
