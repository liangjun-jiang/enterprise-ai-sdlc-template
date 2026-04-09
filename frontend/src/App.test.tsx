import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, beforeEach, afterEach, describe, it, expect } from 'vitest';
import App from './App';

const mockMetrics = {
  period: 'this_week',
  period_start: '2024-01-15',
  period_end: '2024-01-21',
  plans_generated: 5,
  issues_created_by_ai: 12,
  ai_prs_opened: 8,
  ai_prs_merged: 6,
  ai_prs_rejected_closed: 2,
};

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockMetrics),
    })
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('App', () => {
  it('renders the app bar title', async () => {
    await act(async () => {
      render(<App />);
    });
    expect(screen.getByRole('heading', { name: /AI Pipeline Dashboard/i })).toBeTruthy();
  });

  it('shows loading state initially', () => {
    render(<App />);
    expect(screen.getByTestId('loading-state')).toBeTruthy();
  });

  it('renders metrics grid after successful fetch', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByTestId('metrics-grid')).toBeTruthy();
    });
  });

  it('displays period info after successful fetch', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByTestId('period-info')).toBeTruthy();
    });
    expect(screen.getByTestId('period-info').textContent).toContain('2024-01-15');
    expect(screen.getByTestId('period-info').textContent).toContain('2024-01-21');
  });

  it('displays all metric values', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByTestId('metrics-grid')).toBeTruthy();
    });
    expect(screen.getByText('5')).toBeTruthy();
    expect(screen.getByText('12')).toBeTruthy();
    expect(screen.getByText('8')).toBeTruthy();
    expect(screen.getByText('6')).toBeTruthy();
    expect(screen.getByText('2')).toBeTruthy();
  });

  it('shows error state when fetch fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 502,
      })
    );
    render(<App />);
    await waitFor(() => {
      expect(screen.getByTestId('error-state')).toBeTruthy();
    });
    expect(screen.getByTestId('error-state').textContent).toContain('502');
  });

  it('shows error state when fetch throws', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new Error('Network error'))
    );
    render(<App />);
    await waitFor(() => {
      expect(screen.getByTestId('error-state')).toBeTruthy();
    });
    expect(screen.getByTestId('error-state').textContent).toContain('Network error');
  });

  it('period selector renders with default value', async () => {
    await act(async () => {
      render(<App />);
    });
    const select = screen.getByTestId('period-select') as HTMLSelectElement;
    expect(select.value).toBe('this_week');
  });

  it('refetches metrics when period changes', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ ...mockMetrics, period: 'this_month' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<App />);
    await waitFor(() => {
      expect(screen.getByTestId('metrics-grid')).toBeTruthy();
    });

    const select = screen.getByTestId('period-select');
    await userEvent.selectOptions(select, 'this_month');

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(2);
    });
    expect(fetchMock).toHaveBeenLastCalledWith(
      '/api/v1/ai-metrics?period=this_month'
    );
  });
});
