import { useState, useEffect, useCallback } from 'react';
import './App.css';

type Period = 'this_week' | 'this_month';

type AiMetricsResponse = {
  period: string;
  period_start: string;
  period_end: string;
  plans_generated: number;
  issues_created_by_ai: number;
  ai_prs_opened: number;
  ai_prs_merged: number;
  ai_prs_rejected_closed: number;
};

type FetchState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: AiMetricsResponse }
  | { status: 'error'; message: string };

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="metric-card" data-testid="metric-card">
      <span className="metric-value" data-testid={`metric-value-${label.toLowerCase().replace(/\s+/g, '-')}`}>
        {value}
      </span>
      <span className="metric-label">{label}</span>
    </div>
  );
}

export default function App() {
  const [period, setPeriod] = useState<Period>('this_week');
  const [fetchState, setFetchState] = useState<FetchState>({ status: 'idle' });

  const fetchMetrics = useCallback(async (selectedPeriod: Period) => {
    setFetchState({ status: 'loading' });
    try {
      const response = await fetch(`/api/v1/ai-metrics?period=${selectedPeriod}`);
      if (!response.ok) {
        setFetchState({ status: 'error', message: `Request failed: ${response.status} ${response.statusText}` });
        return;
      }
      const data = (await response.json()) as AiMetricsResponse;
      setFetchState({ status: 'success', data });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setFetchState({ status: 'error', message });
    }
  }, []);

  useEffect(() => {
    void fetchMetrics(period);
  }, [period, fetchMetrics]);

  const handlePeriodChange = useCallback((newPeriod: Period) => {
    setPeriod(newPeriod);
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1>AI Pipeline Metrics</h1>
        <p className="app-subtitle">GitHub activity for AI-generated code</p>
      </header>

      <main className="app-main">
        <div className="period-selector" role="group" aria-label="Select time period">
          <button
            className={`period-button${period === 'this_week' ? ' period-button--active' : ''}`}
            onClick={() => handlePeriodChange('this_week')}
            aria-pressed={period === 'this_week'}
            data-testid="period-this-week"
          >
            This Week
          </button>
          <button
            className={`period-button${period === 'this_month' ? ' period-button--active' : ''}`}
            onClick={() => handlePeriodChange('this_month')}
            aria-pressed={period === 'this_month'}
            data-testid="period-this-month"
          >
            This Month
          </button>
        </div>

        {fetchState.status === 'loading' && (
          <div className="state-container" data-testid="loading-indicator">
            <p>Loading metrics…</p>
          </div>
        )}

        {fetchState.status === 'error' && (
          <div className="state-container state-error" data-testid="error-message" role="alert">
            <p>Failed to load metrics: {fetchState.message}</p>
            <button onClick={() => void fetchMetrics(period)}>Retry</button>
          </div>
        )}

        {fetchState.status === 'success' && (
          <div className="metrics-container" data-testid="metrics-container">
            <p className="period-range" data-testid="period-range">
              {fetchState.data.period_start} – {fetchState.data.period_end}
            </p>
            <div className="metrics-grid">
              <MetricCard label="Plans Generated" value={fetchState.data.plans_generated} />
              <MetricCard label="Issues Created by AI" value={fetchState.data.issues_created_by_ai} />
              <MetricCard label="PRs Opened" value={fetchState.data.ai_prs_opened} />
              <MetricCard label="PRs Merged" value={fetchState.data.ai_prs_merged} />
              <MetricCard label="PRs Rejected" value={fetchState.data.ai_prs_rejected_closed} />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
