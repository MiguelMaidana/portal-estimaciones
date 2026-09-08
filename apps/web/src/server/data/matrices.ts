import type { SupabaseClient } from "@supabase/supabase-js";
import { matrizSizingSchema } from "@portal-estimaciones/sizing-engine";
import DEMOMatrix from "../../../../../packages/sizing-engine/matrices/DEMO.json";
import type { MatrizRepository } from "../use-cases/contracts";
import { getSupabaseAdminClient } from "./supabase-admin";

type MatrizRow = {
  id: string;
  cliente_id: string;
  version: number;
  criterios: unknown;
  umbrales: unknown;
  vigente_desde: string;
  creada_por: string;
};

function createMemoryMatrizRepository(): MatrizRepository {
  return {
    async obtenerVigente(clienteId: string) {
      return {
        id: `matriz-${clienteId}-demo`,
        matriz: matrizSizingSchema.parse(DEMOMatrix)
      };
    }
  };
}

async function obtenerVigenteDesdeDb(client: SupabaseClient, clienteId: string) {
  const { data, error } = await client
    .from("matriz_sizing")
    .select("id, cliente_id, version, criterios, umbrales, vigente_desde, creada_por")
    .eq("cliente_id", clienteId)
    .order("vigente_desde", { ascending: false })
    .limit(1)
    .maybeSingle<MatrizRow>();

  if (error) {
    throw error;
  }

  if (!data) {
    return {
      id: `matriz-${clienteId}-demo`,
      matriz: matrizSizingSchema.parse(DEMOMatrix)
    };
  }

  return {
    id: data.id,
    matriz: matrizSizingSchema.parse({
      pesos: data.criterios,
      umbrales_tamano: data.umbrales
    })
  };
}

export class MatrizMemoryRepository implements MatrizRepository {
  private readonly memory = createMemoryMatrizRepository();
  private readonly client = getSupabaseAdminClient();

  async obtenerVigente(clienteId: string) {
    if (!this.client) {
      return this.memory.obtenerVigente(clienteId);
    }

    return obtenerVigenteDesdeDb(this.client, clienteId);
  }
}

export function crearMatrizRepositoryMemoria(): MatrizRepository {
  return new MatrizMemoryRepository();
}
