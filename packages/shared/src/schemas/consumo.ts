import { z } from "zod";

export const consumoMensualSchema = z.object({
  clienteId: z.string().uuid(),
  periodo: z.string(),
  lineaBase: z.number(),
  consumido: z.number(),
  disponible: z.number()
});
