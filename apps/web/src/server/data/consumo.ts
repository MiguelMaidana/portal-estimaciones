import type { SupabaseClient } from "@supabase/supabase-js";
import { getSupabaseAdminClient } from "./supabase-admin";

export type RegistroConsumo = {
  clienteId: string;
  periodo: string;
  lineaBase: number;
  consumido: number;
};

type ConsumoRow = {
  cliente_id: string;
  periodo: string;
  linea_base: number | string;
  consumido: number | string;
};

function normalizarPeriodo(periodo: string) {
  if (/^\d{4}-\d{2}$/.test(periodo)) {
    return `${periodo}-01`;
  }

  return periodo;
}

function desnormalizarPeriodo(periodo: string) {
  if (/^\d{4}-\d{2}-\d{2}$/.test(periodo)) {
    return periodo.slice(0, 7);
  }

  return periodo;
}

function toNumber(value: number | string) {
  return typeof value === "number" ? value : Number(value);
}

function mapRow(row: ConsumoRow): RegistroConsumo {
  return {
    clienteId: row.cliente_id,
    periodo: desnormalizarPeriodo(row.periodo),
    lineaBase: toNumber(row.linea_base),
    consumido: toNumber(row.consumido)
  };
}

function createMemoryConsumptionRepository() {
  const items = new Map<string, RegistroConsumo>();

  return {
    async obtener(clienteId: string, periodo: string) {
      return items.get(`${clienteId}:${periodo}`) ?? null;
    },
    async guardar(registro: RegistroConsumo) {
      items.set(`${registro.clienteId}:${registro.periodo}`, registro);
      return registro;
    },
    async ajustar(clienteId: string, periodo: string, lineaBase: number, deltaConsumido: number) {
      const actual =
        (await items.get(`${clienteId}:${periodo}`)) ?? {
          clienteId,
          periodo,
          lineaBase,
          consumido: 0
        };

      const siguiente = {
        ...actual,
        lineaBase,
        consumido: actual.consumido + deltaConsumido
      };

      items.set(`${siguiente.clienteId}:${siguiente.periodo}`, siguiente);
      return siguiente;
    }
  };
}

async function upsertConsumo(client: SupabaseClient, registro: RegistroConsumo) {
  const payload = {
    cliente_id: registro.clienteId,
    periodo: normalizarPeriodo(registro.periodo),
    linea_base: registro.lineaBase,
    consumido: registro.consumido
  };

  const { error } = await client.from("consumo_mensual").upsert(payload, { onConflict: "cliente_id,periodo" });
  if (error) {
    throw error;
  }

  const guardado = await obtenerConsumo(client, registro.clienteId, registro.periodo);
  if (!guardado) {
    throw new Error("No se pudo recuperar el consumo guardado");
  }

  return guardado;
}

async function obtenerConsumo(client: SupabaseClient, clienteId: string, periodo: string) {
  const { data, error } = await client
    .from("consumo_mensual")
    .select("cliente_id, periodo, linea_base, consumido")
    .eq("cliente_id", clienteId)
    .eq("periodo", normalizarPeriodo(periodo))
    .maybeSingle<ConsumoRow>();

  if (error) {
    throw error;
  }

  return data ? mapRow(data) : null;
}

export class ConsumoMemoryRepository {
  private readonly memory = createMemoryConsumptionRepository();
  private readonly client = getSupabaseAdminClient();

  async obtener(clienteId: string, periodo: string): Promise<RegistroConsumo | null> {
    if (!this.client) {
      return this.memory.obtener(clienteId, periodo);
    }

    return obtenerConsumo(this.client, clienteId, periodo);
  }

  async guardar(registro: RegistroConsumo): Promise<RegistroConsumo> {
    if (!this.client) {
      return this.memory.guardar(registro);
    }

    const result = await upsertConsumo(this.client, registro);
    if (!result) {
      throw new Error("No se pudo guardar el consumo");
    }

    return result;
  }

  async ajustar(clienteId: string, periodo: string, lineaBase: number, deltaConsumido: number): Promise<RegistroConsumo> {
    if (!this.client) {
      return this.memory.ajustar(clienteId, periodo, lineaBase, deltaConsumido);
    }

    const actual = (await this.obtener(clienteId, periodo)) ?? {
      clienteId,
      periodo,
      lineaBase,
      consumido: 0
    };

    return this.guardar({
      ...actual,
      lineaBase,
      consumido: actual.consumido + deltaConsumido
    });
  }
}
