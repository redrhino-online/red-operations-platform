import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/command-center",
}));

import { AppNav } from "./AppNav";
import { RED_SCREENS } from "./screens";

describe("AppNav", () => {
  it("links every RED screen from the single source of truth", () => {
    render(<AppNav />);
    for (const item of RED_SCREENS) {
      const link = screen.getByRole("link", { name: item.label });
      expect(link).toHaveAttribute("href", item.route);
    }
  });

  it("marks the active route", () => {
    render(<AppNav />);
    expect(
      screen.getByRole("link", { name: "Portfolio command center" }),
    ).toHaveAttribute("aria-current", "page");
    expect(
      screen.getByRole("link", { name: "Build board" }),
    ).not.toHaveAttribute("aria-current");
  });
});
