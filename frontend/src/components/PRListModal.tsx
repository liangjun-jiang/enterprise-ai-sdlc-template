import { useEffect, useCallback, useRef, useState } from "react";

type PRItem = {
  number: number;
  title: string;
  url: string;
  created_at: string;
  merged_at: string | null;
  state: string;
};

type PRListResponse = {
  prs: PRItem[];
  total: int;
  page: number;
  per_page: number;
};

type PRListModalProps = {
  state: "open" | "merged";
  onClose: () => void;
};

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function PRListModal({ state, onClose }: PRListModalProps) {
  const [prs, setPrs] = useState<PRItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [hasNext, setHasNext] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);

  const PER_PAGE = 30;

  const fetchPRs = useCallback(
    async (currentPage: number) => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(
          `/api/prs?state=${state}&page=${currentPage}&per_page=${PER_PAGE}`
        );
        if (!res.ok) {
          throw new Error(`Request failed with status ${res.status}`);
        }
        const data: PRListResponse = await res.json();
        setPrs(data.prs);
        setHasNext(data.prs.length === PER_PAGE);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    },
    [state]
  );

  useEffect(() => {
    void fetchPRs(page);
  }, [fetchPRs, page]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  useEffect(() => {
    dialogRef.current?.focus();
  }, []);

  const handlePrev = () => {
    setPage((p) => Math.max(1, p - 1));
  };

  const handleNext = () => {
    setPage((p) => p + 1);
  };

  const label = state === "open" ? "Open PRs" : "Merged PRs";

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0,0,0,0.5)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={label}
        tabIndex={-1}
        style={{
          background: "#fff",
          borderRadius: 8,
          padding: 24,
          minWidth: 480,
          maxWidth: "90vw",
          maxHeight: "80vh",
          display: "flex",
          flexDirection: "column",
          gap: 16,
          outline: "none",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <h2 style={{ margin: 0, fontSize: 20 }}>{label}</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            style={{
              background: "none",
              border: "none",
              fontSize: 20,
              cursor: "pointer",
              padding: "4px 8px",
            }}
          >
            &times;
          </button>
        </div>

        {loading && (
          <div data-testid="pr-list-loading" style={{ textAlign: "center", padding: 24 }}>
            Loading…
          </div>
        )}

        {!loading && error !== null && (
          <div
            data-testid="pr-list-error"
            style={{ color: "red", textAlign: "center", padding: 16 }}
          >
            Error: {error}
          </div>
        )}

        {!loading && error === null && (
          <>
            {prs.length === 0 ? (
              <p style={{ textAlign: "center", color: "#666" }}>No pull requests found.</p>
            ) : (
              <ul
                data-testid="pr-list"
                style={{
                  listStyle: "none",
                  margin: 0,
                  padding: 0,
                  overflowY: "auto",
                  flex: 1,
                }}
              >
                {prs.map((pr) => (
                  <li
                    key={pr.number}
                    style={{
                      padding: "10px 0",
                      borderBottom: "1px solid #eee",
                      display: "flex",
                      flexDirection: "column",
                      gap: 4,
                    }}
                  >
                    <a
                      href={pr.url}
                      target="_blank"
                      rel="noreferrer noopener"
                      style={{ fontWeight: 600, color: "#0969da", textDecoration: "none" }}
                    >
                      #{pr.number} {pr.title}
                    </a>
                    <span style={{ fontSize: 12, color: "#666" }}>
                      {formatTimestamp(pr.created_at)}
                    </span>
                  </li>
                ))}
              </ul>
            )}

            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                paddingTop: 8,
              }}
            >
              <button
                data-testid="pr-list-prev"
                onClick={handlePrev}
                disabled={page === 1}
                style={{ cursor: page === 1 ? "not-allowed" : "pointer" }}
              >
                Previous
              </button>
              <span style={{ fontSize: 13, color: "#555" }}>Page {page}</span>
              <button
                data-testid="pr-list-next"
                onClick={handleNext}
                disabled={!hasNext}
                style={{ cursor: !hasNext ? "not-allowed" : "pointer" }}
              >
                Next
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
