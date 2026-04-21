/**
 * Cookie-Based Auth Session Tracking
 *
 * With HTTPOnly cookie auth, tokens are NOT stored in JavaScript.
 * This module only tracks session existence for UI state management.
 * Actual tokens are in secure HTTPOnly cookies (inaccessible to JS).
 */

const SESSION_KEY = "aegiscore_session_active";

/**
 * Check if user has an active session (based on local UI state).
 * Note: Actual auth validation is done server-side via HTTPOnly cookies.
 */
export function hasSession(): boolean {
  if (typeof window === "undefined") return false;
  return sessionStorage.getItem(SESSION_KEY) === "true";
}

/**
 * Mark session as active (after successful login).
 * Does NOT store tokens - they are in HTTPOnly cookies.
 */
export function setSessionActive(): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(SESSION_KEY, "true");
}

/**
 * Clear session state (after logout or auth failure).
 * Does NOT clear cookies - server handles that.
 */
export function clearSession(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(SESSION_KEY);
}

// Legacy exports for backward compatibility - always return null
// because tokens are stored in HTTPOnly cookies only
export function getAccessToken(): null {
  // Tokens are in HTTPOnly cookies, not accessible to JavaScript
  return null;
}

export function getRefreshToken(): null {
  // Tokens are in HTTPOnly cookies, not accessible to JavaScript
  return null;
}

/** @deprecated Tokens are in HTTPOnly cookies - use setSessionActive() instead */
export function setTokens(_access: string, _refresh: string): void {
  // Tokens are now stored in HTTPOnly cookies by the server
  // Just mark the session as active for UI state
  setSessionActive();
}

/** @deprecated Use clearSession() instead */
export function clearTokens(): void {
  clearSession();
}
