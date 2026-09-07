import type { z } from "zod";
import { resultadoCalidadSchema } from "@portal-estimaciones/shared";

type ResultadoCalidad = z.infer<typeof resultadoCalidadSchema>;

export function calcularCompleta(resultado: ResultadoCalidad): boolean {
  const { dimensiones } = resultado;
  return (
    dimensiones.completitud.cumple &&
    dimensiones.ambiguedad.cumple &&
    dimensiones.buenas_practicas_redaccion.cumple &&
    dimensiones.arquitectura_invest.independiente &&
    dimensiones.arquitectura_invest.negociable &&
    dimensiones.arquitectura_invest.valiosa &&
    dimensiones.arquitectura_invest.estimable &&
    dimensiones.arquitectura_invest.acotada &&
    dimensiones.arquitectura_invest.testeable &&
    dimensiones.dependencias.cumple
  );
}
