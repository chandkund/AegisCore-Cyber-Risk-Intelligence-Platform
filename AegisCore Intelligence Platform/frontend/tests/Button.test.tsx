import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Button } from "@/components/ui/Button";

describe("Button", () => {
  it("renders label and respects disabled", () => {
    render(<Button disabled>Save</Button>);
    const btn = screen.getByRole("button", { name: "Save" });
    expect(btn).toBeDisabled();
  });
});
