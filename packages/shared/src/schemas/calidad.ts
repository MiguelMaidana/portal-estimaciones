import { z } from "zod";

const dimensionSchema = z.object({
  cumple: z.boolean(),
  detalle: z.string()
});

export const resultadoCalidadSchema = z.object({
  dimensiones: z.object({
    completitud: dimensionSchema,
    ambiguedad: dimensionSchema,
    buenas_practicas_redaccion: dimensionSchema,
    arquitectura_invest: z.object({
      independiente: z.boolean(),
      negociable: z.boolean(),
      valiosa: z.boolean(),
      estimable: z.boolean(),
      acotada: z.boolean(),
      testeable: z.boolean(),
      detalle: z.string()
    }),
    dependencias: z.object({
      cumple: z.boolean(),
      detalle: z.string(),
      dependencias_detectadas: z.array(z.string())
    })
  }),
  sugerencias_mejora: z.array(z.string()),
  feedback_resumen: z.string()
});
