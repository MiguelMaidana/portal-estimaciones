import type { SupabaseClient } from "@supabase/supabase-js";
import type { SessionIdentity } from "../use-cases/contracts";
import { getSupabaseAdminClient } from "./supabase-admin";

type UsuarioRow = {
  id: string;
  rol: SessionIdentity["rol"];
  cliente_id: string | null;
  activo: boolean;
};

function createMemoryUsuarioRepository() {
  const items = new Map<string, SessionIdentity>();

  return {
    async guardar(identity: SessionIdentity) {
      items.set(identity.userId, identity);
    },
    async obtenerActivo(userId: string) {
      return items.get(userId) ?? null;
    }
  };
}

async function obtenerUsuarioActivo(client: SupabaseClient, userId: string): Promise<SessionIdentity | null> {
  const { data, error } = await client
    .from("usuario")
    .select("id, rol, cliente_id, activo")
    .eq("id", userId)
    .maybeSingle<UsuarioRow>();

  if (error) {
    throw error;
  }

  if (!data || !data.activo) {
    return null;
  }

  return {
    userId: data.id,
    rol: data.rol,
    clienteId: data.cliente_id
  };
}

export class UsuarioMemoryRepository {
  private readonly memory = createMemoryUsuarioRepository();
  private readonly client = getSupabaseAdminClient();

  async guardar(identity: SessionIdentity): Promise<void> {
    if (!this.client) {
      await this.memory.guardar(identity);
      return;
    }

    const payload = {
      id: identity.userId,
      rol: identity.rol,
      cliente_id: identity.clienteId,
      activo: true
    };

    const { error } = await this.client.from("usuario").upsert(payload, { onConflict: "id" });
    if (error) {
      throw error;
    }
  }

  async obtenerActivo(userId: string): Promise<SessionIdentity | null> {
    if (!this.client) {
      return this.memory.obtenerActivo(userId);
    }

    return obtenerUsuarioActivo(this.client, userId);
  }
}
