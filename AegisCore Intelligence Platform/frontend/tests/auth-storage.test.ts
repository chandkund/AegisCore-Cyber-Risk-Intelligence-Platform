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

  it("tracks session state without exposing tokens", () => {
    expect(hasSession()).toBe(false);
    setTokens("a", "b");
    expect(getAccessToken()).toBeNull();
    expect(hasSession()).toBe(true);
    clearTokens();
    expect(hasSession()).toBe(false);
  });
});
