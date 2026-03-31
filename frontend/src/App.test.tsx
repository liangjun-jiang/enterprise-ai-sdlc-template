import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import App from "./App";

describe("App", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: "ok" }),
      })
    );
  });

  it("renders the main heading", () => {
    render(<App />);
    expect(
      screen.getByRole("heading", { name: /Enterprise AI-SDLC Template/i })
    ).toBeInTheDocument();
  });
});
