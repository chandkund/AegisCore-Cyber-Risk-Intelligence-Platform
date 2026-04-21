"use client";

import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/components/auth/AuthProvider";
import {
  Building,
  CloudUpload,
  Database,
  ShieldCheck,
  PieChart,
} from "lucide-react";

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navItems: NavItem[] = [
  { href: "/platform", label: "Overview", icon: PieChart },
  { href: "/platform/tenants", label: "Companies", icon: Building },
  { href: "/platform/uploads", label: "Uploads", icon: CloudUpload },
  { href: "/platform/storage", label: "Storage", icon: Database },
  { href: "/platform/compliance", label: "Compliance", icon: ShieldCheck },
];

export default function PlatformLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { hasRole } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  // Only platform_owner can access this section
  if (!hasRole("platform_owner")) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <h1 className="text-xl font-semibold text-rose-400">Access Denied</h1>
          <p className="mt-2 text-slate-400">
            You do not have permission to access the platform management area.
          </p>
          <button
            onClick={() => router.push("/dashboard")}
            className="mt-4 text-indigo-400 hover:text-indigo-300"
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    );
  }

  // Check if the current path is an exact match or starts with the href
  function isActive(href: string): boolean {
    if (href === "/platform") {
      return pathname === "/platform";
    }
    return pathname.startsWith(href);
  }

  return (
    <div className="flex min-h-screen">
      {/* Sidebar Navigation */}
      <aside className="w-64 bg-slate-900 border-r border-slate-800">
        <div className="p-4">
          <div className="flex items-center gap-2 mb-6">
            <div className="h-8 w-8 rounded-lg bg-indigo-500/20 flex items-center justify-center">
              <span className="text-indigo-400 font-bold text-sm">P</span>
            </div>
            <h1 className="text-lg font-semibold text-slate-100">Platform</h1>
          </div>

          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.href);
              return (
                <button
                  key={item.href}
                  onClick={() => router.push(item.href)}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    active
                      ? "bg-indigo-500/10 text-indigo-400"
                      : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  {item.label}
                </button>
              );
            })}
          </nav>
        </div>

        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-slate-800">
          <button
            onClick={() => router.push("/dashboard")}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Exit Platform
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto bg-slate-950">
        <div className="p-6 max-w-7xl mx-auto">{children}</div>
      </main>
    </div>
  );
}
