import DEMOMatrix from "../../../../../packages/sizing-engine/matrices/DEMO.json";
import { matrizSizingSchema } from "@portal-estimaciones/sizing-engine";
import type { MatrizRepository } from "../use-cases/contracts";

export class MatrizMemoryRepository implements MatrizRepository {
  async obtenerVigente(clienteId: string) {
    return {
      id: `matriz-${clienteId}-demo`,
      matriz: matrizSizingSchema.parse(DEMOMatrix)
    };
  }
}

export function crearMatrizRepositoryMemoria(): MatrizRepository {
  return new MatrizMemoryRepository();
}
