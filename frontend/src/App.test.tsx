import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, beforeEach, afterEach, describe, it, expect } from 'vitest';
import App from './App';

const mockMetricsWeek = {
  period: 'this_week',
  period_start: '2024-01-15',
  period_end: '2024-01-21',
  plans_generated: 5,
  issues_created_by_ai: 12,
  ai_prs_opened: 8,
  ai_prs_merged: 6,
  ai_prs_rejected_closed: 2,
};

const mockMetricsMonth = {
  period: 'this_month',
  period_start: '2024-01-01',
  period_end: '2024-01-21',
  plans_generated: 20,
  issues_created_by_ai: 45,
  ai_prs_opened: 30,
  ai_prs_merged: 25,
  ai_prs_rejected_closed: 5,
};

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      statusText: 'OK',
      json: () => Promise.resolve(mockMetricsWeek),
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('App', () => {
  it('shows loading indicator while fetching', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(
        () => new Promise(() => { /* never resolves */ }),
      ),
    );

    render(<App />);
    expect(screen.getByTestId('loading-indicator')).toBeInTheDocument();
  });

  it('renders metrics on successful fetch', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('metrics-display')).toBeInTheDocument();
    });

    expect(screen.getByTestId('metric-plans-generated')).toHaveTextContent('5');
    expect(screen.getByTestId('metric-issues-created')).toHaveTextContent('12');
    expect(screen.getByTestId('metric-prs-opened')).toHaveTextContent('8');
    expect(screen.getByTestId('metric-prs-merged')).toHaveTextContent('6');
    expect(screen.getByTestId('metric-prs-rejected')).toHaveTextContent('2');
    expect(screen.getByText('2024-01-15 – 2024-01-21')).toBeInTheDocument();
  });

  it('calls the API with the correct default period', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('metrics-display')).toBeInTheDocument();
    });

    expect(vi.mocked(fetch)).toHaveBeenCalledWith('/api/v1/ai-metrics?period=this_week');
  });

  it('shows error message on non-2xx response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 502,
        statusText: 'Bad Gateway',
        json: () => Promise.resolve({ detail: 'GitHub API error: 502' }),
      }),
    );

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toBeInTheDocument();
    });

    expect(screen.getByTestId('error-message')).toHaveTextContent('Request failed: 502 Bad Gateway');
  });

  it('shows error message on network failure', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new Error('Network error')),
    );

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toBeInTheDocument();
    });

    expect(screen.getByTestId('error-message')).toHaveTextContent('Network error');
  });

  it('switches period and refetches when month button is clicked', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: () => Promise.resolve(mockMetricsWeek),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: () => Promise.resolve(mockMetricsMonth),
      });

    vi.stubGlobal('fetch', fetchMock);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('metrics-display')).toBeInTheDocument();
    });

    expect(screen.getByTestId('metric-plans-generated')).toHaveTextContent('5');

    fireEvent.click(screen.getByRole('button', { name: /this month/i }));

    await waitFor(() => {
      expect(screen.getByTestId('metric-plans-generated')).toHaveTextContent('20');
    });

    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/v1/ai-metrics?period=this_week');
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/v1/ai-metrics?period=this_month');
  });

  it('renders the period selector with both buttons', () => {
    render(<App />);

    expect(screen.getByRole('button', { name: /this week/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /this month/i })).toBeInTheDocument();
  });

  it('marks the active period button with aria-pressed', async () => {
    render(<App />);

    const weekButton = screen.getByRole('button', { name: /this week/i });
    const monthButton = screen.getByRole('button', { name: /this month/i });

    expect(weekButton).toHaveAttribute('aria-pressed', 'true');
    expect(monthButton).toHaveAttribute('aria-pressed', 'false');

    fireEvent.click(monthButton);

    await waitFor(() => {
      expect(monthButton).toHaveAttribute('aria-pressed', 'true');
    });
    expect(weekButton).toHaveAttribute('aria-pressed', 'false');
  });
});
