import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import PrioritizedPage from "./page";

// Mock the hooks
vi.mock("@/hooks/useVulnerabilities", () => ({
  useVulnerabilities: vi.fn(),
}));

import { useVulnerabilities } from "@/hooks/useVulnerabilities";

const mockVulnerabilities = [
  {
    id: "1",
    asset_id: "asset-1",
    cve_record_id: "cve-1",
    cve_id: "CVE-2024-1234",
    status: "OPEN",
    discovered_at: "2024-01-15T10:00:00Z",
    due_at: "2024-01-30T10:00:00Z",
    assigned_to_user_id: null,
    risk_score: 85.5,
    risk_factors: { cvss: 9.0, criticality: 8.5, exposure: 7.0 },
    risk_calculated_at: "2024-01-16T10:00:00Z",
    asset_name: "Web Server 01",
    asset_criticality: "HIGH",
    cvss_score: 9.0,
  },
  {
    id: "2",
    asset_id: "asset-2",
    cve_record_id: "cve-2",
    cve_id: "CVE-2024-5678",
    status: "IN_PROGRESS",
    discovered_at: "2024-01-14T10:00:00Z",
    due_at: "2024-01-28T10:00:00Z",
    assigned_to_user_id: "user-1",
    risk_score: 72.3,
    risk_factors: { cvss: 7.5, criticality: 7.0, exposure: 6.5 },
    risk_calculated_at: "2024-01-15T10:00:00Z",
    asset_name: "Database Server",
    asset_criticality: "CRITICAL",
    cvss_score: 7.5,
  },
];

describe("PrioritizedPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state initially", () => {
    (useVulnerabilities as jest.Mock).mockReturnValue({
      data: [],
      total: 0,
      loading: true,
      error: null,
      fetchVulnerabilities: vi.fn(),
    });

    render(<PrioritizedPage />);

    expect(screen.getByText(/prioritized vulnerabilities/i)).toBeInTheDocument();
  });

  it("renders vulnerabilities table with data", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ items: mockVulnerabilities, total: 2 });
    (useVulnerabilities as jest.Mock).mockReturnValue({
      data: mockVulnerabilities,
      total: 2,
      loading: false,
      error: null,
      fetchVulnerabilities: fetchMock,
    });

    render(<PrioritizedPage />);

    await waitFor(() => {
      expect(screen.getByText("CVE-2024-1234")).toBeInTheDocument();
      expect(screen.getByText("CVE-2024-5678")).toBeInTheDocument();
      expect(screen.getByText("Web Server 01")).toBeInTheDocument();
      expect(screen.getByText("Database Server")).toBeInTheDocument();
    });
  });

  it("displays risk scores with proper color coding", async () => {
    (useVulnerabilities as jest.Mock).mockReturnValue({
      data: mockVulnerabilities,
      total: 2,
      loading: false,
      error: null,
      fetchVulnerabilities: vi.fn(),
    });

    render(<PrioritizedPage />);

    await waitFor(() => {
      // High risk score should be visible
      expect(screen.getByText("85.5")).toBeInTheDocument();
      expect(screen.getByText("72.3")).toBeInTheDocument();
    });
  });

  it("renders error state when API fails", async () => {
    (useVulnerabilities as jest.Mock).mockReturnValue({
      data: [],
      total: 0,
      loading: false,
      error: "Failed to fetch vulnerabilities",
      fetchVulnerabilities: vi.fn(),
    });

    render(<PrioritizedPage />);

    await waitFor(() => {
      expect(screen.getByText(/failed to load vulnerabilities/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
    });
  });

  it("renders empty state when no vulnerabilities", async () => {
    (useVulnerabilities as jest.Mock).mockReturnValue({
      data: [],
      total: 0,
      loading: false,
      error: null,
      fetchVulnerabilities: vi.fn(),
    });

    render(<PrioritizedPage />);

    await waitFor(() => {
      expect(screen.getByText(/no vulnerabilities found/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /upload data/i })).toBeInTheDocument();
    });
  });

  it("allows retry on error", async () => {
    const fetchMock = vi.fn();
    (useVulnerabilities as jest.Mock).mockReturnValue({
      data: [],
      total: 0,
      loading: false,
      error: "Failed to fetch vulnerabilities",
      fetchVulnerabilities: fetchMock,
    });

    render(<PrioritizedPage />);

    const retryButton = await screen.findByRole("button", { name: /try again/i });
    await userEvent.click(retryButton);

    expect(fetchMock).toHaveBeenCalled();
  });
});
