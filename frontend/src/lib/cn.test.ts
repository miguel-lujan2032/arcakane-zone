import { describe, expect, it } from "vitest";
import { cn } from "./cn";

describe("cn", () => {
  it("combines conditional classes into a single string", () => {
    const active = true;

    expect(cn("px-3", active && "text-brand-200", !active && "text-slate-400")).toBe(
      "px-3 text-brand-200",
    );
  });

  it("resolves conflicting Tailwind utilities keeping the last one", () => {
    const result = cn("px-3 py-2", "px-4");

    expect(result).toContain("py-2");
    expect(result).toContain("px-4");
    expect(result).not.toContain("px-3");
  });
});
