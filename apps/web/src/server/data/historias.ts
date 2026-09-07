import type { HistoriaRecord, HistoriaRepository } from "../use-cases/contracts";

export class HistoriaMemoryRepository implements HistoriaRepository {
  private readonly items = new Map<string, HistoriaRecord>();

  async crear(input: HistoriaRecord): Promise<HistoriaRecord> {
    this.items.set(input.id, input);
    return input;
  }

  async actualizar(id: string, patch: Partial<HistoriaRecord>): Promise<HistoriaRecord> {
    const actual = this.items.get(id);
    if (!actual) {
      throw new Error("Historia no encontrada");
    }

    const actualizado = { ...actual, ...patch };
    this.items.set(id, actualizado);
    return actualizado;
  }

  async obtenerPorId(id: string): Promise<HistoriaRecord | null> {
    return this.items.get(id) ?? null;
  }

  async listar(): Promise<HistoriaRecord[]> {
    return Array.from(this.items.values());
  }
}

export function crearHistoriaRepositoryMemoria(): HistoriaRepository {
  return new HistoriaMemoryRepository();
}
