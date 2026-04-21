"use client";

import { useState, useCallback } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

interface FileUploadProps {
  onUploadSuccess?: (result: UploadResult) => void;
  allowedTypes?: string;
  maxSizeMB?: number;
}

interface UploadResult {
  id: string;
  original_filename: string;
  size: number;
  uploaded_at: string;
  message: string;
}

export function FileUpload({
  onUploadSuccess,
  allowedTypes = ".csv,.json,.xml,.nessus,.sarif,.pdf,.zip",
  maxSizeMB = 50,
}: FileUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [description, setDescription] = useState("");

  const maxSizeBytes = maxSizeMB * 1024 * 1024;

  const validateAndSetFile = useCallback((selectedFile: File) => {
    setError(null);
    setSuccess(null);

    // Check file size
    if (selectedFile.size > maxSizeBytes) {
      setError(`File too large. Max size: ${maxSizeMB}MB`);
      return;
    }

    // Check file extension
    const ext = selectedFile.name.split(".").pop()?.toLowerCase();
    const allowedExts = allowedTypes.split(",").map((t) => t.replace(".", "").trim());
    if (!ext || !allowedExts.includes(ext)) {
      setError(`File type not allowed. Allowed: ${allowedTypes}`);
      return;
    }

    setFile(selectedFile);
  }, [allowedTypes, maxSizeBytes, maxSizeMB]);

  const onDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) validateAndSetFile(droppedFile);
  }, [validateAndSetFile]);

  const onFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) validateAndSetFile(selectedFile);
  };

  const uploadFile = async () => {
    if (!file) return;

    setUploading(true);
    setError(null);
    setSuccess(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      if (description) {
        formData.append("description", description);
      }

      // Cookie-based auth - cookies sent automatically with credentials: 'include'
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/upload`, {
        method: "POST",
        credentials: "include",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Upload failed");
      }

      const result: UploadResult = await res.json();
      setSuccess(`Uploaded: ${result.original_filename} (${(result.size / 1024).toFixed(1)} KB)`);
      onUploadSuccess?.(result);
      setFile(null);
      setDescription("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <Card title="Upload Vulnerability Report">
      <div className="space-y-4">
        {/* Drag & Drop Zone */}
        <div
          onDrop={onDrop}
          onDragOver={(e) => e.preventDefault()}
          className="border-2 border-dashed border-slate-600 rounded-lg p-8 text-center hover:border-sky-500 transition-colors cursor-pointer"
          onClick={() => document.getElementById("file-input")?.click()}
        >
          <input
            id="file-input"
            type="file"
            accept={allowedTypes}
            onChange={onFileSelect}
            className="hidden"
          />
          <p className="text-slate-400">
            {file ? (
              <span className="text-sky-400">{file.name}</span>
            ) : (
              <>Drop file here or click to select</>
            )}
          </p>
          <p className="text-xs text-slate-500 mt-2">
            Allowed: {allowedTypes} | Max: {maxSizeMB}MB
          </p>
        </div>

        {/* Description */}
        {file && (
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Description (optional)
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g., Q1 vulnerability scan results"
              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-slate-100 focus:border-sky-500 focus:outline-none"
              rows={2}
            />
          </div>
        )}

        {/* Upload Button */}
        {file && (
          <Button
            onClick={uploadFile}
            disabled={uploading}
            className="w-full"
          >
            {uploading ? "Uploading..." : "Upload File"}
          </Button>
        )}

        {/* Error */}
        {error && (
          <p className="text-rose-400 text-sm" role="alert">
            {error}
          </p>
        )}

        {/* Success */}
        {success && (
          <p className="text-emerald-400 text-sm" role="status">
            {success}
          </p>
        )}
      </div>
    </Card>
  );
}
