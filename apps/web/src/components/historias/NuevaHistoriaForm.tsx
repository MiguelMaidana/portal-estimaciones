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

function contarCoincidencias(texto: string) {
  const limpio = texto.toLowerCase();
  return ["como", "quiero", "para"].filter((fragmento) => limpio.includes(fragmento)).length;
}

export function NuevaHistoriaForm({ demoMode, clienteId }: NuevaHistoriaFormProps) {
  const [textoOriginal, setTextoOriginal] = useState("");
  const [textoOcr, setTextoOcr] = useState("");
  const [contieneContenidoOcr, setContieneContenidoOcr] = useState(false);
  const [imagenes, setImagenes] = useState<FileList | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [createdId, setCreatedId] = useState<string | null>(null);

  const historiaLimpia = textoOriginal.trim();
  const ocrLimpio = textoOcr.trim();
  const estructuraBase = contarCoincidencias(historiaLimpia);
  const calidadBase = [historiaLimpia.length >= 60, estructuraBase >= 2, historiaLimpia.length >= 140].filter(Boolean).length;
  const tonoSemaforo = calidadBase >= 3 ? "verde" : calidadBase >= 2 ? "amber" : "rojo";
  const semaforoTexto =
    tonoSemaforo === "verde"
      ? "Lista para pasar a evaluacion"
      : tonoSemaforo === "amber"
        ? "Aun necesita detalle"
        : "Todavia esta en captura";
  const detallesEvaluacion = [
    {
      label: "Historia de usuario",
      value: historiaLimpia ? "Redactada" : "Pendiente",
      note: historiaLimpia ? "Hay contenido para evaluar." : "Necesitamos el texto principal."
    },
    {
      label: "Estructura",
      value: estructuraBase >= 3 ? "Como / Quiero / Para" : estructuraBase === 2 ? "Parcial" : "Sin patron claro",
      note: estructuraBase >= 2 ? "El formato base ya aparece." : "Todavia falta la forma de historia."
    },
    {
      label: "OCR",
      value: contieneContenidoOcr || ocrLimpio ? "Con apoyo OCR" : "No aplica",
      note: ocrLimpio ? "Existe texto extraido para revisar manualmente." : "Si hay imagenes, el OCR se completa despues."
    },
    {
      label: "Adjuntos",
      value: imagenes?.length ? `${imagenes.length} imagen${imagenes.length === 1 ? "" : "es"}` : "Sin imagenes",
      note: "El soporte visual suma trazabilidad, no reemplaza la historia."
    }
  ];

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setIsSubmitting(true);

    try {
      const formData = new FormData();
      formData.set("clienteId", clienteId);
      formData.set("textoOriginal", textoOriginal);
      formData.set("textoOcr", textoOcr);
      formData.set("contieneContenidoOcr", String(contieneContenidoOcr));

      if (imagenes) {
        Array.from(imagenes).forEach((file) => {
          formData.append("imagenes", file);
        });
      }

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
      setTextoOcr("");
      setContieneContenidoOcr(false);
      setImagenes(null);
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
          <p>Una sola historia a la vez. El evaluador tecnico de la derecha te dice si ya tiene forma suficiente para entrar al flujo.</p>
        </div>

        <form onSubmit={handleSubmit} className="story-form">
          <label className="story-label" htmlFor="textoOriginal">
            Historia
          </label>
          <textarea
            id="textoOriginal"
            value={textoOriginal}
            onChange={(event) => setTextoOriginal(event.target.value)}
            className="story-textarea"
            placeholder="Como cliente quiero ... para ..."
            rows={8}
            required
          />

          <label className="story-label" htmlFor="textoOcr">
            Texto OCR
          </label>
          <textarea
            id="textoOcr"
            value={textoOcr}
            onChange={(event) => setTextoOcr(event.target.value)}
            className="story-textarea"
            placeholder="Texto extraido de imagenes, si aplica"
            rows={5}
          />

          <label className="story-check">
            <input
              type="checkbox"
              checked={contieneContenidoOcr}
              onChange={(event) => setContieneContenidoOcr(event.target.checked)}
            />
            La historia incluye OCR
          </label>

          <label className="story-label" htmlFor="imagenes">
            Imagenes
          </label>
          <input
            id="imagenes"
            type="file"
            accept="image/png,image/jpeg"
            multiple
            onChange={(event) => setImagenes(event.target.files)}
          />

          <button type="submit" className="story-button" disabled={isSubmitting}>
            {isSubmitting ? "Creando..." : "Crear historia"}
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
            <h2>Semaforo de calidad</h2>
            <p>Este panel no calcula el sizing final. Solo te dice si la historia ya esta lista para pasar a analisis.</p>
          </div>

          <div className={`signal-banner signal-banner--${tonoSemaforo}`}>
            <div className="signal-dot" />
            <div>
              <strong>{semaforoTexto}</strong>
              <span>El sizing queda bloqueado hasta que la historia este completa.</span>
            </div>
          </div>

          <div className="signal-grid">
            {detallesEvaluacion.map((item) => (
              <div key={item.label} className="signal-card">
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <p>{item.note}</p>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <div className="section-heading">
            <h2>Reglas de la carga</h2>
            <p>La pantalla esta pensada como una compuerta antes del flujo principal.</p>
          </div>
          <div className="summary-list">
            <div className="summary-row">
              <span>Entrada</span>
              <strong>Una historia por vez</strong>
            </div>
            <div className="summary-row">
              <span>OCR</span>
              <strong>Best effort con revision manual</strong>
            </div>
            <div className="summary-row">
              <span>Salida</span>
              <strong>Estado inicial del analisis</strong>
            </div>
            <div className="summary-row">
              <span>Sizing</span>
              <strong>Solo cuando calidad da verde</strong>
            </div>
          </div>
        </Card>

        <Card>
          <div className="section-heading">
            <h2>Definicion de la salida</h2>
            <p>Si la historia pasa, el flujo la toma para calidad, sizing y validacion.</p>
          </div>
          <div className="flow-mini">
            <div className="flow-mini-step">
              <span>01</span>
              <div>
                <strong>Captura</strong>
                <p>Se guarda texto, OCR e imagenes si existen.</p>
              </div>
            </div>
            <div className="flow-mini-step">
              <span>02</span>
              <div>
                <strong>Evaluacion</strong>
                <p>Se decide si pasa a completa o si vuelve con observaciones.</p>
              </div>
            </div>
            <div className="flow-mini-step">
              <span>03</span>
              <div>
                <strong>Sizing</strong>
                <p>Solo arranca cuando la historia queda completa.</p>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
