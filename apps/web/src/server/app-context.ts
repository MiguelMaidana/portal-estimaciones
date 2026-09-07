import { calcularCompleta } from "@portal-estimaciones/quality-agent";
import type { CriteriosExtraidos } from "@portal-estimaciones/sizing-engine";
import { matrizSizingSchema } from "@portal-estimaciones/sizing-engine";
import DEMOMatrix from "../../../../packages/sizing-engine/matrices/DEMO.json";
import { resolveIdentityFromRequest } from "./auth/resolve-identity";
import { AuditoriaMemoryRepository } from "./data/auditoria";
import { ConsumoMemoryRepository } from "./data/consumo";
import { HistoriaMemoryRepository } from "./data/historias";
import { MatrizMemoryRepository } from "./data/matrices";
import { UsuarioMemoryRepository } from "./data/usuarios";
import { unauthorized } from "./http/errors";
import type { CalidadPort, RepositorioAuditoria, SessionIdentity, SizingPort } from "./use-cases/contracts";

class LocalQualityPort implements CalidadPort {
  async evaluar(input: { historiaTexto: string; contieneContenidoOcr: boolean }) {
    const texto = input.historiaTexto.toLowerCase();
    const tieneActor = texto.includes("como ");
    const tieneBeneficio = texto.includes("para ");
    const completa = tieneActor && tieneBeneficio && texto.length >= 40;

    return {
      completa,
      feedbackResumen: completa
        ? "La historia cumple con el umbral minimo de calidad."
        : "La historia requiere mayor claridad o estructura antes de sizing.",
      sugerenciasMejora: completa
        ? []
        : ["Revisar rol/accion/beneficio", "Agregar contexto suficiente para evitar ambiguedad"]
    };
  }
}

class LocalSizingPort implements SizingPort {
  async extraerCriterios(input: { historiaTexto: string; contieneContenidoOcr: boolean }): Promise<CriteriosExtraidos> {
    const texto = input.historiaTexto.toLowerCase();
    const integraciones_detectadas = texto.includes("api") || texto.includes("integracion") ? ["integracion"] : [];
    const ambiguedades_detectadas = texto.includes("rapido") || texto.includes("facil") ? ["términos vagos"] : [];
    const dependencias_externas = texto.includes("depende") ? ["dependencia externa"] : [];
    const cantidad = Math.max(1, Math.min(5, Math.ceil(input.historiaTexto.length / 120)));

    return {
      complejidad_tecnica: integraciones_detectadas.length > 0 ? "media" : "baja",
      menciona_integraciones: integraciones_detectadas.length > 0,
      integraciones_detectadas,
      ambiguedades_detectadas,
      cantidad_criterios_aceptacion_estimados: cantidad,
      dependencias_externas,
      alerta_fuera_de_matriz: null
    };
  }
}

export interface AppContext {
  identity: SessionIdentity;
  historias: HistoriaMemoryRepository;
  matrices: MatrizMemoryRepository;
  consumo: ConsumoMemoryRepository;
  usuarios: UsuarioMemoryRepository;
  auditoria: RepositorioAuditoria;
  calidad: CalidadPort;
  sizing: SizingPort;
}

const historias = new HistoriaMemoryRepository();
const matrices = new MatrizMemoryRepository();
const consumo = new ConsumoMemoryRepository();
const usuarios = new UsuarioMemoryRepository();
const auditoria = new AuditoriaMemoryRepository();
const calidad = new LocalQualityPort();
const sizing = new LocalSizingPort();

export const appContext: AppContext = {
  identity: {
    userId: "demo-user",
    rol: "cliente",
    clienteId: "demo-cliente"
  },
  historias,
  matrices,
  consumo,
  usuarios,
  auditoria,
  calidad,
  sizing
};

export async function resolveAppIdentity(request: Request) {
  try {
    return await resolveIdentityFromRequest(request);
  } catch {
    if (process.env.NODE_ENV !== "production") {
      const userId = request.headers.get("x-demo-user-id") ?? appContext.identity.userId;
      const rol = (request.headers.get("x-demo-role") as AppContext["identity"]["rol"]) ?? appContext.identity.rol;
      const clienteId = request.headers.get("x-demo-cliente-id") ?? appContext.identity.clienteId;
      return { userId, rol, clienteId };
    }

    throw unauthorized("Unauthorized");
  }
}

export function seedDemoMatrix() {
  void matrices.obtenerVigente("demo-cliente");
  void matrizSizingSchema.parse(DEMOMatrix);
}
