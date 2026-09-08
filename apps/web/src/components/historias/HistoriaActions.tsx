"use client";

import { useState } from "react";

type HistoriaEstado =
  | "BORRADOR"
  | "EN_ANALISIS_COMPLETITUD"
  | "INCOMPLETA"
  | "COMPLETA"
  | "EN_SIZING"
  | "SIZING_CALCULADO"
  | "PENDIENTE_VALIDACION_LIDER"
  | "SIZING_VALIDADO"
  | "PENDIENTE_ACEPTACION_CLIENTE"
  | "RECHAZADA_POR_CLIENTE"
  | "ACEPTADA"
  | "EN_EJECUCION"
  | "ENTREGADA"
  | "PENDIENTE_REVISION_OCR";

interface HistoriaActionsProps {
  historiaId: string;
  estado: HistoriaEstado;
  demoMode: boolean;
}

async function parseResponse(response: Response) {
  const payload = (await response.json().catch(() => null)) as
    | { error?: { message?: string }; estado?: string; puntosCalculados?: number; sizingCalculado?: string }
    | null;

  if (!response.ok) {
    throw new Error(payload?.error?.message ?? "Operacion fallida");
  }

  return payload;
}

export function HistoriaActions({ historiaId, estado, demoMode }: HistoriaActionsProps) {
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [liderAprueba, setLiderAprueba] = useState(true);
  const [clienteAcepta, setClienteAcepta] = useState(true);
  const [rolDemo, setRolDemo] = useState<"cliente" | "lider">("lider");

  async function runAction(url: string, body?: unknown) {
    setIsRunning(true);
    setError(null);
    setMessage(null);

    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          ...(body ? { "Content-Type": "application/json" } : {}),
          ...(demoMode
            ? {
                "x-demo-mode": "1",
                "x-demo-user-id": demoMode ? `${rolDemo}-user` : "",
                "x-demo-role": demoMode ? rolDemo : "",
                "x-demo-cliente-id": "demo-cliente"
              }
            : {})
        },
        body: body ? JSON.stringify(body) : undefined
      });

      const payload = await parseResponse(response);
      setMessage(`Estado actualizado a ${payload?.estado ?? "desconocido"}.`);
      window.location.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Operacion fallida");
    } finally {
      setIsRunning(false);
    }
  }

  const puedeCalcular = estado === "COMPLETA";
  const puedeValidar = estado === "PENDIENTE_VALIDACION_LIDER" && (!demoMode || rolDemo === "lider");
  const puedeAceptar = estado === "PENDIENTE_ACEPTACION_CLIENTE" && (!demoMode || rolDemo === "cliente");
  const puedeEntregar = (estado === "ACEPTADA" || estado === "EN_EJECUCION") && (!demoMode || rolDemo === "lider");

  return (
    <section className="story-actions">
      <h2>Acciones</h2>
      {demoMode ? (
        <label className="story-label" htmlFor="rolDemo">
          Rol demo
          <select
            id="rolDemo"
            value={rolDemo}
            onChange={(event) => setRolDemo(event.target.value as "cliente" | "lider")}
            className="story-input"
          >
            <option value="lider">Lider</option>
            <option value="cliente">Cliente</option>
          </select>
        </label>
      ) : null}
      <div className="story-action-grid">
        <button
          type="button"
          className="story-button"
            onClick={() => void runAction(`/api/historias/${historiaId}/calcular-sizing`)}
            disabled={isRunning || !puedeCalcular}
          >
            Calcular sizing
          </button>
        <button
          type="button"
          className="story-button"
          onClick={() => void runAction(`/api/historias/${historiaId}/validar`, { aprobado: liderAprueba })}
          disabled={isRunning || !puedeValidar}
        >
          {liderAprueba ? "Aprobar sizing" : "Corregir sizing"}
        </button>
        <label className="story-check">
          <input
            type="checkbox"
            checked={liderAprueba}
            onChange={(event) => setLiderAprueba(event.target.checked)}
          />
          Lider aprueba
        </label>
        <button
          type="button"
          className="story-button"
          onClick={() => void runAction(`/api/historias/${historiaId}/aceptar`, { aceptado: clienteAcepta })}
          disabled={isRunning || !puedeAceptar}
        >
          {clienteAcepta ? "Aceptar" : "Rechazar"}
        </button>
        <label className="story-check">
          <input
            type="checkbox"
            checked={clienteAcepta}
            onChange={(event) => setClienteAcepta(event.target.checked)}
          />
          Cliente acepta
        </label>
        <button
          type="button"
          className="story-button"
          onClick={() => void runAction(`/api/historias/${historiaId}/entregar`)}
          disabled={isRunning || !puedeEntregar}
        >
          Entregar
        </button>
      </div>
      {message ? <p className="story-message">{message}</p> : null}
      {error ? <p className="story-error">{error}</p> : null}
    </section>
  );
}
