export type RegistroConsumo = {
  clienteId: string;
  periodo: string;
  lineaBase: number;
  consumido: number;
};

export class ConsumoMemoryRepository {
  private readonly items = new Map<string, RegistroConsumo>();

  async obtener(clienteId: string, periodo: string): Promise<RegistroConsumo | null> {
    return this.items.get(`${clienteId}:${periodo}`) ?? null;
  }

  async guardar(registro: RegistroConsumo): Promise<RegistroConsumo> {
    this.items.set(`${registro.clienteId}:${registro.periodo}`, registro);
    return registro;
  }

  async ajustar(clienteId: string, periodo: string, lineaBase: number, deltaConsumido: number): Promise<RegistroConsumo> {
    const actual = (await this.obtener(clienteId, periodo)) ?? {
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

    return this.guardar(siguiente);
  }
}
