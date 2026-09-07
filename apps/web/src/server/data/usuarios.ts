import type { SessionIdentity } from "../use-cases/contracts";

export class UsuarioMemoryRepository {
  private readonly items = new Map<string, SessionIdentity>();

  async guardar(identity: SessionIdentity): Promise<void> {
    this.items.set(identity.userId, identity);
  }

  async obtenerActivo(userId: string): Promise<SessionIdentity | null> {
    return this.items.get(userId) ?? null;
  }
}
