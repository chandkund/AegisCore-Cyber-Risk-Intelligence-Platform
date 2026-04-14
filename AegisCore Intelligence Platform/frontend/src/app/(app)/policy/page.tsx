"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { createPolicyRule, evaluatePolicies, listPolicyRules } from "@/lib/api";
import type { PolicyRuleOut, PolicyViolation } from "@/types/api";

export default function PolicyPage() {
  const [rules, setRules] = useState<PolicyRuleOut[]>([]);
  const [violations, setViolations] = useState<PolicyViolation[]>([]);
  const [name, setName] = useState("Internet-facing high risk escalation");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    const [r, v] = await Promise.all([listPolicyRules(), evaluatePolicies()]);
    setRules(r ?? []);
    setViolations(v ?? []);
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function addDefaultRule() {
    setBusy(true);
    await createPolicyRule({
      name,
      conditions: { min_risk_score: 70, is_external: true, status_in: ["OPEN", "IN_PROGRESS"] },
      action: "escalate",
      severity: "HIGH",
      is_enabled: true,
    });
    setBusy(false);
    await refresh();
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-100">Policy guardrails</h2>
      <Card title="Create rule">
        <div className="flex flex-col gap-3 sm:flex-row">
          <Input value={name} onChange={(e) => setName(e.target.value)} />
          <Button type="button" onClick={() => void addDefaultRule()} disabled={busy}>
            {busy ? "Saving..." : "Add default rule"}
          </Button>
        </div>
      </Card>
      <Card title="Configured rules">
        <ul className="space-y-2 text-sm">
          {rules.map((r) => (
            <li key={r.id} className="rounded border border-slate-800 p-2 text-slate-300">
              <span className="font-medium text-slate-100">{r.name}</span> · {r.action} · {r.severity}
            </li>
          ))}
          {!rules.length ? <li className="text-slate-500">No policy rules found.</li> : null}
        </ul>
      </Card>
      <Card title="Current violations">
        <ul className="space-y-2 text-sm">
          {violations.map((v, idx) => (
            <li key={`${v.finding_id}-${idx}`} className="rounded border border-slate-800 p-2 text-slate-300">
              <span className="font-medium text-slate-100">{v.policy_name}</span> → finding {v.finding_id}
            </li>
          ))}
          {!violations.length ? <li className="text-slate-500">No violations right now.</li> : null}
        </ul>
      </Card>
    </div>
  );
}
