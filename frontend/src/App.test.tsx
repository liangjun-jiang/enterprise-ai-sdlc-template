import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, afterEach, describe, it, expect, vi } from 'vitest';
import App from './App';

const mockMetricsWeek = {
  period: 'this_week',
  period_start: '2024-01-15',
  period_end: '2024-01-21',
  plans_generated: 3,
  issues_created_by_ai: 7,
  ai_prs_opened: 5,
  ai_prs_merged: 4,
  ai_prs_rejected_closed: 1,
};

const mockMetricsMonth = {
  period: 'this_month',
  period_start: '2024-01-01',
  period_end: '2024-01-21',
  plans_generated: 12,
  issues_created_by_ai: 28,
  ai_prs_opened: 20,
  ai_prs_merged: 17,
  ai_prs_rejected_closed: 3,
};

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockMetricsWeek),
    }),
  );
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('App', () => {
  it('renders the page heading', async () => {
    render(<App />);
    expect(screen.getByRole('heading', { name: /AI Pipeline Metrics/i })).toBeDefined();
  });

  it('shows a loading indicator while fetching', () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockReturnValue(new Promise(() => undefined)),
    );
    render(<App />);
    expect(screen.getByTestId('loading-indicator')).toBeDefined();
  });

  it('renders metrics after a successful fetch', async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByTestId('metrics-container')).toBeDefined());
    expect(screen.getByTestId('period-range').textContent).toContain('2024-01-15');
    expect(screen.getByTestId('period-range').textContent).toContain('2024-01-21');
    const cards = screen.getAllByTestId('metric-card');
    expect(cards).toHaveLength(5);
  });

  it('displays correct metric values', async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByTestId('metrics-container')).toBeDefined());
    expect(screen.getByTestId('metric-value-plans-generated').textContent).toBe('3');
    expect(screen.getByTestId('metric-value-issues-created-by-ai').textContent).toBe('7');
    expect(screen.getByTestId('metric-value-prs-opened').textContent).toBe('5');
    expect(screen.getByTestId('metric-value-prs-merged').textContent).toBe('4');
    expect(screen.getByTestId('metric-value-prs-rejected').textContent).toBe('1');
  });

  it('fetches with this_week by default', async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByTestId('metrics-container')).toBeDefined());
    expect(vi.mocked(fetch)).toHaveBeenCalledWith('/api/v1/ai-metrics?period=this_week');
  });

  it('switches to this_month when the button is clicked', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn()
        .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(mockMetricsWeek) })
        .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(mockMetricsMonth) }),
    );

    render(<App />);
    await waitFor(() => expect(screen.getByTestId('metrics-container')).toBeDefined());

    await userEvent.click(screen.getByTestId('period-this-month'));

    await waitFor(() =>
      expect(screen.getByTestId('metric-value-plans-generated').textContent).toBe('12'),
    );
    expect(vi.mocked(fetch)).toHaveBeenLastCalledWith('/api/v1/ai-metrics?period=this_month');
  });

  it('shows an error message when the fetch fails with a non-ok response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 502,
        statusText: 'Bad Gateway',
      }),
    );
    render(<App />);
    await waitFor(() => expect(screen.getByTestId('error-message')).toBeDefined());
    expect(screen.getByTestId('error-message').textContent).toContain('502');
  });

  it('shows an error message when fetch throws', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new Error('Network failure')),
    );
    render(<App />);
    await waitFor(() => expect(screen.getByTestId('error-message')).toBeDefined());
    expect(screen.getByTestId('error-message').textContent).toContain('Network failure');
  });

  it('retries the fetch when the retry button is clicked', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn()
        .mockRejectedValueOnce(new Error('Network failure'))
        .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(mockMetricsWeek) }),
    );
    render(<App />);
    await waitFor(() => expect(screen.getByTestId('error-message')).toBeDefined());

    await userEvent.click(screen.getByRole('button', { name: /retry/i }));

    await waitFor(() => expect(screen.getByTestId('metrics-container')).toBeDefined());
  });

  it('marks the active period button with aria-pressed', async () => {
    render(<App />);
    const weekBtn = screen.getByTestId('period-this-week');
    const monthBtn = screen.getByTestId('period-this-month');
    expect(weekBtn.getAttribute('aria-pressed')).toBe('true');
    expect(monthBtn.getAttribute('aria-pressed')).toBe('false');
  });
});
