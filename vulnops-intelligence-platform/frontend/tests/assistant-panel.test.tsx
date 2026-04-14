import { describe, it, expect, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AssistantPanel } from "@/components/assistant/AssistantPanel";
import { askAssistant } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  askAssistant: vi.fn(),
}));

describe("AssistantPanel", () => {
  it("submits a question and renders answer", async () => {
    const mocked = askAssistant as unknown as ReturnType<typeof vi.fn>;
    mocked.mockResolvedValue({
      answer: "Top risk is CVE-2024-0001",
      question_type: "prioritization",
      supporting_records: [{ finding_id: "a" }],
      confidence: "high",
      suggested_followups: [],
      generated_at: new Date().toISOString(),
    });

    render(<AssistantPanel />);
    fireEvent.change(screen.getByPlaceholderText(/Ask:/i), {
      target: { value: "What should I fix first?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Ask/i }));

    await waitFor(() => {
      expect(screen.getByText(/Top risk is CVE-2024-0001/i)).toBeInTheDocument();
    });
  });
});
