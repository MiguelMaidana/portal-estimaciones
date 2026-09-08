"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/login", label: "Ingresar" },
  { href: "/historias/nueva?demo=1", label: "Nueva historia" },
  { href: "/lider", label: "Lider" },
  { href: "/consumo", label: "Consumo" }
];

export function AppHeader() {
  const pathname = usePathname();

  return (
    <header className="app-topbar">
      <div className="app-topbar-inner">
        <div className="app-brand">
          <span className="app-brand-mark">PE</span>
          <div className="app-brand-copy">
            <div className="app-brand-title">Portal Estimaciones</div>
            <small>POC para sizing asistido por IA</small>
          </div>
        </div>

        <nav className="app-nav" aria-label="Navegacion principal">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href.split("?")[0];

            return (
              <Link key={item.href} href={item.href} data-active={active ? "true" : "false"}>
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
