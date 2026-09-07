import { z } from "zod";

export const criteriosExtraidosSchema = z.object({
  complejidad_tecnica: z.enum(["baja", "media", "alta"]),
  menciona_integraciones: z.boolean(),
  integraciones_detectadas: z.array(z.string()),
  ambiguedades_detectadas: z.array(z.string()),
  cantidad_criterios_aceptacion_estimados: z.number().int().nonnegative(),
  dependencias_externas: z.array(z.string()),
  alerta_fuera_de_matriz: z.string().nullable()
});
