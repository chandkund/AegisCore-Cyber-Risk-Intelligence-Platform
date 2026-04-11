import { afterEach, describe, expect, it } from "vitest";
import {
  clearTokens,
  getAccessToken,
  hasSession,
  setTokens,
} from "@/lib/auth-storage";

describe("auth-storage", () => {
  afterEach(() => {
    sessionStorage.clear();
  });

  it("round-trips tokens and hasSession", () => {
    expect(hasSession()).toBe(false);
    setTokens("a", "b");
    expect(getAccessToken()).toBe("a");
    expect(hasSession()).toBe(true);
    clearTokens();
    expect(hasSession()).toBe(false);
  });
});
