import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { RiskExplanationPanel } from "@/components/explanations/RiskExplanationPanel";
import { getRiskExplanation } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  getRiskExplanation: vi.fn(),
}));

describe("RiskExplanationPanel", () => {
  it("renders explanation content when API succeeds", async () => {
    const mocked = getRiskExplanation as unknown as ReturnType<typeof vi.fn>;
    mocked.mockResolvedValue({
      finding_id: "f-1",
      risk_score: 82.5,
      severity_level: "Critical",
      overall_assessment: "High risk due to external exposure.",
      top_factors: [{ factor: "exposure", weight: 0.2, score: 1, description: "Internet-facing", impact: "high" }],
      detailed_explanation: "Detailed text",
      remediation_priority_reason: "Fix immediately.",
      comparable_examples: ["Comparable case"],
      generated_at: new Date().toISOString(),
    });

    render(<RiskExplanationPanel findingId="f-1" />);

    await waitFor(() => {
      expect(screen.getByText(/Risk Explanation/i)).toBeInTheDocument();
      expect(screen.getByText(/High risk due to external exposure/i)).toBeInTheDocument();
      expect(screen.getByText(/Fix immediately/i)).toBeInTheDocument();
    });
  });
});
