"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/AuthProvider";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { uploadAssetsCsv, uploadVulnerabilitiesCsv, getUploadTemplate } from "@/lib/api";

interface UploadResult {
  success: boolean;
  message: string;
  summary: {
    total_rows: number;
    inserted: number;
    updated: number;
    failed: number;
    skipped: number;
    errors: Array<{
      row_number: number;
      field?: string;
      message: string;
    }>;
    processing_time_ms: number;
  };
}

export default function UploadPage() {
  const { hasRole } = useAuth();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"assets" | "vulnerabilities">("assets");
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Only admin and analyst roles can upload
  const canUpload = hasRole("admin") || hasRole("analyst");

  const handleUpload = useCallback(async (file: File) => {
    setUploading(true);
    setResult(null);
    setError(null);

    try {
      let response;
      if (activeTab === "assets") {
        response = await uploadAssetsCsv(file);
      } else {
        response = await uploadVulnerabilitiesCsv(file);
      }

      if (response.ok && response.data) {
        setResult(response.data);
      } else {
        setError(response.error || "Upload failed");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }, [activeTab]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      const files = e.dataTransfer.files;
      if (files.length > 0) {
        await handleUpload(files[0]);
      }
    },
    [handleUpload]
  );

  const handleFileSelect = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        await handleUpload(file);
      }
    },
    [handleUpload]
  );

  const downloadTemplate = async (type: "assets" | "vulnerabilities") => {
    try {
      const blob = await getUploadTemplate(type);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${type}_template.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError("Failed to download template");
    }
  };

  if (!canUpload) {
    return (
      <div className="rounded-lg bg-rose-500/10 p-4 text-rose-400">
        You do not have permission to upload data.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-100">Data Upload</h1>
        <Button variant="secondary" onClick={() => router.push("/admin")}>
          Back to Admin
        </Button>
      </div>

      <p className="text-slate-400">
        Upload CSV files to import assets and vulnerabilities. All data is
        automatically assigned to your company.
      </p>

      {/* Tab Selection */}
      <div className="flex gap-2 border-b border-slate-700">
        <button
          onClick={() => {
            setActiveTab("assets");
            setResult(null);
            setError(null);
          }}
          className={`px-4 py-2 text-sm font-medium ${
            activeTab === "assets"
              ? "border-b-2 border-cyan-500 text-cyan-400"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          Assets
        </button>
        <button
          onClick={() => {
            setActiveTab("vulnerabilities");
            setResult(null);
            setError(null);
          }}
          className={`px-4 py-2 text-sm font-medium ${
            activeTab === "vulnerabilities"
              ? "border-b-2 border-cyan-500 text-cyan-400"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          Vulnerabilities
        </button>
      </div>

      {/* Template Download */}
      <Card title="CSV Template">
        <p className="mb-4 text-sm text-slate-400">
          Download a template CSV file with the correct column headers:
        </p>
        <div className="flex gap-4">
          <Button
            variant="secondary"
            onClick={() => downloadTemplate("assets")}
          >
            Download Assets Template
          </Button>
          <Button
            variant="secondary"
            onClick={() => downloadTemplate("vulnerabilities")}
          >
            Download Vulnerabilities Template
          </Button>
        </div>
      </Card>

      {/* Upload Area */}
      <Card title="Upload CSV File">
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
            isDragging
              ? "border-cyan-500 bg-cyan-500/10"
              : "border-slate-700 hover:border-slate-500"
          }`}
        >
          <div className="space-y-4">
            <div className="text-4xl">📄</div>
            <p className="text-slate-300">
              {isDragging
                ? "Drop your CSV file here"
                : "Drag and drop your CSV file here, or click to select"}
            </p>
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={handleFileSelect}
              className="hidden"
              id="csv-upload"
            />
            <Button
              variant="secondary"
              onClick={() => document.getElementById("csv-upload")?.click()}
              disabled={uploading}
            >
              {uploading ? "Uploading..." : "Select File"}
            </Button>
          </div>
        </div>

        {uploading && (
          <div className="mt-4 text-center text-slate-400">
            Processing your file... This may take a moment for large files.
          </div>
        )}
      </Card>

      {/* Error Display */}
      {error && (
        <div className="rounded-lg bg-rose-500/10 p-4 text-rose-400">
          <p className="font-medium">Upload Failed</p>
          <p className="text-sm">{error}</p>
        </div>
      )}

      {/* Results Display */}
      {result && (
        <Card title="Import Results">
          <div
            className={`rounded-lg p-4 ${
              result.success ? "bg-emerald-500/10" : "bg-amber-500/10"
            }`}
          >
            <p
              className={`font-medium ${
                result.success ? "text-emerald-400" : "text-amber-400"
              }`}
            >
              {result.message}
            </p>
          </div>

          <div className="mt-4 grid grid-cols-4 gap-4">
            <ResultMetric
              label="Total Rows"
              value={result.summary.total_rows}
              color="slate"
            />
            <ResultMetric
              label="Inserted"
              value={result.summary.inserted}
              color="emerald"
            />
            <ResultMetric
              label="Updated"
              value={result.summary.updated}
              color="cyan"
            />
            <ResultMetric
              label="Failed"
              value={result.summary.failed}
              color="rose"
            />
          </div>

          <p className="mt-4 text-sm text-slate-500">
            Processing time: {result.summary.processing_time_ms}ms
          </p>

          {/* Error Details */}
          {result.summary.errors.length > 0 && (
            <div className="mt-6">
              <h3 className="mb-2 font-medium text-slate-200">
                Errors ({result.summary.errors.length} shown):
              </h3>
              <div className="max-h-64 overflow-auto rounded-lg bg-slate-800/50">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-slate-700">
                    <tr>
                      <th className="px-4 py-2 text-slate-400">Row</th>
                      <th className="px-4 py-2 text-slate-400">Field</th>
                      <th className="px-4 py-2 text-slate-400">Error</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {result.summary.errors.map((err, idx) => (
                      <tr key={idx}>
                        <td className="px-4 py-2 text-slate-300">{err.row_number}</td>
                        <td className="px-4 py-2 text-slate-400">
                          {err.field || "-"}
                        </td>
                        <td className="px-4 py-2 text-rose-400">{err.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Instructions */}
      <Card title="Upload Instructions">
        {activeTab === "assets" ? (
          <div className="space-y-2 text-sm text-slate-400">
            <p>
              <strong className="text-slate-200">Required columns:</strong>
            </p>
            <ul className="ml-4 list-disc space-y-1">
              <li>name - Asset name (e.g., &quot;Web Server 01&quot;)</li>
              <li>asset_type - Type: server, workstation, network, etc.</li>
              <li>business_unit_code - Must match an existing business unit code</li>
            </ul>
            <p className="mt-4">
              <strong className="text-slate-200">Optional columns:</strong>
            </p>
            <ul className="ml-4 list-disc space-y-1">
              <li>hostname - Fully qualified domain name</li>
              <li>ip_address - IPv4 or IPv6 address</li>
              <li>team_name - Must match existing team in the business unit</li>
              <li>location_name - Must match existing location</li>
              <li>criticality - 1-5 (1=critical, 5=low), default 3</li>
              <li>owner_email - Must be a user in your company</li>
            </ul>
            <p className="mt-4 text-amber-400">
              Note: Existing assets are matched by hostname or IP address and
              will be updated.
            </p>
          </div>
        ) : (
          <div className="space-y-2 text-sm text-slate-400">
            <p>
              <strong className="text-slate-200">Required columns:</strong>
            </p>
            <ul className="ml-4 list-disc space-y-1">
              <li>cve_id - CVE identifier (e.g., CVE-2024-1234)</li>
              <li>asset_identifier - Hostname or IP of existing asset</li>
            </ul>
            <p className="mt-4">
              <strong className="text-slate-200">Optional columns:</strong>
            </p>
            <ul className="ml-4 list-disc space-y-1">
              <li>
                status - OPEN, IN_PROGRESS, REMEDIATED, ACCEPTED_RISK,
                FALSE_POSITIVE
              </li>
              <li>discovered_date - ISO format (2024-01-15)</li>
              <li>due_date - ISO format (2024-02-15)</li>
              <li>notes - Free text description</li>
              <li>assigned_to_email - Must be a user in your company</li>
            </ul>
            <p className="mt-4 text-amber-400">
              Note: Assets must already exist in your company (upload assets
              first).
            </p>
          </div>
        )}
      </Card>
    </div>
  );
}

function ResultMetric({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: "slate" | "emerald" | "cyan" | "rose";
}) {
  const colors = {
    slate: "bg-slate-800/50 text-slate-200",
    emerald: "bg-emerald-500/10 text-emerald-400",
    cyan: "bg-cyan-500/10 text-cyan-400",
    rose: "bg-rose-500/10 text-rose-400",
  };

  return (
    <div className={`rounded-lg p-3 ${colors[color]}`}>
      <p className="text-xs opacity-80">{label}</p>
      <p className="text-2xl font-semibold">{value}</p>
    </div>
  );
}
