"use client";

import Link from "next/link";
import type { FormEvent } from "react";
import { useState } from "react";

interface NuevaHistoriaFormProps {
  demoMode: boolean;
  clienteId: string;
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
              "x-demo-cliente-id": clienteId
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
  );
}
