import { z } from "zod";

export const matrizSizingSchema = z.object({
  pesos: z.object({
    complejidad_tecnica: z.object({
      baja: z.number().nonnegative(),
      media: z.number().nonnegative(),
      alta: z.number().nonnegative()
    }),
    por_integracion_detectada: z.number().nonnegative(),
    por_ambiguedad_detectada: z.number().nonnegative(),
    por_dependencia_externa: z.number().nonnegative(),
    por_criterio_aceptacion: z.number().nonnegative()
  }),
  umbrales_tamano: z
    .array(
      z.object({
        tamano: z.enum(["XS", "S", "M", "L", "XL"]),
        puntos_max: z.number().nonnegative().nullable()
      })
    )
    .min(1)
});

export type MatrizSizing = z.infer<typeof matrizSizingSchema>;
