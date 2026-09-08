"use client";

import Link from "next/link";
import type { FormEvent } from "react";
import { useState } from "react";
import { Card } from "../ui/Card";
import { DEMO_CLIENT_ID } from "../../server/demo";

interface NuevaHistoriaFormProps {
  demoMode: boolean;
  clienteId: string;
}

function evaluarHistoria(texto: string) {
  const limpio = texto.trim().toLowerCase();
  const tieneFormatoBase = limpio.includes("como") && limpio.includes("quiero") && limpio.includes("para");
  const tieneCuerpo = limpio.length >= 80;

  if (!limpio) {
    return {
      tone: "rojo",
      titulo: "Todavia esta vacia",
      descripcion: "Escribe la historia antes de evaluar cualquier cosa."
    };
  }

  if (tieneFormatoBase && tieneCuerpo) {
    return {
      tone: "verde",
      titulo: "Lista para analisis",
      descripcion: "Ya tiene forma de historia y puede pasar al flujo de calidad."
    };
  }

  if (tieneFormatoBase || tieneCuerpo) {
    return {
      tone: "amber",
      titulo: "Casi lista",
      descripcion: "Se entiende la base, pero aun falta detalle para entrar limpia al analisis."
    };
  }

  return {
    tone: "rojo",
    titulo: "Necesita reescritura",
    descripcion: "No aparece una historia clara todavia."
  };
}

export function NuevaHistoriaForm({ demoMode, clienteId }: NuevaHistoriaFormProps) {
  const [textoOriginal, setTextoOriginal] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [createdId, setCreatedId] = useState<string | null>(null);

  const analisis = evaluarHistoria(textoOriginal);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setIsSubmitting(true);

    try {
      const formData = new FormData();
      formData.set("clienteId", clienteId);
      formData.set("textoOriginal", textoOriginal);
      formData.set("textoOcr", "");
      formData.set("contieneContenidoOcr", "false");

      const response = await fetch("/api/historias", {
        method: "POST",
        body: formData,
        headers: demoMode
          ? {
              "x-demo-mode": "1",
              "x-demo-user-id": "demo-user",
              "x-demo-role": "cliente",
              "x-demo-cliente-id": clienteId || DEMO_CLIENT_ID
            }
          : undefined
      });

      const payload = (await response.json()) as
        | { id?: string; estado?: string; error?: { message?: string } }
        | undefined;

      if (!response.ok) {
        setError(payload?.error?.message ?? "No se pudo crear la historia.");
        return;
      }

      setMessage(`Historia creada (${payload?.id ?? "sin id"}) en estado ${payload?.estado ?? "desconocido"}.`);
      setCreatedId(payload?.id ?? null);
      setTextoOriginal("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo crear la historia.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="story-workbench">
      <Card className="card--accent story-workbench-main">
        <div className="section-heading">
          <span className="pill pill-blue">Historia de usuario</span>
          <h2>Redaccion y carga</h2>
          <p>Una sola historia a la vez. La evaluacion inicial se ve a la derecha y te marca si ya tiene forma suficiente.</p>
        </div>

        <form onSubmit={handleSubmit} className="story-form">
          <label className="story-label" htmlFor="textoOriginal">
            Historia
          </label>
          <textarea
            id="textoOriginal"
            value={textoOriginal}
            onChange={(event) => setTextoOriginal(event.target.value)}
            className="story-textarea story-textarea--large"
            placeholder="Como cliente quiero ... para ..."
            rows={12}
            required
          />

          <button type="submit" className="story-button" disabled={isSubmitting}>
            {isSubmitting ? "Enviando..." : "Enviar a evaluación"}
          </button>

          {demoMode ? <p className="story-note">Modo demo activo: la API usa headers de desarrollo.</p> : null}
          {createdId ? (
            <p className="story-message">
              <Link href={`/historias/${createdId}${demoMode ? "?demo=1" : ""}`}>Ver historia creada</Link>
            </p>
          ) : null}
          {message ? <p className="story-message">{message}</p> : null}
          {error ? <p className="story-error">{error}</p> : null}
        </form>
      </Card>

      <div className="story-workbench-side">
        <Card className="card--accent">
          <div className="section-heading">
            <span className="pill pill-amber">Evaluador tecnico</span>
            <h2>Primer analisis</h2>
            <p>Este es el control rapido previo a calidad. No reemplaza el sizing, solo decide si la historia entra al flujo.</p>
          </div>

          <div className={`signal-banner signal-banner--${analisis.tone}`}>
            <div className="signal-dot" />
            <div>
              <strong>{analisis.titulo}</strong>
              <span>{analisis.descripcion}</span>
            </div>
          </div>

          <div className="signal-grid signal-grid--compact">
            <div className="signal-card">
              <span>Historia</span>
              <strong>{textoOriginal.trim() ? "Cargada" : "Pendiente"}</strong>
              <p>La historia es la unica entrada de esta version.</p>
            </div>
            <div className="signal-card">
              <span>Estructura</span>
              <strong>{textoOriginal.toLowerCase().includes("como") && textoOriginal.toLowerCase().includes("quiero") && textoOriginal.toLowerCase().includes("para") ? "Base reconocible" : "Aun difusa"}</strong>
              <p>Buscamos una narracion clara, no un checklist tecnico.</p>
            </div>
            <div className="signal-card">
              <span>Salida esperada</span>
              <strong>{analisis.tone === "verde" ? "Pasa a calidad" : "Pide ajuste"}</strong>
              <p>Si entra, la siguiente pantalla toma el relevo con calidad y sizing.</p>
            </div>
          </div>
          <div className="callout callout-info" style={{ marginTop: 14 }}>
            <strong>Siguiente paso</strong>
            <span>{analisis.tone === "verde" ? "Pasar al detalle para calidad y sizing." : "Ajustar la historia antes de continuar."}</span>
          </div>
        </Card>
      </div>
    </div>
  );
}
