export const rolesUsuario = ["cliente", "lider", "equipo_delivery"] as const;
export type RolUsuario = (typeof rolesUsuario)[number];

export const estadosHistoria = [
  "BORRADOR",
  "EN_ANALISIS_COMPLETITUD",
  "INCOMPLETA",
  "COMPLETA",
  "EN_SIZING",
  "PENDIENTE_REVISION_OCR",
  "SIZING_CALCULADO",
  "PENDIENTE_VALIDACION_LIDER",
  "SIZING_VALIDADO",
  "PENDIENTE_ACEPTACION_CLIENTE",
  "RECHAZADA_POR_CLIENTE",
  "ACEPTADA",
  "EN_EJECUCION",
  "ENTREGADA"
] as const;
export type EstadoHistoria = (typeof estadosHistoria)[number];

export const tamanosSizing = ["XS", "S", "M", "L", "XL"] as const;
export type TamanoSizing = (typeof tamanosSizing)[number];

export const eventosHistoria = [
  "ENVIAR_A_ANALISIS",
  "CALIDAD_INCOMPLETA",
  "CALIDAD_COMPLETA",
  "REENVIAR",
  "INICIAR_SIZING",
  "SIZING_OBTENIDO",
  "SOLICITAR_VALIDACION",
  "APROBAR_SIZING",
  "CORREGIR_SIZING",
  "PUBLICAR_AL_CLIENTE",
  "ACEPTAR",
  "RECHAZAR",
  "INICIAR_EJECUCION",
  "ENTREGAR",
  "REQUIERE_REVISION_OCR",
  "OCR_APROBADO",
  "OCR_RECHAZADO"
] as const;
export type EventoHistoria = (typeof eventosHistoria)[number];
