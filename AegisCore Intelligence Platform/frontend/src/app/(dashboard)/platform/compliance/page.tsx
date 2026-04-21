"use client";

import { useEffect, useState } from "react";
import { usePlatformOwner } from "@/hooks/use-platform-owner";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Progress } from "@/components/ui/Progress";
import { AlertCircle, CheckCircle, Shield, RefreshCw, FileText, Lock, Eye } from "lucide-react";
import { platformGetSecurityScore, platformGetSecurityEvents, platformGetComplianceFrameworks, platformRecalculateCompliance } from "@/lib/api-compliance";

interface SecurityDetail {
  category: string;
  score: number;
  max_score: number;
  status: "pass" | "warn" | "fail";
  findings: string[];
}

interface SecurityScore {
  overall_score: number;
  max_score: number;
  grade: string;
  last_updated: string;
  details: SecurityDetail[];
}

interface ComplianceFramework {
  framework: string;
  readiness: "ready" | "in_progress" | "not_applicable";
  completion_percentage: number;
  gaps: string[];
  last_assessment: string | null;
}

interface SecurityEvents {
  period: string;
  total_events: number;
  critical_events: number;
  failed_logins: number;
  blocked_requests: number;
}

export default function CompliancePage() {
  const { isLoading: authLoading, isPlatformOwner } = usePlatformOwner();
  const [score, setScore] = useState<SecurityScore | null>(null);
  const [events, setEvents] = useState<SecurityEvents | null>(null);
  const [frameworks, setFrameworks] = useState<ComplianceFramework[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [scoreData, eventsData, frameworksData] = await Promise.all([
        platformGetSecurityScore(),
        platformGetSecurityEvents(7),
        platformGetComplianceFrameworks(),
      ]);
      setScore(scoreData);
      setEvents(eventsData);
      setFrameworks(frameworksData);
    } catch (err) {
      setError("Failed to load compliance data");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleRecalculate = async () => {
    setLoading(true);
    try {
      await platformRecalculateCompliance();
      await loadData();
    } catch (err) {
      setError("Failed to recalculate compliance scores");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (authLoading || loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (!isPlatformOwner) {
    return (
      <div className="p-8">
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
          <div className="flex items-center gap-2 font-semibold">
            <AlertCircle className="h-4 w-4" />
            Access Denied
          </div>
          <p className="mt-1 text-sm">
            Only platform owners can access the compliance dashboard.
          </p>
        </div>
      </div>
    );
  }

  const getGradeColor = (grade: string) => {
    if (grade.startsWith("A")) return "bg-green-500";
    if (grade === "B") return "bg-blue-500";
    if (grade === "C") return "bg-yellow-500";
    if (grade === "D") return "bg-orange-500";
    return "bg-red-500";
  };

  const getStatusIcon = (status: string) => {
    if (status === "pass") return <CheckCircle className="h-5 w-5 text-green-500" />;
    if (status === "warn") return <AlertCircle className="h-5 w-5 text-yellow-500" />;
    return <AlertCircle className="h-5 w-5 text-red-500" />;
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Security Compliance</h1>
          <p className="text-muted-foreground">
            Enterprise security posture and compliance framework status
          </p>
        </div>
        <Button onClick={handleRecalculate} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Recalculate
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
          <div className="flex items-center gap-2 font-semibold">
            <AlertCircle className="h-4 w-4" />
            Error
          </div>
          <p className="mt-1 text-sm">{error}</p>
        </div>
      )}

      {/* Overall Score */}
      {score && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Overall Security Score
            </CardTitle>
            <CardDescription>
              Last updated: {new Date(score.last_updated).toLocaleString()}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-6">
              <div className={`w-24 h-24 rounded-full flex items-center justify-center text-white text-3xl font-bold ${getGradeColor(score.grade)}`}>
                {score.grade}
              </div>
              <div className="flex-1 space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span>Score</span>
                  <span className="font-medium">{score.overall_score} / {score.max_score}</span>
                </div>
                <Progress value={(score.overall_score / score.max_score) * 100} className="h-3" />
                <p className="text-sm text-muted-foreground">
                  {score.overall_score >= 95 ? "Excellent security posture" :
                   score.overall_score >= 85 ? "Good security posture with minor improvements needed" :
                   score.overall_score >= 70 ? "Security improvements required" :
                   "Critical security issues detected"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Security Events */}
      {events && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Total Events</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{events.total_events.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground">Last {events.period}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Critical Events</CardTitle>
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${events.critical_events > 0 ? "text-red-600" : ""}`}>
                {events.critical_events.toLocaleString()}
              </div>
              <p className="text-xs text-muted-foreground">Requiring attention</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Failed Logins</CardTitle>
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${events.failed_logins > 100 ? "text-yellow-600" : ""}`}>
                {events.failed_logins.toLocaleString()}
              </div>
              <p className="text-xs text-muted-foreground">Brute force attempts</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Blocked Requests</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{events.blocked_requests.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground">By WAF / Rate limiting</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Category Details */}
      {score && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {score.details.map((detail) => (
            <Card key={detail.category}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base flex items-center gap-2">
                    {getStatusIcon(detail.status)}
                    {detail.category}
                  </CardTitle>
                  <Badge variant={detail.status === "pass" ? "default" : detail.status === "warn" ? "secondary" : "destructive"}>
                    {detail.score} / {detail.max_score}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <Progress 
                  value={(detail.score / detail.max_score) * 100} 
                  className="h-2 mb-3"
                />
                <ul className="text-sm space-y-1">
                  {detail.findings.map((finding, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      {finding.includes("Enabled") || finding.includes("active") || finding.includes("success") ? (
                        <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-yellow-500 mt-0.5 shrink-0" />
                      )}
                      <span className={finding.includes("not") || finding.includes("pending") || finding.includes("No ") ? "text-yellow-700" : "text-muted-foreground"}>
                        {finding}
                      </span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Compliance Frameworks */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {frameworks.map((framework) => (
          <Card key={framework.framework}>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm">{framework.framework}</CardTitle>
                <Badge 
                  variant={
                    framework.readiness === "ready" ? "default" :
                    framework.readiness === "in_progress" ? "secondary" : "outline"
                  }
                >
                  {framework.readiness.replace("_", " ")}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span>Completion</span>
                    <span>{framework.completion_percentage.toFixed(0)}%</span>
                  </div>
                  <Progress value={framework.completion_percentage} className="h-2" />
                </div>
                {framework.gaps.length > 0 && (
                  <div className="text-xs">
                    <p className="text-muted-foreground mb-1">Gaps:</p>
                    <ul className="space-y-0.5 text-red-600">
                      {framework.gaps.map((gap, idx) => (
                        <li key={idx}>{gap}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {framework.last_assessment && (
                  <p className="text-xs text-muted-foreground">
                    Assessed: {new Date(framework.last_assessment).toLocaleDateString()}
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Documentation Links */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Compliance Documentation
          </CardTitle>
          <CardDescription>
            Review security policies and compliance documentation
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <a 
              href="/docs/compliance/SOC2_READINESS.md" 
              className="flex items-center gap-3 p-4 rounded-lg border hover:bg-muted transition-colors"
            >
              <Shield className="h-5 w-5 text-blue-500" />
              <div>
                <p className="font-medium">SOC 2 Readiness</p>
                <p className="text-sm text-muted-foreground">Trust Services Criteria mapping</p>
              </div>
            </a>
            <a 
              href="/docs/compliance/DATABASE_ENCRYPTION.md" 
              className="flex items-center gap-3 p-4 rounded-lg border hover:bg-muted transition-colors"
            >
              <Lock className="h-5 w-5 text-green-500" />
              <div>
                <p className="font-medium">Database Encryption</p>
                <p className="text-sm text-muted-foreground">TDE and KMS configuration</p>
              </div>
            </a>
            <a 
              href="/docs/runbooks/credential-rotation.md" 
              className="flex items-center gap-3 p-4 rounded-lg border hover:bg-muted transition-colors"
            >
              <Eye className="h-5 w-5 text-purple-500" />
              <div>
                <p className="font-medium">Credential Rotation</p>
                <p className="text-sm text-muted-foreground">Key rotation procedures</p>
              </div>
            </a>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
