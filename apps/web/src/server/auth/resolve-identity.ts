import type { RolUsuario } from "@portal-estimaciones/shared";
import { unauthorized } from "../http/errors";

export interface SessionIdentity {
  userId: string;
  rol: RolUsuario;
  clienteId: string | null;
}

export async function resolveIdentityFromRequest(request: Request): Promise<SessionIdentity> {
  const authorization = request.headers.get("authorization");
  if (!authorization?.startsWith("Bearer ")) {
    throw unauthorized("Missing bearer token");
  }

  throw unauthorized("Supabase auth adapter not wired yet");
}
