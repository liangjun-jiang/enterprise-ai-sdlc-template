import { useEffect, useState } from "react";

type HealthStatus = "loading" | "ok" | "error";

function App() {
  const [status, setStatus] = useState<HealthStatus>("loading");

  useEffect(() => {
    fetch("/health")
      .then((res) => {
        if (!res.ok) throw new Error("not ok");
        return res.json();
      })
      .then((data: { status: string }) => {
        setStatus(data.status === "ok" ? "ok" : "error");
      })
      .catch(() => setStatus("error"));
  }, []);

  return (
    <div>
      <h1>Enterprise AI-SDLC Template</h1>
      <p data-testid="health-status">{status}</p>
    </div>
  );
}

export default App;
