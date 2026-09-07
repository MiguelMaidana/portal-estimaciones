"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import { createSupabaseBrowserClient } from "../../lib/supabase/browser";

export function LoginForm() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setIsSubmitting(true);

    try {
      const supabase = createSupabaseBrowserClient();
      const { error: signInError } = await supabase.auth.signInWithOtp({
        email,
        options: {
          emailRedirectTo: `${window.location.origin}/`,
        },
      });

      if (signInError) {
        setError(signInError.message);
        return;
      }

      setMessage("Revisá tu correo para completar el ingreso.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo iniciar sesión.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="login-form">
      <label className="login-label" htmlFor="email">
        Correo
      </label>
      <input
        id="email"
        type="email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        className="login-input"
        placeholder="usuario@empresa.com"
        autoComplete="email"
        required
      />
      <button type="submit" className="login-button" disabled={isSubmitting}>
        {isSubmitting ? "Enviando..." : "Enviar enlace de acceso"}
      </button>
      {message ? <p className="login-message">{message}</p> : null}
      {error ? <p className="login-error">{error}</p> : null}
    </form>
  );
}
