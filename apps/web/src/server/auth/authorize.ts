import type { RolUsuario } from "@portal-estimaciones/shared";
import { forbidden } from "../http/errors";
import type { SessionIdentity } from "./resolve-identity";

export function requireRole(identity: SessionIdentity, allowed: RolUsuario[]) {
  if (!allowed.includes(identity.rol)) {
    throw forbidden("Role not allowed");
  }
}

export function requireClientePropietario(identity: SessionIdentity, clienteId: string) {
  if (identity.rol !== "cliente" || identity.clienteId !== clienteId) {
    throw forbidden("Cliente not allowed");
  }
}
