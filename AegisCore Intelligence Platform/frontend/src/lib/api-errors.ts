/** Normalize FastAPI `detail` (string | object | list) for UI. */
export function formatApiDetail(detail: unknown): string {
  if (detail == null) return "Request failed";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return JSON.stringify(item);
      })
      .join("; ");
  }
  if (typeof detail === "object" && detail !== null) {
    return JSON.stringify(detail);
  }
  return String(detail);
}
