import { useEffect, useState, useCallback } from 'react';
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

type FetchState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: AiMetrics }
  | { status: 'error'; message: string };

function App() {
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
      const data: AiMetrics = await response.json() as AiMetrics;
      setFetchState({ status: 'success', data });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setFetchState({ status: 'error', message });
    }
  }, []);

  useEffect(() => {
    fetchMetrics(period);
  }, [period, fetchMetrics]);

  const handlePeriodChange = useCallback((newPeriod: Period) => {
    setPeriod(newPeriod);
  }, []);

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>AI Pipeline Metrics</h1>
        <div className="period-selector" role="group" aria-label="Select time period">
          <button
            className={period === 'this_week' ? 'active' : ''}
            onClick={() => handlePeriodChange('this_week')}
            aria-pressed={period === 'this_week'}
          >
            This Week
          </button>
          <button
            className={period === 'this_month' ? 'active' : ''}
            onClick={() => handlePeriodChange('this_month')}
            aria-pressed={period === 'this_month'}
          >
            This Month
          </button>
        </div>
      </header>

      <main>
        {fetchState.status === 'loading' && (
          <div className="status-message" data-testid="loading-indicator">
            Loading metrics…
          </div>
        )}

        {fetchState.status === 'error' && (
          <div className="status-message error" data-testid="error-message" role="alert">
            {fetchState.message}
          </div>
        )}

        {fetchState.status === 'success' && (
          <div data-testid="metrics-display">
            <p className="period-range">
              {fetchState.data.period_start} – {fetchState.data.period_end}
            </p>
            <div className="metrics-grid">
              <div className="metric-card" data-testid="metric-plans-generated">
                <span className="metric-value">{fetchState.data.plans_generated}</span>
                <span className="metric-label">Plans Generated</span>
              </div>
              <div className="metric-card" data-testid="metric-issues-created">
                <span className="metric-value">{fetchState.data.issues_created_by_ai}</span>
                <span className="metric-label">Issues Created by AI</span>
              </div>
              <div className="metric-card" data-testid="metric-prs-opened">
                <span className="metric-value">{fetchState.data.ai_prs_opened}</span>
                <span className="metric-label">AI PRs Opened</span>
              </div>
              <div className="metric-card" data-testid="metric-prs-merged">
                <span className="metric-value">{fetchState.data.ai_prs_merged}</span>
                <span className="metric-label">AI PRs Merged</span>
              </div>
              <div className="metric-card" data-testid="metric-prs-rejected">
                <span className="metric-value">{fetchState.data.ai_prs_rejected_closed}</span>
                <span className="metric-label">AI PRs Rejected / Closed</span>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
