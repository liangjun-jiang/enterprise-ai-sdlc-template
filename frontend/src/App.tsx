import { useState, useEffect, useCallback } from 'react';
import './App.css';

type Period = 'this_week' | 'this_month';

type AiMetrics = {
  period: string;
  period_start: string;
  period_end: string;
  plans_generated: number;
  issues_created_by_ai: number;
  ai_prs_opened: number;
  ai_prs_merged: number;
  ai_prs_rejected_closed: number;
};

type MetricCardProps = {
  label: string;
  value: number;
};

function MetricCard({ label, value }: MetricCardProps) {
  return (
    <div className="metric-card">
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value}</span>
    </div>
  );
}

export default function App() {
  const [period, setPeriod] = useState<Period>('this_week');
  const [metrics, setMetrics] = useState<AiMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = useCallback(async (selectedPeriod: Period) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/v1/ai-metrics?period=${selectedPeriod}`);
      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }
      const data: AiMetrics = await response.json() as AiMetrics;
      setMetrics(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchMetrics(period);
  }, [period, fetchMetrics]);

  const handlePeriodChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      setPeriod(e.target.value as Period);
    },
    []
  );

  return (
    <div className="app">
      <header className="app-bar">
        <h1>AI Pipeline Dashboard</h1>
      </header>

      <main className="content">
        <div className="period-selector">
          <label htmlFor="period-select">Time period</label>
          <select
            id="period-select"
            value={period}
            onChange={handlePeriodChange}
            data-testid="period-select"
          >
            <option value="this_week">This Week</option>
            <option value="this_month">This Month</option>
          </select>
        </div>

        {loading && (
          <div className="status-message loading" data-testid="loading-state">
            Loading metrics…
          </div>
        )}

        {!loading && error && (
          <div className="status-message error" data-testid="error-state">
            {error}
          </div>
        )}

        {!loading && !error && metrics && (
          <>
            <p className="period-info" data-testid="period-info">
              {metrics.period_start} – {metrics.period_end}
            </p>
            <div className="metrics-grid" data-testid="metrics-grid">
              <MetricCard label="Plans Generated" value={metrics.plans_generated} />
              <MetricCard label="Issues Created by AI" value={metrics.issues_created_by_ai} />
              <MetricCard label="AI PRs Opened" value={metrics.ai_prs_opened} />
              <MetricCard label="AI PRs Merged" value={metrics.ai_prs_merged} />
              <MetricCard label="AI PRs Rejected/Closed" value={metrics.ai_prs_rejected_closed} />
            </div>
          </>
        )}
      </main>
    </div>
  );
}
