import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

import { RED_SCREENS } from "@/shared/nav/screens";
import Home from "./page";

describe("Home", () => {
  it("links every RED screen", () => {
    render(<Home />);
    for (const item of RED_SCREENS) {
      expect(
        screen.getByRole("link", { name: item.label }),
      ).toHaveAttribute("href", item.route);
    }
  });

  it("does not claim the screens are unimplemented", () => {
    render(<Home />);
    expect(screen.queryByText(/not yet implemented/i)).not.toBeInTheDocument();
  });
});
