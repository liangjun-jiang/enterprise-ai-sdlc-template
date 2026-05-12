import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import PRListModal from "./PRListModal";

type FetchMock = ReturnType<typeof vi.fn>;

const makePR = (overrides: Record<string, unknown> = {}) => ({
  number: 1,
  title: "Fix bug in login flow",
  url: "https://github.com/owner/repo/pull/1",
  created_at: "2024-03-15T10:30:00Z",
  merged_at: null,
  state: "open",
  ...overrides,
});

const makeResponse = (prs: ReturnType<typeof makePR>[], page = 1) => ({
  prs,
  total: prs.length,
  page,
  per_page: 30,
});

function stubFetch(data: unknown, ok = true, status = 200): FetchMock {
  const mock = vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => data,
  });
  vi.stubGlobal("fetch", mock);
  return mock;
}

describe("PRListModal", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  describe("loading state", () => {
    it("renders loading indicator while fetching", () => {
      // Never resolves during this test
      vi.stubGlobal(
        "fetch",
        vi.fn().mockReturnValue(new Promise(() => {})),
      );

      render(<PRListModal state="open" onClose={vi.fn()} />);

      expect(screen.getByTestId("pr-list-loading")).toBeInTheDocument();
    });
  });

  describe("success state", () => {
    it("renders list of PRs with title and timestamp after fetch resolves", async () => {
      const prs = [
        makePR({ number: 1, title: "First PR", created_at: "2024-03-15T10:30:00Z" }),
        makePR({ number: 2, title: "Second PR", created_at: "2024-03-14T08:00:00Z" }),
      ];
      stubFetch(makeResponse(prs));

      render(<PRListModal state="open" onClose={vi.fn()} />);

      await waitFor(() => {
        expect(screen.getByTestId("pr-list")).toBeInTheDocument();
      });

      expect(screen.getByText("First PR")).toBeInTheDocument();
      expect(screen.getByText("Second PR")).toBeInTheDocument();
    });

    it("renders formatted timestamps", async () => {
      const prs = [makePR({ created_at: "2024-03-15T10:30:00Z" })];
      stubFetch(makeResponse(prs));

      render(<PRListModal state="open" onClose={vi.fn()} />);

      await waitFor(() => {
        expect(screen.getByTestId("pr-list")).toBeInTheDocument();
      });

      // The formatted date should appear somewhere in the document
      // Exact format depends on locale — just confirm some date text appears
      const listEl = screen.getByTestId("pr-list");
      expect(listEl.textContent).toMatch(/2024|Mar/i);
    });

    it("renders PR links with correct href", async () => {
      const prs = [
        makePR({ url: "https://github.com/owner/repo/pull/42", title: "My PR" }),
      ];
      stubFetch(makeResponse(prs));

      render(<PRListModal state="open" onClose={vi.fn()} />);

      await waitFor(() => {
        expect(screen.getByTestId("pr-list")).toBeInTheDocument();
      });

      const link = screen.getByRole("link", { name: /My PR/i });
      expect(link).toHaveAttribute("href", "https://github.com/owner/repo/pull/42");
    });

    it("does not show loading indicator after fetch completes", async () => {
      stubFetch(makeResponse([makePR()]));

      render(<PRListModal state="open" onClose={vi.fn()} />);

      await waitFor(() => {
        expect(screen.queryByTestId("pr-list-loading")).not.toBeInTheDocument();
      });
    });
  });

  describe("error state", () => {
    it("renders error message when fetch fails with network error", async () => {
      vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network Error")));

      render(<PRListModal state="open" onClose={vi.fn()} />);

      await waitFor(() => {
        expect(screen.getByTestId("pr-list-error")).toBeInTheDocument();
      });
    });

    it("renders error message when server returns non-ok response", async () => {
      stubFetch({ detail: "Bad Gateway" }, false, 502);

      render(<PRListModal state="open" onClose={vi.fn()} />);

      await waitFor(() => {
        expect(screen.getByTestId("pr-list-error")).toBeInTheDocument();
      });
    });

    it("does not show loading indicator when in error state", async () => {
      vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("fail")));

      render(<PRListModal state="open" onClose={vi.fn()} />);

      await waitFor(() => {
        expect(screen.queryByTestId("pr-list-loading")).not.toBeInTheDocument();
      });
    });
  });

  describe("close behaviour", () => {
    it("calls onClose when close button is clicked", async () => {
      stubFetch(makeResponse([]));
      const onClose = vi.fn();

      render(<PRListModal state="open" onClose={onClose} />);

      await waitFor(() => {
        expect(screen.queryByTestId("pr-list-loading")).not.toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /close/i }));
      expect(onClose).toHaveBeenCalledOnce();
    });

    it("calls onClose when ESC key is pressed", async () => {
      stubFetch(makeResponse([]));
      const onClose = vi.fn();

      render(<PRListModal state="open" onClose={onClose} />);

      await waitFor(() => {
        expect(screen.queryByTestId("pr-list-loading")).not.toBeInTheDocument();
      });

      fireEvent.keyDown(document, { key: "Escape", code: "Escape" });
      expect(onClose).toHaveBeenCalledOnce();
    });
  });

  describe("pagination", () => {
    beforeEach(() => {
      // Default: next page exists
    });

    it("prev button is disabled on the first page", async () => {
      stubFetch(makeResponse([makePR()], 1));

      render(<PRListModal state="open" onClose={vi.fn()} />);

      await waitFor(() => {
        expect(screen.getByTestId("pr-list")).toBeInTheDocument();
      });

      expect(screen.getByTestId("pr-list-prev")).toBeDisabled();
    });

    it("next button triggers fetch with page 2", async () => {
      const fetchMock = stubFetch(makeResponse([makePR()], 1));

      render(<PRListModal state="open" onClose={vi.fn()} />);

      await waitFor(() => {
        expect(screen.getByTestId("pr-list")).toBeInTheDocument();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId("pr-list-next"));
      });

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalledTimes(2);
      });

      const secondCallUrl = fetchMock.mock.calls[1][0] as string;
      expect(secondCallUrl).toContain("page=2");
    });

    it("prev button triggers fetch with previous page", async () => {
      const fetchMock = stubFetch(makeResponse([makePR()], 2));

      // Start on page 2 by clicking next first
      render(<PRListModal state="open" onClose={vi.fn()} />);

      await waitFor(() => {
        expect(screen.getByTestId("pr-list")).toBeInTheDocument();
      });

      // Go to page 2
      await act(async () => {
        fireEvent.click(screen.getByTestId("pr-list-next"));
      });

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalledTimes(2);
      });

      // Go back to page 1
      await act(async () => {
        fireEvent.click(screen.getByTestId("pr-list-prev"));
      });

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalledTimes(3);
      });

      const thirdCallUrl = fetchMock.mock.calls[2][0] as string;
      expect(thirdCallUrl).toContain("page=1");
    });

    it("next button is disabled when current page returns fewer items than per_page", async () => {
      // Return only 5 items → last page
      const prs = Array.from({ length: 5 }, (_, i) => makePR({ number: i + 1, title: `PR ${i + 1}` }));
      stubFetch(makeResponse(prs, 1));

      render(<PRListModal state="open" onClose={vi.fn()} />);

      await waitFor(() => {
        expect(screen.getByTestId("pr-list")).toBeInTheDocument();
      });

      expect(screen.getByTestId("pr-list-next")).toBeDisabled();
    });

    it("fetch includes correct state param", async () => {
      const fetchMock = stubFetch(makeResponse([]));

      render(<PRListModal state="merged" onClose={vi.fn()} />);

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalledOnce();
      });

      const url = fetchMock.mock.calls[0][0] as string;
      expect(url).toContain("state=merged");
    });

    it("fetch includes per_page param", async () => {
      const fetchMock = stubFetch(makeResponse([]));

      render(<PRListModal state="open" onClose={vi.fn()} />);

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalledOnce();
      });

      const url = fetchMock.mock.calls[0][0] as string;
      expect(url).toContain("per_page=30");
    });
  });

  describe("accessibility", () => {
    it("has role=dialog with aria-modal", async () => {
      stubFetch(makeResponse([]));

      render(<PRListModal state="open" onClose={vi.fn()} />);

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-modal", "true");
    });

    it("has an accessible label on the dialog", async () => {
      stubFetch(makeResponse([]));

      render(<PRListModal state="open" onClose={vi.fn()} />);

      const dialog = screen.getByRole("dialog");
      // Should have aria-labelledby or aria-label
      const hasLabel =
        dialog.hasAttribute("aria-label") || dialog.hasAttribute("aria-labelledby");
      expect(hasLabel).toBe(true);
    });
  });

  describe("state prop", () => {
    it("displays 'Open Pull Requests' heading for state=open", async () => {
      stubFetch(makeResponse([]));

      render(<PRListModal state="open" onClose={vi.fn()} />);

      await waitFor(() => {
        expect(screen.queryByTestId("pr-list-loading")).not.toBeInTheDocument();
      });

      expect(screen.getByText(/open pull requests/i)).toBeInTheDocument();
    });

    it("displays 'Merged Pull Requests' heading for state=merged", async () => {
      stubFetch(makeResponse([]));

      render(<PRListModal state="merged" onClose={vi.fn()} />);

      await waitFor(() => {
        expect(screen.queryByTestId("pr-list-loading")).not.toBeInTheDocument();
      });

      expect(screen.getByText(/merged pull requests/i)).toBeInTheDocument();
    });

    it("shows empty message when no PRs returned", async () => {
      stubFetch(makeResponse([]));

      render(<PRListModal state="open" onClose={vi.fn()} />);

      await waitFor(() => {
        expect(screen.queryByTestId("pr-list-loading")).not.toBeInTheDocument();
      });

      expect(screen.getByTestId("pr-list")).toBeInTheDocument();
      expect(screen.getByText(/no pull requests/i)).toBeInTheDocument();
    });
  });
});
