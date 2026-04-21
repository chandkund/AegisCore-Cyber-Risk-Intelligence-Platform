import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AuthProvider } from "@/components/auth/AuthProvider";
import LoginPage from "@/app/login/page";
import { loginRequest } from "@/lib/api";

// Mock the API module
vi.mock("@/lib/api", () => ({
  loginRequest: vi.fn(),
  meRequest: vi.fn(),
  logoutRequest: vi.fn(),
}));

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: vi.fn(),
    push: vi.fn(),
  }),
}));

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Clear session storage
    sessionStorage.clear();
  });

  it("renders login form with email and password inputs", () => {
    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    );

    expect(screen.getByLabelText(/company code/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("shows error message when login fails", async () => {
    const mockedLoginRequest = loginRequest as unknown as ReturnType<typeof vi.fn>;
    mockedLoginRequest.mockResolvedValue({
      ok: false,
      error: "Invalid credentials",
    });

    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    );

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "test@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/company code/i), {
      target: { value: "acme" },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: "wrongpassword" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/invalid credentials/i);
    });
  });

  it("calls login API with correct credentials", async () => {
    const mockedLoginRequest = loginRequest as unknown as ReturnType<typeof vi.fn>;
    mockedLoginRequest.mockResolvedValue({
      ok: true,
      tokens: {
        access_token: "test-access-token",
        refresh_token: "test-refresh-token",
        token_type: "bearer",
        expires_in: 1800,
      },
    });

    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    );

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "admin@aegiscore.local" },
    });
    fireEvent.change(screen.getByLabelText(/company code/i), {
      target: { value: "default" },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: "admin123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(mockedLoginRequest).toHaveBeenCalledWith("default", "admin@aegiscore.local", "admin123");
    });
  });

  it("disables submit button while submitting", async () => {
    const mockedLoginRequest = loginRequest as unknown as ReturnType<typeof vi.fn>;
    mockedLoginRequest.mockImplementation(() => new Promise(() => {})); // Never resolves

    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    );

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "test@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/company code/i), {
      target: { value: "acme" },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: "password" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      const submitButton = screen.getByRole("button", { name: /signing in/i });
      expect(submitButton).toBeDisabled();
      expect(submitButton).toHaveTextContent(/signing in/i);
    });
  });
});
