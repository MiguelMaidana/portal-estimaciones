import type { SupabaseClient } from "@supabase/supabase-js";
import { getSupabaseAdminClient } from "./supabase-admin";

export type RegistroAuditoria = {
  historiaId: string;
  evento: string;
  actor: string;
  detalle: Record<string, unknown>;
};

type AuditoriaRow = {
  historia_id: string;
  evento: string;
  actor: string;
  detalle: Record<string, unknown> | null;
};

function createMemoryAuditRepository() {
  const items: RegistroAuditoria[] = [];

  return {
    items,
    async registrar(input: RegistroAuditoria) {
      items.push(input);
    }
  };
}

async function registrarAuditoria(client: SupabaseClient, input: RegistroAuditoria) {
  const payload: AuditoriaRow = {
    historia_id: input.historiaId,
    evento: input.evento,
    actor: input.actor,
    detalle: input.detalle
  };

  const { error } = await client.from("log_auditoria").insert(payload);
  if (error) {
    throw error;
  }
}

export class AuditoriaMemoryRepository {
  private readonly memory = createMemoryAuditRepository();
  private readonly client = getSupabaseAdminClient();

  get items() {
    return this.memory.items;
  }

  async registrar(input: RegistroAuditoria): Promise<void> {
    if (!this.client) {
      await this.memory.registrar(input);
      return;
    }

    await registrarAuditoria(this.client, input);
  }
}
