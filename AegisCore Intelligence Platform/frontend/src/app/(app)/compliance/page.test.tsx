import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import CompliancePage from "./page";

// Mock the hook
vi.mock("@/hooks/useCompliance", () => ({
  useCompliance: vi.fn(),
}));

import { useCompliance } from "@/hooks/useCompliance";

const mockReport = {
  total_findings: 150,
  open_findings: 45,
  overdue_findings: 8,
  sla_breach_count: 5,
  sla_breach_rate: 0.033,
  mean_time_to_remediate_days: 12,
  findings_by_severity: {
    CRITICAL: 5,
    HIGH: 20,
    MEDIUM: 50,
    LOW: 75,
  },
  findings_by_status: {
    OPEN: 45,
    IN_PROGRESS: 30,
    RESOLVED: 75,
  },
};

const mockClusters = [
  {
    root_cause_category: "Outdated Dependencies",
    count: 35,
    percentage: 23.3,
    example_cves: ["CVE-2024-1234", "CVE-2024-5678"],
  },
  {
    root_cause_category: "Misconfiguration",
    count: 28,
    percentage: 18.7,
    example_cves: ["CVE-2024-9012"],
  },
];

describe("CompliancePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state initially", () => {
    (useCompliance as jest.Mock).mockReturnValue({
      report: null,
      clusters: [],
      loading: true,
      error: null,
      loadAll: vi.fn(),
    });

    render(<CompliancePage />);

    expect(screen.getByText(/compliance & governance/i)).toBeInTheDocument();
  });

  it("renders KPI cards with data", async () => {
    (useCompliance as jest.Mock).mockReturnValue({
      report: mockReport,
      clusters: mockClusters,
      loading: false,
      error: null,
      loadAll: vi.fn(),
    });

    render(<CompliancePage />);

    await waitFor(() => {
      expect(screen.getByText("Open Findings")).toBeInTheDocument();
      expect(screen.getByText("45")).toBeInTheDocument();
      expect(screen.getByText("Overdue")).toBeInTheDocument();
      expect(screen.getByText("8")).toBeInTheDocument();
      expect(screen.getByText("SLA Breach Rate")).toBeInTheDocument();
      expect(screen.getByText("3%")).toBeInTheDocument();
    });
  });

  it("renders severity distribution", async () => {
    (useCompliance as jest.Mock).mockReturnValue({
      report: mockReport,
      clusters: mockClusters,
      loading: false,
      error: null,
      loadAll: vi.fn(),
    });

    render(<CompliancePage />);

    await waitFor(() => {
      expect(screen.getByText("Findings by Severity")).toBeInTheDocument();
      expect(screen.getByText("CRITICAL")).toBeInTheDocument();
      expect(screen.getByText("HIGH")).toBeInTheDocument();
    });
  });

  it("renders root cause clusters table", async () => {
    (useCompliance as jest.Mock).mockReturnValue({
      report: mockReport,
      clusters: mockClusters,
      loading: false,
      error: null,
      loadAll: vi.fn(),
    });

    render(<CompliancePage />);

    await waitFor(() => {
      expect(screen.getByText("Root Cause Clusters")).toBeInTheDocument();
      expect(screen.getByText("Outdated Dependencies")).toBeInTheDocument();
      expect(screen.getByText("Misconfiguration")).toBeInTheDocument();
    });
  });

  it("renders error state on failure", async () => {
    const loadAllMock = vi.fn();
    (useCompliance as jest.Mock).mockReturnValue({
      report: null,
      clusters: [],
      loading: false,
      error: "Failed to fetch compliance data",
      loadAll: loadAllMock,
    });

    render(<CompliancePage />);

    await waitFor(() => {
      expect(screen.getByText(/failed to load compliance data/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
    });

    const retryButton = screen.getByRole("button", { name: /try again/i });
    await userEvent.click(retryButton);
    expect(loadAllMock).toHaveBeenCalled();
  });

  it("renders empty state when no data", async () => {
    (useCompliance as jest.Mock).mockReturnValue({
      report: null,
      clusters: [],
      loading: false,
      error: null,
      loadAll: vi.fn(),
    });

    render(<CompliancePage />);

    await waitFor(() => {
      expect(screen.getByText(/no compliance data available/i)).toBeInTheDocument();
    });
  });
});
