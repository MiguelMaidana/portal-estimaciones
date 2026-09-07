import { transicionarEstado } from "../domain/transitions";
import { conflict, forbidden, notFound } from "../http/errors";
import type { HistoriaRepository, RepositorioAuditoria, SessionIdentity } from "./contracts";

export interface EntregarHistoriaInput {
  historiaId: string;
}

export interface EntregarHistoriaDeps {
  identity: SessionIdentity;
  historias: HistoriaRepository;
  auditoria: RepositorioAuditoria;
}

export async function entregarHistoria(input: EntregarHistoriaInput, deps: EntregarHistoriaDeps): Promise<void> {
  const historia = await deps.historias.obtenerPorId(input.historiaId);
  if (!historia) {
    throw notFound("Historia no encontrada");
  }

  if (deps.identity.rol !== "lider") {
    throw forbidden("Solo lider puede entregar");
  }

  if (!["ACEPTADA", "EN_EJECUCION"].includes(historia.estado)) {
    throw conflict("La historia no esta lista para entrega");
  }

  const base = historia.estado === "ACEPTADA"
    ? transicionarEstado(historia.estado, "INICIAR_EJECUCION")
    : historia.estado;
  const siguienteEstado = transicionarEstado(base, "ENTREGAR");

  await deps.auditoria.registrar({
    historiaId: historia.id,
    evento: "entregada",
    actor: deps.identity.userId,
    detalle: { estadoAnterior: historia.estado, estadoPosterior: siguienteEstado }
  });

  await deps.historias.actualizar(historia.id, {
    estado: siguienteEstado,
    fechaEntrega: new Date().toISOString()
  });
}
