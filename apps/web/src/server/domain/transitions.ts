import type { EstadoHistoria, EventoHistoria } from "@portal-estimaciones/shared";
import { conflict } from "../http/errors";

const transitions: Record<EstadoHistoria, Partial<Record<EventoHistoria, EstadoHistoria>>> = {
  BORRADOR: { ENVIAR_A_ANALISIS: "EN_ANALISIS_COMPLETITUD" },
  EN_ANALISIS_COMPLETITUD: {
    CALIDAD_INCOMPLETA: "INCOMPLETA",
    CALIDAD_COMPLETA: "COMPLETA"
  },
  INCOMPLETA: { REENVIAR: "BORRADOR" },
  COMPLETA: { INICIAR_SIZING: "EN_SIZING" },
  EN_SIZING: { SIZING_OBTENIDO: "SIZING_CALCULADO" },
  PENDIENTE_REVISION_OCR: {
    OCR_APROBADO: "COMPLETA",
    OCR_RECHAZADO: "INCOMPLETA"
  },
  SIZING_CALCULADO: { SOLICITAR_VALIDACION: "PENDIENTE_VALIDACION_LIDER" },
  PENDIENTE_VALIDACION_LIDER: {
    APROBAR_SIZING: "SIZING_VALIDADO",
    CORREGIR_SIZING: "EN_SIZING"
  },
  SIZING_VALIDADO: { PUBLICAR_AL_CLIENTE: "PENDIENTE_ACEPTACION_CLIENTE" },
  PENDIENTE_ACEPTACION_CLIENTE: {
    ACEPTAR: "ACEPTADA",
    RECHAZAR: "RECHAZADA_POR_CLIENTE"
  },
  RECHAZADA_POR_CLIENTE: {},
  ACEPTADA: { INICIAR_EJECUCION: "EN_EJECUCION" },
  EN_EJECUCION: { ENTREGAR: "ENTREGADA" },
  ENTREGADA: {}
};

export function transicionarEstado(actual: EstadoHistoria, evento: EventoHistoria): EstadoHistoria {
  const siguiente = transitions[actual]?.[evento];
  if (!siguiente) {
    throw conflict(`Transicion invalida: ${actual} -> ${evento}`);
  }
  return siguiente;
}
