"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/findings", label: "Findings" },
  { href: "/assets", label: "Assets" },
  { href: "/analytics", label: "Analytics" },
  { href: "/ml", label: "ML insights" },
];

function NavLink({
  href,
  label,
  onNavigate,
}: {
  href: string;
  label: string;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
  return (
    <Link
      href={href}
      onClick={onNavigate}
      className={cn(
        "block rounded-lg px-3 py-2 text-sm font-medium transition-colors",
        active
          ? "bg-slate-800 text-sky-300"
          : "text-slate-300 hover:bg-slate-800/80 hover:text-white"
      )}
    >
      {label}
    </Link>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout, hasRole } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const closeMenu = () => setMenuOpen(false);

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <a
        href="#main-content"
        className="sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:m-0 focus:inline-block focus:h-auto focus:w-auto focus:overflow-visible focus:whitespace-normal focus:rounded focus:bg-sky-600 focus:px-3 focus:py-2 focus:text-white"
      >
        Skip to content
      </a>
      <header className="border-b border-slate-800 bg-slate-950/95 md:hidden">
        <div className="flex items-center justify-between px-4 py-3">
          <span className="font-semibold text-slate-100">VulnOps</span>
          <Button
            type="button"
            variant="secondary"
            aria-expanded={menuOpen}
            aria-controls="mobile-nav"
            onClick={() => setMenuOpen((o) => !o)}
          >
            Menu
          </Button>
        </div>
        {menuOpen ? (
          <nav
            id="mobile-nav"
            className="border-t border-slate-800 px-2 pb-3 pt-1"
            aria-label="Primary"
          >
            {nav.map((item) => (
              <NavLink key={item.href} {...item} onNavigate={closeMenu} />
            ))}
            {hasRole("admin") ? (
              <NavLink href="/admin/users" label="Users" onNavigate={closeMenu} />
            ) : null}
          </nav>
        ) : null}
      </header>

      <aside
        className="hidden w-56 shrink-0 border-r border-slate-800 bg-slate-950/80 md:block"
        aria-label="Sidebar"
      >
        <div className="flex h-full flex-col p-4">
          <div className="mb-6 text-lg font-bold tracking-tight text-sky-400">
            VulnOps
          </div>
          <nav className="flex flex-1 flex-col gap-1" aria-label="Primary">
            {nav.map((item) => (
              <NavLink key={item.href} {...item} />
            ))}
            {hasRole("admin") ? (
              <NavLink href="/admin/users" label="Users" />
            ) : null}
          </nav>
          <div className="mt-6 border-t border-slate-800 pt-4 text-xs text-slate-500">
            <p className="truncate font-medium text-slate-300">{user?.full_name}</p>
            <p className="truncate">{user?.email}</p>
            <p className="mt-1 text-slate-500">{user?.roles?.join(", ")}</p>
            <Button
              type="button"
              variant="ghost"
              className="mt-3 w-full justify-start px-0 text-left"
              onClick={() => void logout()}
            >
              Sign out
            </Button>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="hidden border-b border-slate-800 bg-slate-950/60 px-6 py-4 md:block">
          <div className="flex items-center justify-between gap-4">
            <h1 className="text-xl font-semibold text-slate-100">Intelligence</h1>
            <div className="flex items-center gap-3 text-sm text-slate-400">
              <span className="hidden lg:inline">{user?.email}</span>
              <Button type="button" variant="secondary" onClick={() => void logout()}>
                Sign out
              </Button>
            </div>
          </div>
        </header>
        <main id="main-content" className="flex-1 p-4 md:p-6" tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  );
}
