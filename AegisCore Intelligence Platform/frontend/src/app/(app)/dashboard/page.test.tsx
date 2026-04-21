import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import DashboardPage from "./page";

// Mock the API calls
vi.mock("@/lib/api", () => ({
  getAnalyticsSummary: vi.fn(),
  getRiskTrend: vi.fn(),
  getSlaForecast: vi.fn(),
}));

// Mock the components
vi.mock("@/components/assistant/AssistantPanel", () => ({
  AssistantPanel: () => <div data-testid="assistant-panel">Assistant</div>,
}));

vi.mock("@/components/prioritization/TopRisksWidget", () => ({
  TopRisksWidget: () => <div data-testid="top-risks">Top Risks</div>,
}));

import {
  getAnalyticsSummary,
  getRiskTrend,
  getSlaForecast,
} from "@/lib/api";

const mockSummary = {
  total_open_findings: 150,
  by_severity: [
    { severity: "CRITICAL", count: 5 },
    { severity: "HIGH", count: 25 },
    { severity: "MEDIUM", count: 60 },
    { severity: "LOW", count: 60 },
  ],
  by_status: [
    { status: "OPEN", count: 150 },
    { status: "RESOLVED", count: 300 },
  ],
};

const mockTrend = {
  points: [
    { date: "2024-01-01", opened_count: 10, avg_risk_score: 7.5 },
    { date: "2024-01-02", opened_count: 15, avg_risk_score: 7.8 },
    { date: "2024-01-03", opened_count: 12, avg_risk_score: 7.2 },
    { date: "2024-01-04", opened_count: 8, avg_risk_score: 6.9 },
    { date: "2024-01-05", opened_count: 20, avg_risk_score: 8.1 },
    { date: "2024-01-06", opened_count: 18, avg_risk_score: 7.9 },
    { date: "2024-01-07", opened_count: 22, avg_risk_score: 8.3 },
  ],
};

const mockSla = {
  due_next_7_days: 45,
  due_next_14_days: 89,
  predicted_breaches_next_7_days: 3,
  predicted_breaches_next_14_days: 8,
};

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state initially", () => {
    (getAnalyticsSummary as jest.Mock).mockImplementation(
      () => new Promise(() => {})
    );
    (getRiskTrend as jest.Mock).mockImplementation(() => new Promise(() => {}));
    (getSlaForecast as jest.Mock).mockImplementation(() => new Promise(() => {}));

    render(<DashboardPage />);

    expect(screen.getByText(/security dashboard/i)).toBeInTheDocument();
    expect(screen.getAllByText(/loading/i).length).toBeGreaterThan(0);
  });

  it("renders dashboard with data successfully", async () => {
    (getAnalyticsSummary as jest.Mock).mockResolvedValue(mockSummary);
    (getRiskTrend as jest.Mock).mockResolvedValue(mockTrend);
    (getSlaForecast as jest.Mock).mockResolvedValue(mockSla);

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("150")).toBeInTheDocument(); // Total findings
      expect(screen.getByText("5")).toBeInTheDocument(); // Critical
      expect(screen.getByText("25")).toBeInTheDocument(); // High
    });

    expect(screen.getByText(/critical risk/i)).toBeInTheDocument();
    expect(screen.getByText(/high risk/i)).toBeInTheDocument();
    expect(screen.getByTestId("top-risks")).toBeInTheDocument();
    expect(screen.getByTestId("assistant-panel")).toBeInTheDocument();
  });

  it("renders empty state when no data", async () => {
    (getAnalyticsSummary as jest.Mock).mockResolvedValue({
      total_open_findings: 0,
      by_severity: [],
      by_status: [],
    });
    (getRiskTrend as jest.Mock).mockResolvedValue({ points: [] });
    (getSlaForecast as jest.Mock).mockResolvedValue(mockSla);

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/no data uploaded yet/i)).toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: /upload data/i })).toBeInTheDocument();
  });

  it("renders error state when API fails", async () => {
    (getAnalyticsSummary as jest.Mock).mockRejectedValue(
      new Error("Failed to fetch")
    );
    (getRiskTrend as jest.Mock).mockRejectedValue(new Error("Failed to fetch"));
    (getSlaForecast as jest.Mock).mockRejectedValue(new Error("Failed to fetch"));

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/failed to load dashboard/i)).toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });

  it("allows retry on error", async () => {
    (getAnalyticsSummary as jest.Mock)
      .mockRejectedValueOnce(new Error("Failed to fetch"))
      .mockResolvedValueOnce(mockSummary);
    (getRiskTrend as jest.Mock)
      .mockRejectedValueOnce(new Error("Failed to fetch"))
      .mockResolvedValueOnce(mockTrend);
    (getSlaForecast as jest.Mock)
      .mockRejectedValueOnce(new Error("Failed to fetch"))
      .mockResolvedValueOnce(mockSla);

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/failed to load dashboard/i)).toBeInTheDocument();
    });

    const retryButton = screen.getByRole("button", { name: /try again/i });
    await userEvent.click(retryButton);

    await waitFor(() => {
      expect(screen.getByText("150")).toBeInTheDocument();
    });
  });

  it("displays severity distribution bars correctly", async () => {
    (getAnalyticsSummary as jest.Mock).mockResolvedValue(mockSummary);
    (getRiskTrend as jest.Mock).mockResolvedValue(mockTrend);
    (getSlaForecast as jest.Mock).mockResolvedValue(mockSla);

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/severity distribution/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/critical/i)).toBeInTheDocument();
    expect(screen.getByText(/high/i)).toBeInTheDocument();
    expect(screen.getByText(/medium/i)).toBeInTheDocument();
    expect(screen.getByText(/low/i)).toBeInTheDocument();
  });

  it("displays SLA forecast correctly", async () => {
    (getAnalyticsSummary as jest.Mock).mockResolvedValue(mockSummary);
    (getRiskTrend as jest.Mock).mockResolvedValue(mockTrend);
    (getSlaForecast as jest.Mock).mockResolvedValue(mockSla);

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/sla forecast/i)).toBeInTheDocument();
    });

    expect(screen.getByText("45")).toBeInTheDocument(); // Due next 7 days
    expect(screen.getByText("89")).toBeInTheDocument(); // Due next 14 days
    expect(screen.getByText("3")).toBeInTheDocument(); // Predicted breaches 7d
    expect(screen.getByText("8")).toBeInTheDocument(); // Predicted breaches 14d
  });
});
