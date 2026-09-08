import type { SupabaseClient } from "@supabase/supabase-js";
import type { HistoriaRecord, HistoriaRepository } from "../use-cases/contracts";
import { getSupabaseAdminClient } from "./supabase-admin";

type HistoriaRow = {
  id: string;
  cliente_id: string;
  texto_original: string;
  texto_ocr: string | null;
  contiene_contenido_ocr: boolean;
  estado: HistoriaRecord["estado"];
  resultado_completitud: HistoriaRecord["resultadoCompletitud"] | null;
  feedback_completitud: string | null;
  sugerencias_mejora: string[] | null;
  criterios_extraidos: HistoriaRecord["criteriosExtraidos"] | null;
  sizing_calculado: HistoriaRecord["sizingCalculado"] | null;
  puntos_calculados: number | string | null;
  matriz_sizing_id: string | null;
  sizing_validado_por: string | null;
  sizing_validado_en: string | null;
  aceptada_por_cliente: boolean | null;
  fecha_entrega: string | null;
  fecha_carga: string | null;
};

type HistoriaInsert = Partial<HistoriaRow> & Pick<HistoriaRow, "id" | "cliente_id" | "texto_original" | "estado">;

function toNumber(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  return typeof value === "number" ? value : Number(value);
}

function mapRow(row: HistoriaRow): HistoriaRecord {
  return {
    id: row.id,
    clienteId: row.cliente_id,
    textoOriginal: row.texto_original,
    textoOcr: row.texto_ocr,
    contieneContenidoOcr: row.contiene_contenido_ocr,
    estado: row.estado,
    resultadoCompletitud: row.resultado_completitud,
    feedbackCompletitud: row.feedback_completitud,
    sugerenciasMejora: row.sugerencias_mejora,
    criteriosExtraidos: row.criterios_extraidos,
    sizingCalculado: row.sizing_calculado,
    puntosCalculados: toNumber(row.puntos_calculados),
    matrizSizingId: row.matriz_sizing_id,
    sizingValidadoPor: row.sizing_validado_por,
    sizingValidadoEn: row.sizing_validado_en,
    aceptadaPorCliente: row.aceptada_por_cliente,
    fechaEntrega: row.fecha_entrega
  };
}

function mapPatch(patch: Partial<HistoriaRecord>): Partial<HistoriaRow> {
  const mapped: Partial<HistoriaRow> = {};

  if (patch.clienteId !== undefined) mapped.cliente_id = patch.clienteId;
  if (patch.textoOriginal !== undefined) mapped.texto_original = patch.textoOriginal;
  if (patch.textoOcr !== undefined) mapped.texto_ocr = patch.textoOcr ?? null;
  if (patch.contieneContenidoOcr !== undefined) mapped.contiene_contenido_ocr = patch.contieneContenidoOcr;
  if (patch.estado !== undefined) mapped.estado = patch.estado;
  if (patch.resultadoCompletitud !== undefined) mapped.resultado_completitud = patch.resultadoCompletitud ?? null;
  if (patch.feedbackCompletitud !== undefined) mapped.feedback_completitud = patch.feedbackCompletitud ?? null;
  if (patch.sugerenciasMejora !== undefined) mapped.sugerencias_mejora = patch.sugerenciasMejora ?? null;
  if (patch.criteriosExtraidos !== undefined) mapped.criterios_extraidos = patch.criteriosExtraidos ?? null;
  if (patch.sizingCalculado !== undefined) mapped.sizing_calculado = patch.sizingCalculado ?? null;
  if (patch.puntosCalculados !== undefined) mapped.puntos_calculados = patch.puntosCalculados ?? null;
  if (patch.matrizSizingId !== undefined) mapped.matriz_sizing_id = patch.matrizSizingId ?? null;
  if (patch.sizingValidadoPor !== undefined) mapped.sizing_validado_por = patch.sizingValidadoPor ?? null;
  if (patch.sizingValidadoEn !== undefined) mapped.sizing_validado_en = patch.sizingValidadoEn ?? null;
  if (patch.aceptadaPorCliente !== undefined) mapped.aceptada_por_cliente = patch.aceptadaPorCliente ?? null;
  if (patch.fechaEntrega !== undefined) mapped.fecha_entrega = patch.fechaEntrega ?? null;

  return mapped;
}

function createMemoryHistoryRepository(): HistoriaRepository {
  const items = new Map<string, HistoriaRecord>();

  return {
    async crear(input) {
      items.set(input.id, input);
      return input;
    },
    async actualizar(id, patch) {
      const actual = items.get(id);
      if (!actual) {
        throw new Error("Historia no encontrada");
      }

      const actualizado = { ...actual, ...patch };
      items.set(id, actualizado);
      return actualizado;
    },
    async obtenerPorId(id) {
      return items.get(id) ?? null;
    },
    async listar() {
      return Array.from(items.values());
    }
  };
}

async function selectHistoria(client: SupabaseClient, id: string) {
  const { data, error } = await client
    .from("historia_usuario")
    .select(
      "id, cliente_id, texto_original, texto_ocr, contiene_contenido_ocr, estado, resultado_completitud, feedback_completitud, sugerencias_mejora, criterios_extraidos, sizing_calculado, puntos_calculados, matriz_sizing_id, sizing_validado_por, sizing_validado_en, aceptada_por_cliente, fecha_entrega, fecha_carga"
    )
    .eq("id", id)
    .maybeSingle<HistoriaRow>();

  if (error) {
    throw error;
  }

  return data ? mapRow(data) : null;
}

export class HistoriaMemoryRepository implements HistoriaRepository {
  private readonly memory = createMemoryHistoryRepository();
  private readonly client = getSupabaseAdminClient();

  async crear(input: HistoriaRecord): Promise<HistoriaRecord> {
    if (!this.client) {
      return this.memory.crear(input);
    }

    const insert: HistoriaInsert = {
      id: input.id,
      cliente_id: input.clienteId,
      texto_original: input.textoOriginal,
      estado: input.estado,
      texto_ocr: input.textoOcr ?? null,
      contiene_contenido_ocr: input.contieneContenidoOcr,
      resultado_completitud: input.resultadoCompletitud ?? null,
      feedback_completitud: input.feedbackCompletitud ?? null,
      sugerencias_mejora: input.sugerenciasMejora ?? null,
      criterios_extraidos: input.criteriosExtraidos ?? null,
      sizing_calculado: input.sizingCalculado ?? null,
      puntos_calculados: input.puntosCalculados ?? null,
      matriz_sizing_id: input.matrizSizingId ?? null,
      sizing_validado_por: input.sizingValidadoPor ?? null,
      sizing_validado_en: input.sizingValidadoEn ?? null,
      aceptada_por_cliente: input.aceptadaPorCliente ?? null,
      fecha_entrega: input.fechaEntrega ?? null
    };

    const { error } = await this.client.from("historia_usuario").upsert(insert, { onConflict: "id" });
    if (error) {
      throw error;
    }

    const creada = await selectHistoria(this.client, input.id);
    if (!creada) {
      throw new Error("Historia no encontrada luego de insertar");
    }

    return creada;
  }

  async actualizar(id: string, patch: Partial<HistoriaRecord>): Promise<HistoriaRecord> {
    if (!this.client) {
      return this.memory.actualizar(id, patch);
    }

    const mapped = mapPatch(patch);
    const { error } = await this.client.from("historia_usuario").update(mapped).eq("id", id);

    if (error) {
      throw error;
    }

    const actualizada = await selectHistoria(this.client, id);
    if (!actualizada) {
      throw new Error("Historia no encontrada");
    }

    return actualizada;
  }

  async obtenerPorId(id: string): Promise<HistoriaRecord | null> {
    if (!this.client) {
      return this.memory.obtenerPorId(id);
    }

    return selectHistoria(this.client, id);
  }

  async listar(): Promise<HistoriaRecord[]> {
    if (!this.client) {
      return this.memory.listar();
    }

    const { data, error } = await this.client
      .from("historia_usuario")
      .select(
        "id, cliente_id, texto_original, texto_ocr, contiene_contenido_ocr, estado, resultado_completitud, feedback_completitud, sugerencias_mejora, criterios_extraidos, sizing_calculado, puntos_calculados, matriz_sizing_id, sizing_validado_por, sizing_validado_en, aceptada_por_cliente, fecha_entrega, fecha_carga"
      )
      .order("fecha_carga", { ascending: false })
      .returns<HistoriaRow[]>();

    if (error) {
      throw error;
    }

    return (data ?? []).map(mapRow);
  }
}

export function crearHistoriaRepositoryMemoria(): HistoriaRepository {
  return new HistoriaMemoryRepository();
}
