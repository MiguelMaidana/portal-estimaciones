import type { MatrizSizing } from "./matrix-schema";

export interface CriteriosExtraidos {
  complejidad_tecnica: "baja" | "media" | "alta";
  menciona_integraciones: boolean;
  integraciones_detectadas: string[];
  ambiguedades_detectadas: string[];
  dependencias_externas: string[];
  cantidad_criterios_aceptacion_estimados: number;
  alerta_fuera_de_matriz: string | null;
}

export function calcularPuntos(criterios: CriteriosExtraidos, matriz: MatrizSizing): number {
  return (
    matriz.pesos.complejidad_tecnica[criterios.complejidad_tecnica] +
    criterios.integraciones_detectadas.length * matriz.pesos.por_integracion_detectada +
    criterios.ambiguedades_detectadas.length * matriz.pesos.por_ambiguedad_detectada +
    criterios.dependencias_externas.length * matriz.pesos.por_dependencia_externa +
    criterios.cantidad_criterios_aceptacion_estimados * matriz.pesos.por_criterio_aceptacion
  );
}

export function calcularTamano(puntos: number, matriz: MatrizSizing): MatrizSizing["umbrales_tamano"][number]["tamano"] {
  for (const umbral of matriz.umbrales_tamano) {
    if (umbral.puntos_max === null) {
      return umbral.tamano;
    }

    if (puntos <= umbral.puntos_max) {
      return umbral.tamano;
    }
  }

  return "XL";
}
