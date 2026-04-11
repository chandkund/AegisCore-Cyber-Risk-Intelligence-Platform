import { describe, expect, it } from "vitest";
import { formatApiDetail } from "@/lib/api-errors";

describe("formatApiDetail", () => {
  it("returns string detail as-is", () => {
    expect(formatApiDetail("Not found")).toBe("Not found");
  });

  it("joins validation error array", () => {
    expect(
      formatApiDetail([
        { loc: ["body", "email"], msg: "invalid email", type: "value_error" },
      ])
    ).toBe("invalid email");
  });

  it("handles null", () => {
    expect(formatApiDetail(null)).toBe("Request failed");
  });
});
