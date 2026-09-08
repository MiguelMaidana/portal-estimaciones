"use client";

import { useState } from "react";
import { DEMO_CLIENT_ID } from "../../server/demo";

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

function actionHint(estado: HistoriaEstado) {
  if (estado === "COMPLETA") {
    return "La historia ya puede pasar a sizing.";
  }

  if (estado === "PENDIENTE_VALIDACION_LIDER") {
    return "La historia espera revisión del líder.";
  }

  if (estado === "PENDIENTE_ACEPTACION_CLIENTE") {
    return "El siguiente paso es la decisión del cliente.";
  }

  if (estado === "ACEPTADA" || estado === "EN_EJECUCION") {
    return "La historia quedó lista para cierre operativo.";
  }

  if (estado === "INCOMPLETA") {
    return "Hace falta reenviar la historia corregida.";
  }

  return "No hay una acción directa disponible para este estado.";
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
                "x-demo-user-id": `${rolDemo}-user`,
                "x-demo-role": rolDemo,
                "x-demo-cliente-id": DEMO_CLIENT_ID
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
    <section className="story-actions" id="acciones">
      <div className="section-heading">
        <h2>Acciones</h2>
        <p>{actionHint(estado)}</p>
      </div>

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
        <div className="action-card">
          <button
            type="button"
            className="story-button"
            onClick={() => void runAction(`/api/historias/${historiaId}/calcular-sizing`)}
            disabled={isRunning || !puedeCalcular}
          >
            Calcular sizing
          </button>
          <p>Disponible cuando la historia está completa.</p>
        </div>

        <div className="action-card">
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
        </div>

        <div className="action-card">
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
        </div>

        <div className="action-card">
          <button
            type="button"
            className="story-button"
            onClick={() => void runAction(`/api/historias/${historiaId}/entregar`)}
            disabled={isRunning || !puedeEntregar}
          >
            Entregar
          </button>
          <p>Marca el cierre operativo cuando la historia ya fue aceptada o está en ejecución.</p>
        </div>
      </div>

      {message ? <p className="story-message">{message}</p> : null}
      {error ? <p className="story-error">{error}</p> : null}
    </section>
  );
}
