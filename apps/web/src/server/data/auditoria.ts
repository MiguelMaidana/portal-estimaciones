export type RegistroAuditoria = {
  historiaId: string;
  evento: string;
  actor: string;
  detalle: Record<string, unknown>;
};

export class AuditoriaMemoryRepository {
  public readonly items: RegistroAuditoria[] = [];

  async registrar(input: RegistroAuditoria): Promise<void> {
    this.items.push(input);
  }
}
