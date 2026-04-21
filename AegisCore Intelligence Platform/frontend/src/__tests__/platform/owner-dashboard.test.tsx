/**
 * Owner Dashboard UI Tests
 *
 * Comprehensive test suite for the Platform Owner Dashboard UI.
 * Tests cover route protection, component rendering, and user interactions.
 */

import React from "react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/components/auth/AuthProvider";
import {
  platformMetricsRequest,
  platformTenantsRequest,
  platformTenantDetailRequest,
  platformUploadsImportsRequest,
  platformStorageStatsRequest,
  platformAuditLogsRequest,
  platformAuditLogsSummaryRequest,
} from "@/lib/api";

// Mock Next.js navigation
vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
  usePathname: vi.fn(),
}));

// Mock Auth provider
vi.mock("@/components/auth/AuthProvider", () => ({
  useAuth: vi.fn(),
}));

// Mock API calls
vi.mock("@/lib/api", () => ({
  platformMetricsRequest: vi.fn(),
  platformTenantsRequest: vi.fn(),
  platformTenantDetailRequest: vi.fn(),
  platformTenantAdminsRequest: vi.fn(),
  platformUpdateTenantRequest: vi.fn(),
  platformResetAdminPasswordRequest: vi.fn(),
  platformUploadsImportsRequest: vi.fn(),
  platformUploadsFilesRequest: vi.fn(),
  platformStorageStatsRequest: vi.fn(),
  platformAuditLogsRequest: vi.fn(),
  platformAuditLogsSummaryRequest: vi.fn(),
}));

// Mock components
vi.mock("@/components/ui/Card", () => ({
  Card: ({ children, title }: { children: React.ReactNode; title?: string }) => (
    <div data-testid="card">
      {title && <h2 data-testid="card-title">{title}</h2>}
      {children}
    </div>
  ),
}));

vi.mock("@/components/ui/Button", () => ({
  Button: ({ children, onClick, disabled }: any) => (
    <button onClick={onClick} disabled={disabled} data-testid="button">
      {children}
    </button>
  ),
}));

vi.mock("@/components/ui/Input", () => ({
  Input: ({ value, onChange, placeholder }: any) => (
    <input
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      data-testid="input"
    />
  ),
}));

describe("Platform Owner Dashboard - Route Protection", () => {
  const mockRouter = { replace: vi.fn(), push: vi.fn() };
  const mockUseAuth = useAuth as ReturnType<typeof vi.fn>;
  const mockUseRouter = useRouter as ReturnType<typeof vi.fn>;
  const mockUsePathname = usePathname as ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseRouter.mockReturnValue(mockRouter as any);
    mockUsePathname.mockReturnValue("/platform");
  });

  describe("Test 1: super_admin can access owner pages", () => {
    it("should allow platform_owner to access platform dashboard", async () => {
      mockUseAuth.mockReturnValue({
        user: { id: "1", email: "platform@aegis.local", roles: ["platform_owner"] },
        hasRole: (role: string) => role === "platform_owner",
        isAuthenticated: true,
      } as any);

      platformMetricsRequest.mockResolvedValue({
        ok: true,
        data: {
          total_tenants: 10,
          active_tenants: 8,
          pending_tenants: 2,
          total_users: 50,
          active_users: 45,
          total_invitations_sent: 20,
          pending_invitations: 5,
          recent_signups_7d: 3,
          recent_signups_30d: 8,
        },
      });

      platformTenantsRequest.mockResolvedValue({
        ok: true,
        data: { items: [], total: 0 },
      });

      const PlatformPage = (await import("@/app/(dashboard)/platform/page")).default;
      render(<PlatformPage />);

      await waitFor(() => {
        expect(mockRouter.replace).not.toHaveBeenCalled();
      });
    });

    it("should display platform management content for owner", async () => {
      mockUseAuth.mockReturnValue({
        user: { id: "1", roles: ["platform_owner"] },
        hasRole: (role: string) => role === "platform_owner",
        isAuthenticated: true,
      } as any);

      platformMetricsRequest.mockResolvedValue({
        ok: true,
        data: {
          total_tenants: 5,
          active_tenants: 4,
          pending_tenants: 1,
          total_users: 25,
          active_users: 20,
          total_invitations_sent: 10,
          pending_invitations: 2,
          recent_signups_7d: 1,
          recent_signups_30d: 3,
        },
      });

      platformTenantsRequest.mockResolvedValue({
        ok: true,
        data: { items: [], total: 0 },
      });

      const PlatformPage = (await import("@/app/(dashboard)/platform/page")).default;
      render(<PlatformPage />);

      await waitFor(() => {
        expect(screen.getByText("Platform Management")).toBeInTheDocument();
        expect(screen.getByText("Total Companies")).toBeInTheDocument();
      });
    });
  });

  describe("Test 2: company_admin blocked from owner pages", () => {
    it("should redirect company_admin away from platform dashboard", async () => {
      mockUseAuth.mockReturnValue({
        user: { id: "2", email: "admin@company.com", roles: ["admin"] },
        hasRole: (role: string) => role === "admin",
        isAuthenticated: true,
      } as any);

      const PlatformPage = (await import("@/app/(dashboard)/platform/page")).default;
      render(<PlatformPage />);

      await waitFor(() => {
        expect(mockRouter.replace).toHaveBeenCalledWith("/dashboard");
      });
    });

    it("should redirect analyst away from platform dashboard", async () => {
      mockUseAuth.mockReturnValue({
        user: { id: "3", email: "analyst@company.com", roles: ["analyst"] },
        hasRole: (role: string) => role === "analyst",
        isAuthenticated: true,
      } as any);

      const PlatformPage = (await import("@/app/(dashboard)/platform/page")).default;
      render(<PlatformPage />);

      await waitFor(() => {
        expect(mockRouter.replace).toHaveBeenCalledWith("/dashboard");
      });
    });

    it("should show access denied in layout for non-platform-owner", async () => {
      mockUseAuth.mockReturnValue({
        user: { id: "2", roles: ["admin"] },
        hasRole: () => false,
        isAuthenticated: true,
      } as any);

      const PlatformLayout = (await import("@/app/(dashboard)/platform/layout")).default;
      render(
        <PlatformLayout>
          <div>Content</div>
        </PlatformLayout>
      );

      await waitFor(() => {
        expect(screen.getByText("Access Denied")).toBeInTheDocument();
        expect(screen.getByText(/do not have permission/i)).toBeInTheDocument();
      });
    });
  });
});

describe("Platform Owner Dashboard - Companies Page", () => {
  const mockRouter = { replace: vi.fn(), push: vi.fn() };
  const mockUseAuth = useAuth as ReturnType<typeof vi.fn>;
  const mockUseRouter = useRouter as ReturnType<typeof vi.fn>;
  const mockPlatformTenantsRequest = platformTenantsRequest as ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseRouter.mockReturnValue(mockRouter as any);
    mockUseAuth.mockReturnValue({
      user: { id: "1", roles: ["platform_owner"] },
      hasRole: (role: string) => role === "platform_owner",
      isAuthenticated: true,
    } as any);
  });

  describe("Test 3: companies list renders correctly", () => {
    it("should display companies table with correct columns", async () => {
      const mockTenants = [
        {
          id: "tenant-1",
          name: "Test Company 1",
          code: "test-1",
          is_active: true,
          approval_status: "approved",
          created_at: "2024-01-01T00:00:00Z",
        },
        {
          id: "tenant-2",
          name: "Test Company 2",
          code: "test-2",
          is_active: false,
          approval_status: "pending",
          created_at: "2024-01-02T00:00:00Z",
        },
      ];

      mockPlatformTenantsRequest.mockResolvedValue({
        ok: true,
        data: { items: mockTenants, total: 2 },
      });

      const TenantsPage = (await import("@/app/(dashboard)/platform/tenants/page")).default;
      render(<TenantsPage />);

      await waitFor(() => {
        expect(screen.getByText("Companies")).toBeInTheDocument();
        expect(screen.getByText("Test Company 1")).toBeInTheDocument();
        expect(screen.getByText("Test Company 2")).toBeInTheDocument();
      });
    });

    it("should show loading state initially", async () => {
      mockPlatformTenantsRequest.mockImplementation(() => new Promise(() => {}));

      const TenantsPage = (await import("@/app/(dashboard)/platform/tenants/page")).default;
      render(<TenantsPage />);

      expect(screen.getByText(/loading companies/i)).toBeInTheDocument();
    });

    it("should show empty state when no companies exist", async () => {
      mockPlatformTenantsRequest.mockResolvedValue({
        ok: true,
        data: { items: [], total: 0 },
      });

      const TenantsPage = (await import("@/app/(dashboard)/platform/tenants/page")).default;
      render(<TenantsPage />);

      await waitFor(() => {
        expect(screen.getByText(/no companies found/i)).toBeInTheDocument();
      });
    });
  });

  describe("Test 4: status updates reflect in UI", () => {
    it("should display correct status badges", async () => {
      const mockTenants = [
        {
          id: "tenant-1",
          name: "Active Company",
          code: "active",
          is_active: true,
          approval_status: "approved",
          created_at: "2024-01-01T00:00:00Z",
        },
        {
          id: "tenant-2",
          name: "Suspended Company",
          code: "suspended",
          is_active: false,
          approval_status: "approved",
          created_at: "2024-01-01T00:00:00Z",
        },
      ];

      mockPlatformTenantsRequest.mockResolvedValue({
        ok: true,
        data: { items: mockTenants, total: 2 },
      });

      const TenantsPage = (await import("@/app/(dashboard)/platform/tenants/page")).default;
      render(<TenantsPage />);

      await waitFor(() => {
        const activeBadges = screen.getAllByText("Active");
        expect(activeBadges.length).toBeGreaterThan(0);
      });
    });

    it("should show approval status badges correctly", async () => {
      const mockTenants = [
        {
          id: "tenant-1",
          name: "Approved Company",
          code: "approved",
          is_active: true,
          approval_status: "approved",
          created_at: "2024-01-01T00:00:00Z",
        },
        {
          id: "tenant-2",
          name: "Pending Company",
          code: "pending",
          is_active: true,
          approval_status: "pending",
          created_at: "2024-01-01T00:00:00Z",
        },
      ];

      mockPlatformTenantsRequest.mockResolvedValue({
        ok: true,
        data: { items: mockTenants, total: 2 },
      });

      const TenantsPage = (await import("@/app/(dashboard)/platform/tenants/page")).default;
      render(<TenantsPage />);

      await waitFor(() => {
        expect(screen.getByText("Approved")).toBeInTheDocument();
        expect(screen.getByText("Pending")).toBeInTheDocument();
      });
    });
  });

  describe("Company filtering", () => {
    it("should filter companies by search query", async () => {
      const mockTenants = [
        { id: "1", name: "Alpha Corp", code: "alpha", is_active: true, approval_status: "approved", created_at: "2024-01-01T00:00:00Z" },
        { id: "2", name: "Beta Inc", code: "beta", is_active: true, approval_status: "approved", created_at: "2024-01-01T00:00:00Z" },
      ];

      mockPlatformTenantsRequest.mockResolvedValue({
        ok: true,
        data: { items: mockTenants, total: 2 },
      });

      const TenantsPage = (await import("@/app/(dashboard)/platform/tenants/page")).default;
      render(<TenantsPage />);

      await waitFor(() => {
        expect(screen.getByText("Alpha Corp")).toBeInTheDocument();
        expect(screen.getByText("Beta Inc")).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText(/search companies/i);
      fireEvent.change(searchInput, { target: { value: "alpha" } });

      await waitFor(() => {
        expect(screen.getByText("Alpha Corp")).toBeInTheDocument();
        expect(screen.queryByText("Beta Inc")).not.toBeInTheDocument();
      });
    });
  });
});

describe("Platform Owner Dashboard - Company Details", () => {
  const mockRouter = { replace: vi.fn(), push: vi.fn() };
  const mockUseAuth = useAuth as ReturnType<typeof vi.fn>;
  const mockUseRouter = useRouter as ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseRouter.mockReturnValue(mockRouter as any);
    mockUseAuth.mockReturnValue({
      user: { id: "1", roles: ["platform_owner"] },
      hasRole: (role: string) => role === "platform_owner",
      isAuthenticated: true,
    } as any);
  });

  it("should display company details with stats", async () => {
    const mockTenantDetail = {
      id: "tenant-1",
      name: "Test Company",
      code: "test-co",
      is_active: true,
      approval_status: "approved",
      created_at: "2024-01-01T00:00:00Z",
      user_count: 10,
    };

    const mockAdmins = [
      { id: "admin-1", full_name: "Admin User", email: "admin@test.com", is_active: true, created_at: "2024-01-01T00:00:00Z" },
    ];

    (platformTenantDetailRequest as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: true,
        data: mockTenantDetail,
      });

      const { platformTenantAdminsRequest } = await import("@/lib/api");
      (platformTenantAdminsRequest as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: true,
        data: mockAdmins,
      });

    const TenantDetailPage = (await import("@/app/(dashboard)/platform/tenants/[id]/page")).default;
    render(<TenantDetailPage params={Promise.resolve({ id: "tenant-1" })} />);

    await waitFor(() => {
      expect(screen.getByText("Test Company")).toBeInTheDocument();
      expect(screen.getByText("Code: test-co")).toBeInTheDocument();
    });
  });
});

describe("Platform Owner Dashboard - Uploads Page", () => {
  const mockRouter = { replace: vi.fn(), push: vi.fn() };
  const mockUseAuth = useAuth as ReturnType<typeof vi.fn>;
  const mockUseRouter = useRouter as ReturnType<typeof vi.fn>;
  const mockPlatformUploadsImportsRequest = platformUploadsImportsRequest as ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseRouter.mockReturnValue(mockRouter as any);
    mockUseAuth.mockReturnValue({
      user: { id: "1", roles: ["platform_owner"] },
      hasRole: (role: string) => role === "platform_owner",
      isAuthenticated: true,
    } as any);
  });

  describe("Test 5: uploads list renders correctly", () => {
    it("should display imports tab by default", async () => {
      mockPlatformUploadsImportsRequest.mockResolvedValue({
        ok: true,
        data: { items: [], total: 0 },
      });

      const { platformUploadsFilesRequest } = await import("@/lib/api");
      platformUploadsFilesRequest.mockResolvedValue({
        ok: true,
        data: { items: [], total: 0, total_storage_bytes: 0 },
      });

      const UploadsPage = (await import("@/app/(dashboard)/platform/uploads/page")).default;
      render(<UploadsPage />);

      await waitFor(() => {
        expect(screen.getByText("Upload Monitoring")).toBeInTheDocument();
        expect(screen.getByText("Data Imports")).toBeInTheDocument();
      });
    });

    it("should display upload details in table", async () => {
      const mockImports = [
        {
          id: "import-1",
          tenant_id: "tenant-1",
          upload_type: "assets_import",
          original_filename: "assets.csv",
          file_size_bytes: 1024,
          status: "completed",
          summary: { total_rows: 100, inserted: 90, updated: 5, failed: 5, skipped: 0, errors: [] },
          processing_time_ms: 1500,
          uploaded_by_user_id: "user-1",
          created_at: "2024-01-01T00:00:00Z",
          completed_at: "2024-01-01T00:00:01Z",
        },
      ];

      mockPlatformUploadsImportsRequest.mockResolvedValue({
        ok: true,
        data: { items: mockImports, total: 1 },
      });

      const { platformUploadsFilesRequest } = await import("@/lib/api");
      platformUploadsFilesRequest.mockResolvedValue({
        ok: true,
        data: { items: [], total: 0, total_storage_bytes: 0 },
      });

      const UploadsPage = (await import("@/app/(dashboard)/platform/uploads/page")).default;
      render(<UploadsPage />);

      await waitFor(() => {
        expect(screen.getByText("assets.csv")).toBeInTheDocument();
        expect(screen.getByText("completed")).toBeInTheDocument();
      });
    });

    it("should switch between imports and files tabs", async () => {
      mockPlatformUploadsImportsRequest.mockResolvedValue({
        ok: true,
        data: { items: [], total: 0 },
      });

      const { platformUploadsFilesRequest } = await import("@/lib/api");
      platformUploadsFilesRequest.mockResolvedValue({
        ok: true,
        data: {
          items: [
            {
              id: "file-1",
              tenant_id: "tenant-1",
              upload_type: "document",
              original_filename: "report.pdf",
              storage_path: "/path/to/file",
              file_size_bytes: 2048,
              mime_type: "application/pdf",
              uploaded_by_user_id: "user-1",
              created_at: "2024-01-01T00:00:00Z",
            },
          ],
          total: 1,
          total_storage_bytes: 2048,
        },
      });

      const UploadsPage = (await import("@/app/(dashboard)/platform/uploads/page")).default;
      render(<UploadsPage />);

      await waitFor(() => {
        expect(screen.getByText("Data Imports")).toBeInTheDocument();
      });

      // Click on Files tab
      fireEvent.click(screen.getByText("File Uploads"));

      await waitFor(() => {
        expect(screen.getByText("report.pdf")).toBeInTheDocument();
      });
    });
  });
});

describe("Platform Owner Dashboard - Storage Page", () => {
  const mockRouter = { replace: vi.fn(), push: vi.fn() };
  const mockUseAuth = useAuth as ReturnType<typeof vi.fn>;
  const mockUseRouter = useRouter as ReturnType<typeof vi.fn>;
  const mockPlatformStorageStatsRequest = platformStorageStatsRequest as ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseRouter.mockReturnValue(mockRouter as any);
    mockUseAuth.mockReturnValue({
      user: { id: "1", roles: ["platform_owner"] },
      hasRole: (role: string) => role === "platform_owner",
      isAuthenticated: true,
    } as any);
  });

  it("should display storage statistics", async () => {
    mockPlatformStorageStatsRequest.mockResolvedValue({
      ok: true,
      data: {
        total_storage_bytes: 1073741824, // 1 GB
        total_files: 150,
        tenants: [
          { tenant_id: "tenant-1", storage_bytes: 536870912, file_count: 75 },
          { tenant_id: "tenant-2", storage_bytes: 268435456, file_count: 40 },
          { tenant_id: "tenant-3", storage_bytes: 268435456, file_count: 35 },
        ],
      },
    });

    const StoragePage = (await import("@/app/(dashboard)/platform/storage/page")).default;
    render(<StoragePage />);

    await waitFor(() => {
      expect(screen.getByText("Storage Overview")).toBeInTheDocument();
      expect(screen.getByText("1 GB")).toBeInTheDocument();
      expect(screen.getByText("150")).toBeInTheDocument();
    });
  });

  it("should show storage distribution by company", async () => {
    mockPlatformStorageStatsRequest.mockResolvedValue({
      ok: true,
      data: {
        total_storage_bytes: 1000000,
        total_files: 50,
        tenants: [
          { tenant_id: "tenant-1", storage_bytes: 600000, file_count: 30 },
          { tenant_id: "tenant-2", storage_bytes: 400000, file_count: 20 },
        ],
      },
    });

    const StoragePage = (await import("@/app/(dashboard)/platform/storage/page")).default;
    render(<StoragePage />);

    await waitFor(() => {
      expect(screen.getByText("Storage by Company")).toBeInTheDocument();
      expect(screen.getByText(/tenant-1/)).toBeInTheDocument();
    });
  });
});

describe("Platform Owner Dashboard - Audit Logs Page", () => {
  const mockRouter = { replace: vi.fn(), push: vi.fn() };
  const mockUseAuth = useAuth as ReturnType<typeof vi.fn>;
  const mockUseRouter = useRouter as ReturnType<typeof vi.fn>;
  const mockPlatformAuditLogsRequest = platformAuditLogsRequest as ReturnType<typeof vi.fn>;
  const mockPlatformAuditLogsSummaryRequest = platformAuditLogsSummaryRequest as ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseRouter.mockReturnValue(mockRouter as any);
    mockUseAuth.mockReturnValue({
      user: { id: "1", roles: ["platform_owner"] },
      hasRole: (role: string) => role === "platform_owner",
      isAuthenticated: true,
    } as any);
  });

  describe("Test 6: audit logs render correctly", () => {
    it("should display audit logs with filters", async () => {
      const mockLogs = [
        {
          id: "log-1",
          tenant_id: "tenant-1",
          tenant_name: "Test Company",
          actor_user_id: "user-1",
          actor_email: "user@test.com",
          action: "LOGIN",
          resource_type: "authentication",
          resource_id: "session-1",
          payload: null,
          occurred_at: "2024-01-01T00:00:00Z",
        },
      ];

      const mockSummary = {
        period_days: 7,
        total_actions: 100,
        actions_by_type: [{ action: "LOGIN", count: 50 }],
        actions_by_tenant: [{ tenant_id: "tenant-1", count: 50 }],
        daily_trend: [{ date: "2024-01-01", count: 10 }],
      };

      mockPlatformAuditLogsRequest.mockResolvedValue({
        ok: true,
        data: { items: mockLogs, total: 1 },
      });

      mockPlatformAuditLogsSummaryRequest.mockResolvedValue({
        ok: true,
        data: mockSummary,
      });

      const AuditPage = (await import("@/app/(dashboard)/platform/audit/page")).default;
      render(<AuditPage />);

      await waitFor(() => {
        expect(screen.getByText("Audit Logs")).toBeInTheDocument();
        expect(screen.getByText("LOGIN")).toBeInTheDocument();
        expect(screen.getByText("user@test.com")).toBeInTheDocument();
      });
    });

    it("should display audit summary statistics", async () => {
      const mockSummary = {
        period_days: 7,
        total_actions: 250,
        actions_by_type: [
          { action: "LOGIN", count: 100 },
          { action: "FILE_UPLOAD", count: 50 },
        ],
        actions_by_tenant: [{ tenant_id: "tenant-1", count: 150 }],
        daily_trend: [{ date: "2024-01-01", count: 30 }],
      };

      mockPlatformAuditLogsRequest.mockResolvedValue({
        ok: true,
        data: { items: [], total: 0 },
      });

      mockPlatformAuditLogsSummaryRequest.mockResolvedValue({
        ok: true,
        data: mockSummary,
      });

      const AuditPage = (await import("@/app/(dashboard)/platform/audit/page")).default;
      render(<AuditPage />);

      await waitFor(() => {
        expect(screen.getByText("250")).toBeInTheDocument();
        expect(screen.getByText("Total Actions")).toBeInTheDocument();
      });
    });
  });
});

describe("Platform Owner Dashboard - Loading, Error, Empty States", () => {
  const mockRouter = { replace: vi.fn(), push: vi.fn() };
  const mockUseAuth = useAuth as ReturnType<typeof vi.fn>;
  const mockUseRouter = useRouter as ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseRouter.mockReturnValue(mockRouter as any);
    mockUseAuth.mockReturnValue({
      user: { id: "1", roles: ["platform_owner"] },
      hasRole: (role: string) => role === "platform_owner",
      isAuthenticated: true,
    } as any);
  });

  describe("Test 7: loading/error/empty states work", () => {
    it("should show loading state on platform page", async () => {
      (platformMetricsRequest as ReturnType<typeof vi.fn>).mockImplementation(() => new Promise(() => {}));
      (platformTenantsRequest as ReturnType<typeof vi.fn>).mockImplementation(() => new Promise(() => {}));

      const PlatformPage = (await import("@/app/(dashboard)/platform/page")).default;
      render(<PlatformPage />);

      expect(screen.getByText(/loading platform data/i)).toBeInTheDocument();
    });

    it("should show error state on API failure", async () => {
      (platformMetricsRequest as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: false,
        error: "API Error",
      });
      (platformTenantsRequest as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: false,
        error: "API Error",
      });

      const PlatformPage = (await import("@/app/(dashboard)/platform/page")).default;
      render(<PlatformPage />);

      await waitFor(() => {
        expect(screen.getByText(/failed to load platform data/i)).toBeInTheDocument();
      });
    });

    it("should handle network errors gracefully", async () => {
      (platformMetricsRequest as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("Network error"));
      (platformTenantsRequest as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("Network error"));

      const PlatformPage = (await import("@/app/(dashboard)/platform/page")).default;
      render(<PlatformPage />);

      await waitFor(() => {
        expect(screen.getByText(/failed to load platform data/i)).toBeInTheDocument();
      });
    });
  });
});

describe("Platform Owner Dashboard - Navigation", () => {
  const mockRouter = { replace: vi.fn(), push: vi.fn() };
  const mockUseAuth = useAuth as ReturnType<typeof vi.fn>;
  const mockUseRouter = useRouter as ReturnType<typeof vi.fn>;
  const mockUsePathname = usePathname as ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseRouter.mockReturnValue(mockRouter as any);
    mockUsePathname.mockReturnValue("/platform");
    mockUseAuth.mockReturnValue({
      user: { id: "1", roles: ["platform_owner"] },
      hasRole: (role: string) => role === "platform_owner",
      isAuthenticated: true,
    } as any);
  });

  it("should render sidebar navigation with all items", async () => {
    const PlatformLayout = (await import("@/app/(dashboard)/platform/layout")).default;
    render(
      <PlatformLayout>
        <div data-testid="page-content">Page Content</div>
      </PlatformLayout>
    );

    await waitFor(() => {
      expect(screen.getByText("Overview")).toBeInTheDocument();
      expect(screen.getByText("Companies")).toBeInTheDocument();
      expect(screen.getByText("Uploads")).toBeInTheDocument();
      expect(screen.getByText("Storage")).toBeInTheDocument();
      expect(screen.getByText("Audit Logs")).toBeInTheDocument();
    });
  });

  it("should highlight active navigation item", async () => {
    mockUsePathname.mockReturnValue("/platform/tenants");

    const PlatformLayout = (await import("@/app/(dashboard)/platform/layout")).default;
    render(
      <PlatformLayout>
        <div>Page Content</div>
      </PlatformLayout>
    );

    await waitFor(() => {
      const companiesButton = screen.getByText("Companies").closest("button");
      expect(companiesButton).toHaveClass("bg-indigo-500/10");
    });
  });

  it("should navigate to different pages when clicking nav items", async () => {
    const PlatformLayout = (await import("@/app/(dashboard)/platform/layout")).default;
    render(
      <PlatformLayout>
        <div>Page Content</div>
      </PlatformLayout>
    );

    fireEvent.click(screen.getByText("Companies"));

    expect(mockRouter.push).toHaveBeenCalledWith("/platform/tenants");
  });

  it("should have exit platform button", async () => {
    const PlatformLayout = (await import("@/app/(dashboard)/platform/layout")).default;
    render(
      <PlatformLayout>
        <div>Page Content</div>
      </PlatformLayout>
    );

    await waitFor(() => {
      expect(screen.getByText("Exit Platform")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Exit Platform"));
    expect(mockRouter.push).toHaveBeenCalledWith("/dashboard");
  });
});
