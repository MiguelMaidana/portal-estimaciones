import type { RolUsuario, EstadoHistoria, TamanoSizing } from "@portal-estimaciones/shared";
import type { CriteriosExtraidos, MatrizSizing } from "@portal-estimaciones/sizing-engine";

export interface SessionIdentity {
  userId: string;
  rol: RolUsuario;
  clienteId: string | null;
}

export interface HistoriaRecord {
  id: string;
  clienteId: string;
  textoOriginal: string;
  textoOcr?: string | null;
  contieneContenidoOcr: boolean;
  estado: EstadoHistoria;
  resultadoCompletitud?: "completa" | "incompleta" | null;
  feedbackCompletitud?: string | null;
  sugerenciasMejora?: string[] | null;
  criteriosExtraidos?: CriteriosExtraidos | null;
  sizingCalculado?: TamanoSizing | null;
  puntosCalculados?: number | null;
  matrizSizingId?: string | null;
  sizingValidadoPor?: string | null;
  sizingValidadoEn?: string | null;
  aceptadaPorCliente?: boolean | null;
  fechaEntrega?: string | null;
}

export interface HistoriaRepository {
  crear(input: HistoriaRecord): Promise<HistoriaRecord>;
  actualizar(id: string, patch: Partial<HistoriaRecord>): Promise<HistoriaRecord>;
  obtenerPorId(id: string): Promise<HistoriaRecord | null>;
  listar(): Promise<HistoriaRecord[]>;
}

export interface MatrizRepository {
  obtenerVigente(clienteId: string): Promise<{ id: string; matriz: MatrizSizing }>;
}

export interface CalidadPort {
  evaluar(input: {
    historiaTexto: string;
    contieneContenidoOcr: boolean;
  }): Promise<{
    completa: boolean;
    feedbackResumen: string;
    sugerenciasMejora: string[];
  }>;
}

export interface SizingPort {
  extraerCriterios(input: {
    historiaTexto: string;
    contieneContenidoOcr: boolean;
  }): Promise<CriteriosExtraidos>;
}

export interface RepositorioAuditoria {
  registrar(input: {
    historiaId: string;
    evento: string;
    actor: string;
    detalle: Record<string, unknown>;
  }): Promise<void>;
}
