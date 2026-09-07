import type { TamanoSizing } from "@portal-estimaciones/shared";
import { transicionarEstado } from "../domain/transitions";
import { conflict, forbidden, notFound } from "../http/errors";
import type { HistoriaRepository, RepositorioAuditoria, SessionIdentity } from "./contracts";

export interface ValidarSizingInput {
  historiaId: string;
  aprobado: boolean;
  sizingCorregido?: TamanoSizing;
}

export interface ValidarSizingDeps {
  identity: SessionIdentity;
  historias: HistoriaRepository;
  auditoria: RepositorioAuditoria;
}

export async function validarSizing(input: ValidarSizingInput, deps: ValidarSizingDeps): Promise<void> {
  const historia = await deps.historias.obtenerPorId(input.historiaId);
  if (!historia) {
    throw notFound("Historia no encontrada");
  }

  if (deps.identity.rol !== "lider") {
    throw forbidden("Solo lider puede validar sizing");
  }

  if (historia.estado !== "PENDIENTE_VALIDACION_LIDER") {
    throw conflict("La historia no esta pendiente de validacion");
  }

  const siguienteEstado = input.aprobado
    ? transicionarEstado(historia.estado, "APROBAR_SIZING")
    : transicionarEstado(historia.estado, "CORREGIR_SIZING");

  await deps.auditoria.registrar({
    historiaId: historia.id,
    evento: input.aprobado ? "sizing_aprobado" : "sizing_corregido",
    actor: deps.identity.userId,
    detalle: {
      estadoAnterior: historia.estado,
      estadoPosterior: siguienteEstado,
      sizingCorregido: input.sizingCorregido ?? null
    }
  });

  await deps.historias.actualizar(historia.id, {
    estado: siguienteEstado,
    sizingCalculado: input.aprobado ? historia.sizingCalculado : input.sizingCorregido ?? historia.sizingCalculado,
    sizingValidadoPor: deps.identity.userId,
    sizingValidadoEn: new Date().toISOString()
  });
}
