import { z } from "zod";
import { estadosHistoria } from "../domain";

export const estadoHistoriaSchema = z.enum(estadosHistoria);

export const historiaBaseSchema = z.object({
  id: z.string().uuid(),
  clienteId: z.string().uuid(),
  textoOriginal: z.string().min(1),
  textoOcr: z.string().nullable().optional(),
  contieneContenidoOcr: z.boolean().default(false),
  estado: estadoHistoriaSchema
});
