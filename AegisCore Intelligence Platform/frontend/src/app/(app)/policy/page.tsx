"use client";

import { useEffect, useState } from "react";
import { Shield, AlertTriangle, Plus, Gavel, FileText, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { createPolicyRule, evaluatePolicies, listPolicyRules } from "@/lib/api";
import type { PolicyRuleOut, PolicyViolation } from "@/types/api";

export default function PolicyPage() {
  const [rules, setRules] = useState<PolicyRuleOut[]>([]);
  const [violations, setViolations] = useState<PolicyViolation[]>([]);
  const [name, setName] = useState("Internet-facing high risk escalation");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [r, v] = await Promise.all([listPolicyRules(), evaluatePolicies()]);
      setRules(r ?? []);
      setViolations(v ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load policy data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function addDefaultRule() {
    setBusy(true);
    try {
      await createPolicyRule({
        name,
        conditions: { min_risk_score: 70, is_external: true, status_in: ["OPEN", "IN_PROGRESS"] },
        action: "escalate",
        severity: "HIGH",
        is_enabled: true,
      });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create rule");
    } finally {
      setBusy(false);
    }
  }

  if (error && !rules.length) {
    return (
      <div className="space-y-6">
        <PageHeader title="Policy Guardrails" description="Automated policy enforcement and compliance rules" />
        <ErrorState title="Failed to load policies" message={error} onRetry={refresh} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Policy Guardrails" description="Automated policy enforcement and compliance rules" />

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <Card title="Active Rules" className="text-center">
          <div className="flex items-center justify-center gap-2">
            <Shield className="w-5 h-5 text-emerald-500" />
            <span className="text-2xl font-bold text-slate-100">{rules.filter(r => r.is_enabled).length}</span>
          </div>
        </Card>
        <Card title="Total Rules" className="text-center">
          <div className="flex items-center justify-center gap-2">
            <Gavel className="w-5 h-5 text-sky-500" />
            <span className="text-2xl font-bold text-slate-100">{rules.length}</span>
          </div>
        </Card>
        <Card title="Violations" className="text-center">
          <div className="flex items-center justify-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            <span className="text-2xl font-bold text-slate-100">{violations.length}</span>
          </div>
        </Card>
      </div>

      {/* Create Rule */}
      <Card title="Create Policy Rule">
        <div className="flex flex-col gap-3 sm:flex-row">
          <Input 
            value={name} 
            onChange={(e) => setName(e.target.value)} 
            placeholder="Rule name..."
            className="flex-1"
          />
          <Button 
            onClick={() => void addDefaultRule()} 
            disabled={busy || !name.trim()}
            className="gap-2"
          >
            <Plus className="w-4 h-4" />
            {busy ? "Saving..." : "Add Rule"}
          </Button>
        </div>
      </Card>

      {/* Rules Table */}
      <Card title="Configured Rules" className={loading ? "opacity-70" : ""}>
        {loading && !rules.length ? (
          <div className="space-y-3">
            <div className="h-12 animate-pulse bg-slate-800/50 rounded" />
            <div className="h-12 animate-pulse bg-slate-800/50 rounded" />
          </div>
        ) : rules.length > 0 ? (
          <DataTable
            columns={[
              { key: "name", header: "Rule Name", sortable: true, cell: (row) => row.name },
              { key: "action", header: "Action", sortable: true, cell: (row) => (
                <span className="inline-flex items-center gap-1.5">
                  <Badge tone={row.action === "escalate" ? "CRITICAL" : "INFO"}>{row.action}</Badge>
                </span>
              )},
              { key: "severity", header: "Severity", sortable: true, cell: (row) => (
                <Badge tone={row.severity}>{row.severity}</Badge>
              )},
              { key: "status", header: "Status", sortable: true, cell: (row) => (
                <span className={`inline-flex items-center gap-1.5 text-sm ${row.is_enabled ? "text-emerald-400" : "text-slate-500"}`}>
                  {row.is_enabled ? <CheckCircle className="w-4 h-4" /> : <Shield className="w-4 h-4" />}
                  {row.is_enabled ? "Active" : "Disabled"}
                </span>
              )},
            ]}
            data={rules.map(r => ({ ...r, id: r.id }))}
            keyExtractor={(row) => row.id}
            sortable
          />
        ) : (
          <EmptyState
            title="No policy rules"
            description="Create your first policy rule to enforce compliance"
            icon={<Shield className="w-10 h-10" />}
          />
        )}
      </Card>

      {/* Violations Table */}
      <Card title="Current Violations" className={loading ? "opacity-70" : ""}>
        {loading && !violations.length ? (
          <div className="space-y-3">
            <div className="h-12 animate-pulse bg-slate-800/50 rounded" />
            <div className="h-12 animate-pulse bg-slate-800/50 rounded" />
          </div>
        ) : violations.length > 0 ? (
          <DataTable
            columns={[
              { key: "policy", header: "Policy", sortable: true, cell: (row) => row.policy_name },
              { key: "finding", header: "Finding ID", sortable: true, cell: (row) => (
                <span className="font-mono text-sm text-sky-400">{row.finding_id}</span>
              )},
              { key: "severity", header: "Severity", sortable: true, cell: (row) => (
                <Badge tone={row.severity}>{row.severity}</Badge>
              )},
            ]}
            data={violations.map((v, idx) => ({ ...v, id: `${v.finding_id}-${idx}` }))}
            keyExtractor={(row) => row.id}
            sortable
          />
        ) : (
          <EmptyState
            title="No violations"
            description="All findings are currently compliant with policies"
            icon={<CheckCircle className="w-10 h-10" />}
          />
        )}
      </Card>
    </div>
  );
}
