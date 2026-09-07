export interface ClienteSeed {
  nombre: string;
  servicio: string;
  lineaBasePuntos: number;
}

export const clienteDemoSeed: ClienteSeed = {
  nombre: "DEMO",
  servicio: "DEMO",
  lineaBasePuntos: Number(process.env.DEMO_LINEA_BASE_PUNTOS ?? "100")
};
