import "../styles/globals.css";
import "../styles/tokens.css";
import type { ReactNode } from "react";
import { AppHeader } from "../components/layout/AppHeader";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <body>
        <div className="app-shell">
          <AppHeader />
          {children}
        </div>
      </body>
    </html>
  );
}
