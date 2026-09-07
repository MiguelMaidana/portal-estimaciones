import type { z } from "zod";
import { resultadoCalidadSchema } from "@portal-estimaciones/shared";

export interface QualityModel {
  evaluate(input: {
    historiaTexto: string;
    contieneContenidoOcr: boolean;
  }): Promise<z.infer<typeof resultadoCalidadSchema>>;
}
