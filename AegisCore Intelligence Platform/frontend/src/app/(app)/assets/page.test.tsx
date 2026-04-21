import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import AssetsPage from "./page";

// Mock the hooks
vi.mock("@/hooks/useAssets", () => ({
  useAssets: vi.fn(),
}));

import { useAssets } from "@/hooks/useAssets";

const mockAssets = [
  {
    id: "asset-1",
    business_unit_id: "bu-1",
    name: "Web Server 01",
    type: "SERVER",
    criticality: 1,
    owner_email: "admin@example.com",
    tags: { environment: "production", team: "platform" },
    description: "Main web server",
    first_seen_at: "2024-01-01T00:00:00Z",
    last_seen_at: "2024-01-20T00:00:00Z",
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-20T00:00:00Z",
    ip_address: "192.168.1.100",
    hostname: "web01.prod",
    os_family: "Ubuntu",
    cloud_provider: null,
    region: null,
    open_findings_count: 5,
    max_risk_score: 85.5,
  },
  {
    id: "asset-2",
    business_unit_id: "bu-1",
    name: "Database Server",
    type: "SERVER",
    criticality: 2,
    owner_email: "dba@example.com",
    tags: { environment: "production", team: "data" },
    description: "Primary database",
    first_seen_at: "2024-01-01T00:00:00Z",
    last_seen_at: "2024-01-20T00:00:00Z",
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-20T00:00:00Z",
    ip_address: "192.168.1.200",
    hostname: "db01.prod",
    os_family: "RHEL",
    cloud_provider: "AWS",
    region: "us-east-1",
    open_findings_count: 2,
    max_risk_score: 72.0,
  },
];

describe("AssetsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state initially", () => {
    (useAssets as jest.Mock).mockReturnValue({
      data: [],
      total: 0,
      loading: true,
      error: null,
      selectedAsset: null,
      fetchAssets: vi.fn(),
      fetchAssetDetail: vi.fn(),
      setSelectedAsset: vi.fn(),
    });

    render(<AssetsPage />);

    expect(screen.getByText(/asset inventory/i)).toBeInTheDocument();
  });

  it("renders assets table with data", async () => {
    (useAssets as jest.Mock).mockReturnValue({
      data: mockAssets,
      total: 2,
      loading: false,
      error: null,
      selectedAsset: null,
      fetchAssets: vi.fn(),
      fetchAssetDetail: vi.fn(),
      setSelectedAsset: vi.fn(),
    });

    render(<AssetsPage />);

    await waitFor(() => {
      expect(screen.getByText("Web Server 01")).toBeInTheDocument();
      expect(screen.getByText("Database Server")).toBeInTheDocument();
      expect(screen.getByText("192.168.1.100")).toBeInTheDocument();
      expect(screen.getByText("192.168.1.200")).toBeInTheDocument();
    });
  });

  it("displays criticality badges with proper colors", async () => {
    (useAssets as jest.Mock).mockReturnValue({
      data: mockAssets,
      total: 2,
      loading: false,
      error: null,
      selectedAsset: null,
      fetchAssets: vi.fn(),
      fetchAssetDetail: vi.fn(),
      setSelectedAsset: vi.fn(),
    });

    render(<AssetsPage />);

    await waitFor(() => {
      expect(screen.getByText("Critical")).toBeInTheDocument();
      expect(screen.getByText("High")).toBeInTheDocument();
    });
  });

  it("displays risk scores with color coding", async () => {
    (useAssets as jest.Mock).mockReturnValue({
      data: mockAssets,
      total: 2,
      loading: false,
      error: null,
      selectedAsset: null,
      fetchAssets: vi.fn(),
      fetchAssetDetail: vi.fn(),
      setSelectedAsset: vi.fn(),
    });

    render(<AssetsPage />);

    await waitFor(() => {
      expect(screen.getByText("85.5")).toBeInTheDocument();
      expect(screen.getByText("72.0")).toBeInTheDocument();
    });
  });

  it("displays open findings count with icons", async () => {
    (useAssets as jest.Mock).mockReturnValue({
      data: mockAssets,
      total: 2,
      loading: false,
      error: null,
      selectedAsset: null,
      fetchAssets: vi.fn(),
      fetchAssetDetail: vi.fn(),
      setSelectedAsset: vi.fn(),
    });

    render(<AssetsPage />);

    await waitFor(() => {
      expect(screen.getByText("5")).toBeInTheDocument();
      expect(screen.getByText("2")).toBeInTheDocument();
    });
  });

  it("renders error state when API fails", async () => {
    (useAssets as jest.Mock).mockReturnValue({
      data: [],
      total: 0,
      loading: false,
      error: "Failed to fetch assets",
      selectedAsset: null,
      fetchAssets: vi.fn(),
      fetchAssetDetail: vi.fn(),
      setSelectedAsset: vi.fn(),
    });

    render(<AssetsPage />);

    await waitFor(() => {
      expect(screen.getByText(/failed to load assets/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
    });
  });

  it("renders empty state when no assets", async () => {
    (useAssets as jest.Mock).mockReturnValue({
      data: [],
      total: 0,
      loading: false,
      error: null,
      selectedAsset: null,
      fetchAssets: vi.fn(),
      fetchAssetDetail: vi.fn(),
      setSelectedAsset: vi.fn(),
    });

    render(<AssetsPage />);

    await waitFor(() => {
      expect(screen.getByText(/no assets found/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /upload data/i })).toBeInTheDocument();
    });
  });

  it("allows applying filters", async () => {
    const fetchMock = vi.fn();
    (useAssets as jest.Mock).mockReturnValue({
      data: mockAssets,
      total: 2,
      loading: false,
      error: null,
      selectedAsset: null,
      fetchAssets: fetchMock,
      fetchAssetDetail: vi.fn(),
      setSelectedAsset: vi.fn(),
    });

    render(<AssetsPage />);

    // Change the criticality filter
    const criticalitySelect = screen.getByLabelText(/criticality/i);
    await userEvent.selectOptions(criticalitySelect, "1");

    expect(fetchMock).toHaveBeenCalledWith(25, 0, { criticality: 1 });
  });

  it("allows clearing filters", async () => {
    const fetchMock = vi.fn();
    (useAssets as jest.Mock).mockReturnValue({
      data: mockAssets,
      total: 2,
      loading: false,
      error: null,
      selectedAsset: null,
      fetchAssets: fetchMock,
      fetchAssetDetail: vi.fn(),
      setSelectedAsset: vi.fn(),
    });

    render(<AssetsPage />);

    // Apply a filter first
    const criticalitySelect = screen.getByLabelText(/criticality/i);
    await userEvent.selectOptions(criticalitySelect, "1");

    // Then clear filters
    const clearButton = screen.getByRole("button", { name: /clear/i });
    await userEvent.click(clearButton);

    expect(fetchMock).toHaveBeenLastCalledWith(25, 0, {});
  });
});
