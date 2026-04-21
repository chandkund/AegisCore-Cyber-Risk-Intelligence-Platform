"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/AuthProvider";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import {
  platformUploadsImportsRequest,
  platformUploadsFilesRequest,
} from "@/lib/api";

interface ImportUpload {
  id: string;
  tenant_id: string;
  upload_type: string;
  original_filename: string;
  file_size_bytes: number;
  status: string;
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
  };
  processing_time_ms: number;
  uploaded_by_user_id: string | null;
  created_at: string;
  completed_at: string | null;
}

interface FileUpload {
  id: string;
  tenant_id: string;
  upload_type: string;
  original_filename: string;
  storage_path: string;
  file_size_bytes: number;
  mime_type: string;
  uploaded_by_user_id: string | null;
  created_at: string;
}

export default function PlatformUploadsPage() {
  const { hasRole } = useAuth();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"imports" | "files">("imports");
  const [imports, setImports] = useState<ImportUpload[]>([]);
  const [files, setFiles] = useState<FileUpload[]>([]);
  const [totalStorage, setTotalStorage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [typeFilter, setTypeFilter] = useState<string>("");

  useEffect(() => {
    if (!hasRole("platform_owner")) {
      router.replace("/dashboard");
      return;
    }

    async function loadData() {
      try {
        setLoading(true);
        if (activeTab === "imports") {
          const res = await platformUploadsImportsRequest(50, 0, typeFilter || undefined, statusFilter || undefined);
          if (res.ok && res.data) {
            setImports(res.data.items);
          }
        } else {
          const res = await platformUploadsFilesRequest(50, 0, typeFilter || undefined);
          if (res.ok && res.data) {
            setFiles(res.data.items);
            setTotalStorage(res.data.total_storage_bytes);
          }
        }
      } catch (err) {
        setError("Failed to load upload data");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [hasRole, router, activeTab, statusFilter, typeFilter]);

  if (!hasRole("platform_owner")) {
    return null;
  }

  function formatBytes(bytes: number): string {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  }

  function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleString();
  }

  function getStatusBadgeColor(status: string): string {
    const colors: Record<string, string> = {
      completed: "bg-emerald-500/10 text-emerald-400",
      processing: "bg-amber-500/10 text-amber-400",
      failed: "bg-rose-500/10 text-rose-400",
      partial: "bg-orange-500/10 text-orange-400",
    };
    return colors[status] || "bg-slate-500/10 text-slate-400";
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-100">Upload Monitoring</h1>
        <Button variant="secondary" onClick={() => router.push("/platform")}>
          Back to Platform
        </Button>
      </div>

      {error && (
        <div className="rounded-lg bg-rose-500/10 p-4 text-rose-400">
          {error}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-700">
        <button
          onClick={() => setActiveTab("imports")}
          className={`px-4 py-2 text-sm font-medium ${
            activeTab === "imports"
              ? "border-b-2 border-indigo-500 text-indigo-400"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          Data Imports
        </button>
        <button
          onClick={() => setActiveTab("files")}
          className={`px-4 py-2 text-sm font-medium ${
            activeTab === "files"
              ? "border-b-2 border-indigo-500 text-indigo-400"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          File Uploads
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        {activeTab === "imports" && (
          <>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-sm text-slate-200"
            >
              <option value="">All Statuses</option>
              <option value="completed">Completed</option>
              <option value="processing">Processing</option>
              <option value="failed">Failed</option>
              <option value="partial">Partial</option>
            </select>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-sm text-slate-200"
            >
              <option value="">All Types</option>
              <option value="assets_import">Assets</option>
              <option value="vulnerabilities_import">Vulnerabilities</option>
              <option value="mappings_import">Mappings</option>
            </select>
          </>
        )}
        {activeTab === "files" && (
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-sm text-slate-200"
          >
            <option value="">All Types</option>
            <option value="document">Documents</option>
            <option value="scan_report">Scan Reports</option>
            <option value="evidence">Evidence</option>
          </select>
        )}
      </div>

      {/* Summary Cards */}
      {activeTab === "files" && (
        <div className="grid grid-cols-2 gap-4">
          <div className="rounded-lg bg-slate-800/50 p-4">
            <p className="text-sm text-slate-400">Total Storage Used</p>
            <p className="mt-1 text-2xl font-semibold text-slate-100">
              {formatBytes(totalStorage)}
            </p>
          </div>
          <div className="rounded-lg bg-slate-800/50 p-4">
            <p className="text-sm text-slate-400">Total Files</p>
            <p className="mt-1 text-2xl font-semibold text-slate-100">
              {files.length}
            </p>
          </div>
        </div>
      )}

      {/* Data Tables */}
      {loading ? (
        <div className="flex min-h-[30vh] items-center justify-center text-slate-400">
          Loading uploads…
        </div>
      ) : activeTab === "imports" ? (
        <Card title="Data Imports">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-700">
                <tr>
                  <th className="pb-3 font-medium text-slate-400">Tenant ID</th>
                  <th className="pb-3 font-medium text-slate-400">Type</th>
                  <th className="pb-3 font-medium text-slate-400">Filename</th>
                  <th className="pb-3 font-medium text-slate-400">Status</th>
                  <th className="pb-3 font-medium text-slate-400">Results</th>
                  <th className="pb-3 font-medium text-slate-400">Time</th>
                  <th className="pb-3 font-medium text-slate-400">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {imports.map((imp) => (
                  <tr key={imp.id}>
                    <td className="py-3 text-slate-400 font-mono text-xs">
                      {imp.tenant_id.slice(0, 8)}…
                    </td>
                    <td className="py-3 text-slate-300">{imp.upload_type.replace("_", " ")}</td>
                    <td className="py-3 text-slate-300">{imp.original_filename}</td>
                    <td className="py-3">
                      <span className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${getStatusBadgeColor(imp.status)}`}>
                        {imp.status}
                      </span>
                    </td>
                    <td className="py-3 text-slate-400 text-xs">
                      {imp.summary && (
                        <span>
                          ✓ {imp.summary.inserted + imp.summary.updated} | ✗ {imp.summary.failed}
                        </span>
                      )}
                    </td>
                    <td className="py-3 text-slate-400 text-xs">
                      {imp.processing_time_ms}ms
                    </td>
                    <td className="py-3 text-slate-400 text-xs">
                      {formatDate(imp.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {imports.length === 0 && (
              <p className="py-8 text-center text-slate-400">No imports found</p>
            )}
          </div>
        </Card>
      ) : (
        <Card title="File Uploads">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-700">
                <tr>
                  <th className="pb-3 font-medium text-slate-400">Tenant ID</th>
                  <th className="pb-3 font-medium text-slate-400">Type</th>
                  <th className="pb-3 font-medium text-slate-400">Filename</th>
                  <th className="pb-3 font-medium text-slate-400">Size</th>
                  <th className="pb-3 font-medium text-slate-400">MIME Type</th>
                  <th className="pb-3 font-medium text-slate-400">Uploaded</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {files.map((file) => (
                  <tr key={file.id}>
                    <td className="py-3 text-slate-400 font-mono text-xs">
                      {file.tenant_id.slice(0, 8)}…
                    </td>
                    <td className="py-3 text-slate-300">{file.upload_type}</td>
                    <td className="py-3 text-slate-300">{file.original_filename}</td>
                    <td className="py-3 text-slate-400">{formatBytes(file.file_size_bytes)}</td>
                    <td className="py-3 text-slate-400 text-xs">{file.mime_type}</td>
                    <td className="py-3 text-slate-400 text-xs">
                      {formatDate(file.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {files.length === 0 && (
              <p className="py-8 text-center text-slate-400">No files found</p>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
