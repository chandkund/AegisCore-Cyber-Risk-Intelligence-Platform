import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import FindingsPage from "./page";

// Mock the hooks
vi.mock("@/hooks/useFindings", () => ({
  useFindings: vi.fn(),
}));

import { useFindings } from "@/hooks/useFindings";

const mockFindings = [
  {
    id: "1",
    asset_id: "asset-1",
    asset_name: "Web Server 01",
    vulnerability_id: "vuln-1",
    cve_id: "CVE-2024-1234",
    severity: "CRITICAL",
    cvss_score: 9.8,
    status: "OPEN",
    discovered_at: "2024-01-15T10:00:00Z",
    last_seen_at: "2024-01-20T10:00:00Z",
    description: "SQL injection vulnerability in login form",
    remediation: "Update to latest version and sanitize inputs",
    port: 443,
    service_name: "HTTPS",
    raw_payload: null,
    confidence: "HIGH",
    risk_score: 95.0,
  },
  {
    id: "2",
    asset_id: "asset-2",
    asset_name: "Database Server",
    vulnerability_id: "vuln-2",
    cve_id: "CVE-2024-5678",
    severity: "HIGH",
    cvss_score: 7.5,
    status: "IN_PROGRESS",
    discovered_at: "2024-01-14T10:00:00Z",
    last_seen_at: null,
    description: "Outdated TLS version",
    remediation: "Upgrade TLS to 1.3",
    port: 3306,
    service_name: "MySQL",
    raw_payload: null,
    confidence: "MEDIUM",
    risk_score: 72.0,
  },
];

describe("FindingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state initially", () => {
    (useFindings as jest.Mock).mockReturnValue({
      data: [],
      total: 0,
      loading: true,
      error: null,
      selectedFinding: null,
      fetchFindings: vi.fn(),
      fetchFindingDetail: vi.fn(),
      setSelectedFinding: vi.fn(),
    });

    render(<FindingsPage />);

    expect(screen.getByText(/findings/i)).toBeInTheDocument();
  });

  it("renders findings table with data", async () => {
    (useFindings as jest.Mock).mockReturnValue({
      data: mockFindings,
      total: 2,
      loading: false,
      error: null,
      selectedFinding: null,
      fetchFindings: vi.fn(),
      fetchFindingDetail: vi.fn(),
      setSelectedFinding: vi.fn(),
    });

    render(<FindingsPage />);

    await waitFor(() => {
      expect(screen.getByText("CVE-2024-1234")).toBeInTheDocument();
      expect(screen.getByText("CVE-2024-5678")).toBeInTheDocument();
      expect(screen.getByText("Web Server 01")).toBeInTheDocument();
      expect(screen.getByText("Database Server")).toBeInTheDocument();
    });
  });

  it("displays severity badges with proper colors", async () => {
    (useFindings as jest.Mock).mockReturnValue({
      data: mockFindings,
      total: 2,
      loading: false,
      error: null,
      selectedFinding: null,
      fetchFindings: vi.fn(),
      fetchFindingDetail: vi.fn(),
      setSelectedFinding: vi.fn(),
    });

    render(<FindingsPage />);

    await waitFor(() => {
      expect(screen.getByText("CRITICAL")).toBeInTheDocument();
      expect(screen.getByText("HIGH")).toBeInTheDocument();
    });
  });

  it("displays status badges", async () => {
    (useFindings as jest.Mock).mockReturnValue({
      data: mockFindings,
      total: 2,
      loading: false,
      error: null,
      selectedFinding: null,
      fetchFindings: vi.fn(),
      fetchFindingDetail: vi.fn(),
      setSelectedFinding: vi.fn(),
    });

    render(<FindingsPage />);

    await waitFor(() => {
      expect(screen.getByText("OPEN")).toBeInTheDocument();
      expect(screen.getByText("IN_PROGRESS")).toBeInTheDocument();
    });
  });

  it("renders error state when API fails", async () => {
    (useFindings as jest.Mock).mockReturnValue({
      data: [],
      total: 0,
      loading: false,
      error: "Failed to fetch findings",
      selectedFinding: null,
      fetchFindings: vi.fn(),
      fetchFindingDetail: vi.fn(),
      setSelectedFinding: vi.fn(),
    });

    render(<FindingsPage />);

    await waitFor(() => {
      expect(screen.getByText(/failed to load findings/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
    });
  });

  it("renders empty state when no findings", async () => {
    (useFindings as jest.Mock).mockReturnValue({
      data: [],
      total: 0,
      loading: false,
      error: null,
      selectedFinding: null,
      fetchFindings: vi.fn(),
      fetchFindingDetail: vi.fn(),
      setSelectedFinding: vi.fn(),
    });

    render(<FindingsPage />);

    await waitFor(() => {
      expect(screen.getByText(/no findings found/i)).toBeInTheDocument();
    });
  });

  it("allows opening detail drawer on row click", async () => {
    const fetchDetailMock = vi.fn().mockResolvedValue(mockFindings[0]);
    (useFindings as jest.Mock).mockReturnValue({
      data: mockFindings,
      total: 2,
      loading: false,
      error: null,
      selectedFinding: mockFindings[0],
      fetchFindings: vi.fn(),
      fetchFindingDetail: fetchDetailMock,
      setSelectedFinding: vi.fn(),
    });

    render(<FindingsPage />);

    // Click on the first row
    const rows = await screen.findAllByText("Web Server 01");
    await userEvent.click(rows[0]);

    await waitFor(() => {
      expect(fetchDetailMock).toHaveBeenCalledWith("1");
    });
  });
});
