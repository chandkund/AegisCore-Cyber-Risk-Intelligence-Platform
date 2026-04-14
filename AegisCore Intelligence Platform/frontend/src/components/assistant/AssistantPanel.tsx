"use client";

import { useState } from "react";
import { askAssistant } from "@/lib/api";
import type { AssistantResponseOut } from "@/types/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

export function AssistantPanel() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<AssistantResponseOut[]>([]);

  async function handleAsk() {
    const q = question.trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    const result = await askAssistant(q);
    setLoading(false);
    if (!result) {
      setError("Assistant request failed");
      return;
    }
    setHistory((prev) => [result, ...prev].slice(0, 5));
    setQuestion("");
  }

  return (
    <Card title="AI Security Assistant">
      <div className="space-y-3">
        <div className="flex gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask: What should I fix first this week?"
            className="flex-1 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
          />
          <Button type="button" onClick={() => void handleAsk()} disabled={loading}>
            {loading ? "Asking..." : "Ask"}
          </Button>
        </div>
        {error ? <p className="text-sm text-rose-400">{error}</p> : null}
        {history.map((item, idx) => (
          <div key={idx} className="rounded-md border border-slate-800 p-3">
            <p className="text-sm text-slate-200 whitespace-pre-line">{item.answer}</p>
            <p className="mt-2 text-xs text-slate-400">
              Type: {item.question_type} · Confidence: {item.confidence}
            </p>
          </div>
        ))}
      </div>
    </Card>
  );
}
