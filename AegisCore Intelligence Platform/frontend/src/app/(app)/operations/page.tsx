"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { 
  Shield, 
  Gavel, 
  FileText, 
  Upload, 
  BarChart3, 
  Clock, 
  AlertTriangle,
  Settings,
  ChevronRight
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { apiFetch } from "@/lib/api";

interface QuickStat {
  label: string;
  value: number | string;
  href: string;
  icon: React.ReactNode;
  badge?: string;
}

export default function OperationsPage() {
  const [quickStats, setQuickStats] = useState<QuickStat[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadStats() {
      setLoading(true);
      try {
        // Fetch summary stats from various endpoints
        const [summaryRes, jobsRes] = await Promise.all([
          apiFetch<{ open_findings?: number; overdue_findings?: number }>("/analytics/summary"),
          apiFetch<Array<{ status: string }>>("/jobs?limit=1"),
        ]);

        const stats: QuickStat[] = [];

        if (summaryRes.ok && summaryRes.data) {
          stats.push({
            label: "Open Findings",
            value: summaryRes.data.open_findings || 0,
            href: "/findings",
            icon: <FileText className="w-5 h-5 text-amber-500" />,
          });
          stats.push({
            label: "Overdue",
            value: summaryRes.data.overdue_findings || 0,
            href: "/compliance",
            icon: <AlertTriangle className="w-5 h-5 text-red-500" />,
            badge: summaryRes.data.overdue_findings ? "Action needed" : undefined,
          });
        }

        if (jobsRes.ok && jobsRes.data) {
          const runningJobs = jobsRes.data.filter(j => j.status === "RUNNING").length;
          stats.push({
            label: "Running Jobs",
            value: runningJobs,
            href: "/jobs",
            icon: <Clock className="w-5 h-5 text-sky-500" />,
            badge: runningJobs > 0 ? `${runningJobs} active` : undefined,
          });
        }

        setQuickStats(stats);
      } catch {
        // Silently fail - stats are optional
      } finally {
        setLoading(false);
      }
    }

    loadStats();
  }, []);

  const operationSections = [
    {
      title: "Governance & Compliance",
      description: "Policy enforcement, compliance tracking, and SLA monitoring",
      links: [
        { label: "Policy Guardrails", href: "/policy", icon: <Gavel className="w-4 h-4" />, desc: "Automated rules & violations" },
        { label: "Compliance Summary", href: "/compliance", icon: <Shield className="w-4 h-4" />, desc: "SLA metrics & root cause analysis" },
      ],
    },
    {
      title: "Data & Processing",
      description: "Data ingestion, background jobs, and system operations",
      links: [
        { label: "Upload Center", href: "/uploads", icon: <Upload className="w-4 h-4" />, desc: "Import vulnerability data" },
        { label: "Background Jobs", href: "/jobs", icon: <Clock className="w-4 h-4" />, desc: "Monitor async processing tasks" },
      ],
    },
    {
      title: "Analytics & Reporting",
      description: "Risk trends, metrics, and operational insights",
      links: [
        { label: "Analytics Dashboard", href: "/analytics", icon: <BarChart3 className="w-4 h-4" />, desc: "Detailed risk analysis" },
        { label: "Risk Overview", href: "/prioritized", icon: <AlertTriangle className="w-4 h-4" />, desc: "Prioritized vulnerabilities" },
      ],
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader 
        title="Operations Center" 
        description="Central hub for governance, data management, and system operations" 
      />

      {/* Quick Stats */}
      {quickStats.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {quickStats.map((stat) => (
            <Link key={stat.label} href={stat.href} className="block">
              <Card className="hover:border-sky-500/50 transition-colors cursor-pointer">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {stat.icon}
                    <div>
                      <div className="text-2xl font-bold text-slate-100">{stat.value}</div>
                      <div className="text-sm text-slate-400">{stat.label}</div>
                    </div>
                  </div>
                  {stat.badge && (
                    <Badge tone="CRITICAL">{stat.badge}</Badge>
                  )}
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}

      {/* Operation Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {operationSections.map((section) => (
          <Card key={section.title} title={section.title} className="h-full">
            <p className="text-sm text-slate-400 mb-4">{section.description}</p>
            <div className="space-y-2">
              {section.links.map((link) => (
                <Link
                  key={link.label}
                  href={link.href}
                  className="flex items-center gap-3 p-3 rounded-lg bg-slate-800/50 hover:bg-slate-800 transition-colors group"
                >
                  <span className="text-sky-400">{link.icon}</span>
                  <div className="flex-1">
                    <div className="text-slate-200 font-medium group-hover:text-sky-400 transition-colors">
                      {link.label}
                    </div>
                    <div className="text-xs text-slate-500">{link.desc}</div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-sky-400 transition-colors" />
                </Link>
              ))}
            </div>
          </Card>
        ))}
      </div>

      {/* System Status Footer */}
      <Card title="System Status" className="text-sm text-slate-400">
        <div className="flex flex-wrap gap-6">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>API Operational</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>Database Connected</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>Job Queue Active</span>
          </div>
        </div>
      </Card>
    </div>
  );
}
