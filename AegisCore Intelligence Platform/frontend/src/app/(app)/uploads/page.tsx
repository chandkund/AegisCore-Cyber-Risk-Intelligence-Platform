"use client";

import { FileUpload } from "@/components/upload/FileUpload";
import { Card } from "@/components/ui/Card";

export default function UploadsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-100">File Uploads</h2>
        <p className="mt-1 text-slate-400">
          Upload vulnerability scan results and reports
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <FileUpload
          onUploadSuccess={(result) => {
            console.log("Uploaded:", result);
          }}
        />

        <Card title="Upload Guidelines">
          <ul className="space-y-2 text-sm text-slate-400">
            <li>• <strong>CSV:</strong> Vulnerability scan exports</li>
            <li>• <strong>JSON:</strong> API scan results</li>
            <li>• <strong>XML/Nessus:</strong> Nessus scan reports</li>
            <li>• <strong>SARIF:</strong> Static analysis results</li>
            <li>• <strong>PDF:</strong> Executive reports</li>
            <li>• <strong>ZIP:</strong> Multiple files (max 50MB)</li>
          </ul>
          <p className="mt-4 text-xs text-slate-500">
            All uploads are logged for audit purposes.
          </p>
        </Card>
      </div>
    </div>
  );
}
