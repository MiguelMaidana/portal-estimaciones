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

async function parseResponse(response: Response) {
  const payload = (await response.json().catch(() => null)) as
    | { error?: { message?: string }; estado?: string }
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
  const rolRequerido = estado === "PENDIENTE_ACEPTACION_CLIENTE" ? "cliente" : "lider";

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
                "x-demo-user-id": `${rolRequerido}-user`,
                "x-demo-role": rolRequerido,
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

  const sinAccion = ![
    "COMPLETA",
    "PENDIENTE_VALIDACION_LIDER",
    "PENDIENTE_ACEPTACION_CLIENTE",
    "ACEPTADA",
    "EN_EJECUCION"
  ].includes(estado);

  return (
    <section className="story-actions" id="acciones">
      <div className="section-heading">
        <span className="pill pill-blue">Accion disponible</span>
        <h2>Siguiente decision</h2>
      </div>

      {estado === "COMPLETA" ? (
        <div className="action-primary">
          <strong>La calidad esta aprobada</strong>
          <p>Ejecuta el motor deterministico para obtener tamano y puntos.</p>
          <button type="button" className="story-button" onClick={() => void runAction(`/api/historias/${historiaId}/calcular-sizing`)} disabled={isRunning}>
            {isRunning ? "Calculando..." : "Calcular sizing"}
          </button>
        </div>
      ) : null}

      {estado === "PENDIENTE_VALIDACION_LIDER" ? (
        <div className="action-primary">
          <strong>Revision del lider</strong>
          <p>Confirma el resultado calculado o devuelvelo para correccion.</p>
          <label className="decision-toggle">
            <input type="checkbox" checked={liderAprueba} onChange={(event) => setLiderAprueba(event.target.checked)} />
            {liderAprueba ? "Aprobar resultado" : "Solicitar correccion"}
          </label>
          <button type="button" className="story-button" onClick={() => void runAction(`/api/historias/${historiaId}/validar`, { aprobado: liderAprueba })} disabled={isRunning}>
            {isRunning ? "Guardando..." : liderAprueba ? "Aprobar sizing" : "Enviar a correccion"}
          </button>
        </div>
      ) : null}

      {estado === "PENDIENTE_ACEPTACION_CLIENTE" ? (
        <div className="action-primary">
          <strong>Decision del cliente</strong>
          <p>Al aceptar, los puntos se descuentan de la linea base mensual.</p>
          <label className="decision-toggle">
            <input type="checkbox" checked={clienteAcepta} onChange={(event) => setClienteAcepta(event.target.checked)} />
            {clienteAcepta ? "Aceptar estimacion" : "Rechazar estimacion"}
          </label>
          <button type="button" className="story-button" onClick={() => void runAction(`/api/historias/${historiaId}/aceptar`, { aceptado: clienteAcepta })} disabled={isRunning}>
            {isRunning ? "Guardando..." : clienteAcepta ? "Aceptar estimacion" : "Rechazar estimacion"}
          </button>
        </div>
      ) : null}

      {estado === "ACEPTADA" || estado === "EN_EJECUCION" ? (
        <div className="action-primary">
          <strong>Cierre operativo</strong>
          <p>La estimacion ya fue aceptada. Marca la entrega cuando el trabajo este finalizado.</p>
          <button type="button" className="story-button" onClick={() => void runAction(`/api/historias/${historiaId}/entregar`)} disabled={isRunning}>
            {isRunning ? "Guardando..." : "Marcar como entregada"}
          </button>
        </div>
      ) : null}

      {sinAccion ? (
        <div className="empty-state">
          <strong>Sin acciones manuales ahora</strong>
          <span>La historia esta esperando otra etapa del flujo.</span>
        </div>
      ) : null}

      {demoMode ? <p className="story-note">Modo demo: la accion usa automaticamente el rol requerido.</p> : null}
      {message ? <p className="story-message">{message}</p> : null}
      {error ? <p className="story-error">{error}</p> : null}
    </section>
  );
}
