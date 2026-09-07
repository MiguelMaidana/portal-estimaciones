import "../styles/globals.css";
import "../styles/tokens.css";
import Link from "next/link";
import type { ReactNode } from "react";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <body>
        <div className="app-shell">
          <header className="app-topbar">
            <div className="app-brand">
              <span className="app-brand-mark">PE</span>
              <div>
                <div>Portal Estimaciones</div>
                <small>POC para sizing asistido por IA</small>
              </div>
            </div>
            <nav className="app-nav" aria-label="Navegacion principal">
              <Link href="/login">Ingresar</Link>
              <Link href="/historias/nueva?demo=1">Nueva historia</Link>
              <Link href="/lider">Lider</Link>
              <Link href="/consumo">Consumo</Link>
            </nav>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
