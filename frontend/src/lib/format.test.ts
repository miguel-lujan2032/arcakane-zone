import { describe, expect, it } from "vitest";
import { formatDate, formatPrice } from "./format";

describe("formatPrice", () => {
  it("formats a price as Colombian pesos with thousands separators", () => {
    expect(formatPrice(89000)).toBe("$89.000");
  });
});

describe("formatDate", () => {
  it("formats an ISO date in Spanish without shifting the day", () => {
    expect(formatDate("2026-02-14")).toBe("14 de febrero de 2026");
  });
});
