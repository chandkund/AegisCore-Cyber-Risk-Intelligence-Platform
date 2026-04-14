"use client";

import Link from "next/link";
import { Card } from "@/components/ui/Card";

const links = [
  { href: "/policy", title: "Policy guardrails", desc: "Define and evaluate policy-as-code rules." },
  { href: "/jobs", title: "Background jobs", desc: "Queue and monitor heavy platform workflows." },
  { href: "/compliance", title: "Compliance exports", desc: "Review SLA/compliance posture and clusters." },
];

export default function OperationsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-100">Operations</h2>
        <p className="mt-1 text-slate-400">Platform governance, automation, and compliance workflows.</p>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {links.map((item) => (
          <Card key={item.href} title={item.title}>
            <p className="mb-3 text-sm text-slate-400">{item.desc}</p>
            <Link href={item.href} className="text-sm text-sky-400 hover:underline">
              Open →
            </Link>
          </Card>
        ))}
      </div>
    </div>
  );
}
