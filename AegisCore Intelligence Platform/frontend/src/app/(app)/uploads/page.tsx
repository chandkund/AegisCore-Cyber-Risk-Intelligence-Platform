"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import { 
  Upload, 
  Server, 
  ShieldAlert, 
  Link2, 
  FileText, 
  Download,
  CheckCircle,
  AlertCircle,
  FileSpreadsheet,
  FileJson
} from "lucide-react";
import { 
  uploadAssets, 
  uploadVulnerabilities, 
  uploadMappings,
  downloadTemplate,
  type UploadResult 
} from "@/lib/api";

// Upload category definitions
const UPLOAD_CATEGORIES = [
  {
    id: "assets",
    title: "Assets Upload",
    description: "Import asset inventory (servers, applications, network devices)",
    icon: Server,
    formats: [".csv", ".json"],
    maxSize: "10MB",
    requiredFields: ["name", "asset_type", "business_unit_code"],
    optionalFields: ["hostname", "ip_address", "team_name", "location_name", "criticality", "owner_email"],
    role: "admin",
  },
  {
    id: "vulnerabilities",
    title: "Vulnerabilities Upload",
    description: "Import CVE records and vulnerability definitions",
    icon: ShieldAlert,
    formats: [".csv", ".json"],
    maxSize: "10MB",
    requiredFields: ["cve_id", "title"],
    optionalFields: ["description", "severity", "cvss_score", "exploit_available", "published_date"],
    role: "analyst",
  },
  {
    id: "mappings",
    title: "Asset-Vulnerability Mapping",
    description: "Link vulnerabilities to specific assets (creates findings)",
    icon: Link2,
    formats: [".csv", ".json"],
    maxSize: "10MB",
    requiredFields: ["asset_identifier", "cve_id"],
    optionalFields: ["status", "discovered_date", "due_date", "notes", "assigned_to_email"],
    role: "analyst",
  },
  {
    id: "documents",
    title: "Supporting Documents",
    description: "Upload reports, evidence files, and documentation",
    icon: FileText,
    formats: [".pdf", ".zip", ".txt"],
    maxSize: "50MB",
    requiredFields: [],
    optionalFields: ["description"],
    role: "user",
  },
] as const;

function UploadCard({ 
  category, 
  onUpload 
}: { 
  category: typeof UPLOAD_CATEGORIES[number];
  onUpload: (categoryId: string, file: File) => Promise<UploadResult>;
}) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const Icon = category.icon;

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) validateAndSetFile(file);
  };

  const validateAndSetFile = (file: File) => {
    setError(null);
    setResult(null);

    // Check extension
    const ext = file.name.split(".").pop()?.toLowerCase();
    const allowedExts = category.formats.map(f => f.replace(".", ""));
    if (!ext || !allowedExts.includes(ext)) {
      setError(`Invalid file type. Allowed: ${category.formats.join(", ")}`);
      return;
    }

    // Check size
    const maxBytes = category.id === "documents" ? 50 * 1024 * 1024 : 10 * 1024 * 1024;
    if (file.size > maxBytes) {
      setError(`File too large. Max size: ${category.maxSize}`);
      return;
    }

    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    
    setIsUploading(true);
    setError(null);
    setResult(null);

    try {
      const uploadResult = await onUpload(category.id, selectedFile);
      setResult(uploadResult);
      setSelectedFile(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setIsUploading(false);
    }
  };

  const handleDownloadTemplate = async () => {
    if (category.id === "documents") return;
    try {
      const blob = await downloadTemplate(category.id as "assets" | "vulnerabilities" | "mappings");
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${category.id}_template.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to download template:", err);
    }
  };

  return (
    <Card title={
      <div className="flex items-center gap-2">
        <Icon className="h-5 w-5 text-accent" />
        <span>{category.title}</span>
      </div>
    }>
      <div className="space-y-4">
        {/* Description */}
        <p className="text-sm text-slate-400">{category.description}</p>

        {/* Template Download */}
        {category.id !== "documents" && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleDownloadTemplate}
            className="text-sky-400 hover:text-sky-300"
          >
            <Download className="h-4 w-4 mr-1" />
            Download CSV Template
          </Button>
        )}

        {/* Format Info */}
        <div className="flex flex-wrap gap-2 text-xs">
          {category.formats.map(format => (
            <span key={format} className="px-2 py-1 bg-slate-800 rounded text-slate-400">
              {format}
            </span>
          ))}
          <span className="px-2 py-1 bg-slate-800 rounded text-slate-400">
            Max {category.maxSize}
          </span>
        </div>

        {/* Required/Optional Fields */}
        <div className="text-xs space-y-1">
          {category.requiredFields.length > 0 && (
            <div>
              <span className="text-slate-500">Required: </span>
              <span className="text-accent">{category.requiredFields.join(", ")}</span>
            </div>
          )}
          {category.optionalFields.length > 0 && (
            <div>
              <span className="text-slate-500">Optional: </span>
              <span className="text-slate-400">{category.optionalFields.join(", ")}</span>
            </div>
          )}
        </div>

        {/* Upload Area */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => document.getElementById(`file-input-${category.id}`)?.click()}
          className={cn(
            "border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors",
            isDragging 
              ? "border-accent bg-accent/5" 
              : "border-slate-600 hover:border-slate-500"
          )}
        >
          <input
            id={`file-input-${category.id}`}
            type="file"
            accept={category.formats.join(",")}
            onChange={(e) => e.target.files?.[0] && validateAndSetFile(e.target.files[0])}
            className="hidden"
          />
          {selectedFile ? (
            <div className="space-y-2">
              <FileSpreadsheet className="h-8 w-8 mx-auto text-accent" />
              <p className="text-sm text-slate-300">{selectedFile.name}</p>
              <p className="text-xs text-slate-500">
                {(selectedFile.size / 1024).toFixed(1)} KB
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              <Upload className="h-8 w-8 mx-auto text-slate-500" />
              <p className="text-sm text-slate-400">
                Drop file here or click to select
              </p>
            </div>
          )}
        </div>

        {/* Upload Button */}
        {selectedFile && (
          <Button
            onClick={handleUpload}
            disabled={isUploading}
            className="w-full"
          >
            {isUploading ? "Uploading..." : "Upload File"}
          </Button>
        )}

        {/* Error */}
        {error && (
          <div className="flex items-start gap-2 p-3 rounded bg-red-500/10 border border-red-500/20">
            <AlertCircle className="h-4 w-4 text-red-400 mt-0.5" />
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        {/* Success Result */}
        {result?.success && (
          <div className="flex items-start gap-2 p-3 rounded bg-green-500/10 border border-green-500/20">
            <CheckCircle className="h-4 w-4 text-green-400 mt-0.5" />
            <div className="text-sm text-green-400">
              <p>{result.message}</p>
              {(result.inserted > 0 || result.updated > 0 || result.failed > 0) && (
                <p className="text-xs mt-1">
                  Inserted: {result.inserted} | Updated: {result.updated} | Failed: {result.failed}
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}

export default function UploadsPage() {
  const [activeTab, setActiveTab] = useState<string>("assets");

  const handleUpload = async (categoryId: string, file: File): Promise<UploadResult> => {
    switch (categoryId) {
      case "assets":
        return uploadAssets(file);
      case "vulnerabilities":
        return uploadVulnerabilities(file);
      case "mappings":
        return uploadMappings(file);
      case "documents":
        // Document upload not yet implemented
        throw new Error("Document upload coming soon");
      default:
        throw new Error("Unknown upload category");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-slate-100">Data Uploads</h2>
        <p className="mt-1 text-slate-400">
          Import assets, vulnerabilities, and mappings into your tenant
        </p>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-slate-800 pb-4">
        {UPLOAD_CATEGORIES.map((category) => (
          <button
            key={category.id}
            onClick={() => setActiveTab(category.id)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
              activeTab === category.id
                ? "bg-accent/10 text-accent border border-accent/20"
                : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
            )}
          >
            <category.icon className="h-4 w-4" />
            {category.title}
          </button>
        ))}
      </div>

      {/* Active Upload Card */}
      <div className="max-w-2xl">
        <UploadCard
          category={UPLOAD_CATEGORIES.find(c => c.id === activeTab)!}
          onUpload={handleUpload}
        />
      </div>

      {/* Upload Guidelines */}
      <Card title="Upload Guidelines">
        <div className="space-y-4 text-sm text-slate-400">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <h4 className="font-medium text-slate-300 mb-2">CSV Format</h4>
              <ul className="space-y-1 text-xs">
                <li>• UTF-8 encoding required</li>
                <li>• Header row required</li>
                <li>• Comma-separated values</li>
                <li>• Text fields may be quoted</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-slate-300 mb-2">JSON Format</h4>
              <ul className="space-y-1 text-xs">
                <li>• Array of objects</li>
                <li>• Field names match CSV headers</li>
                <li>• UTF-8 encoding required</li>
              </ul>
            </div>
          </div>
          <p className="text-xs text-slate-500">
            All uploads are scoped to your tenant and audited. 
            Download templates to see exact field requirements.
          </p>
        </div>
      </Card>
    </div>
  );
}
