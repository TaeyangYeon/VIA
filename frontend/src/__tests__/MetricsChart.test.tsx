import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import MetricsChart from '../components/MetricsChart';

const SAMPLE_ITEM_RESULTS = [
  {
    item_id: 1,
    item_name: 'item_001',
    passed: true,
    metrics: { accuracy: 0.98, fp_rate: 0.01, fn_rate: 0.01, coord_error: 0, success_rate: 1.0 },
    details: 'OK',
  },
  {
    item_id: 2,
    item_name: 'item_002',
    passed: false,
    metrics: { accuracy: 0.85, fp_rate: 0.10, fn_rate: 0.05, coord_error: 0, success_rate: 0.9 },
    details: 'Failed',
  },
];

// ── Empty state ────────────────────────────────────────────────

describe('MetricsChart — empty state', () => {
  it('shows metrics-chart-empty when item_results is an empty array', () => {
    render(<MetricsChart item_results={[]} />);
    expect(screen.getByTestId('metrics-chart-empty')).toBeInTheDocument();
  });

  it('shows metrics-chart-empty when item_results is null', () => {
    render(<MetricsChart item_results={null as any} />);
    expect(screen.getByTestId('metrics-chart-empty')).toBeInTheDocument();
  });

  it('does not render metrics-chart when empty', () => {
    render(<MetricsChart item_results={[]} />);
    expect(screen.queryByTestId('metrics-chart')).not.toBeInTheDocument();
  });
});

// ── Chart rendering ────────────────────────────────────────────

describe('MetricsChart — chart rendering', () => {
  it('renders metrics-chart wrapper when data is present', () => {
    render(<MetricsChart item_results={SAMPLE_ITEM_RESULTS} />);
    expect(screen.getByTestId('metrics-chart')).toBeInTheDocument();
  });

  it('shows item names in chart area', () => {
    render(<MetricsChart item_results={SAMPLE_ITEM_RESULTS} />);
    expect(screen.getByTestId('metrics-chart').textContent).toContain('item_001');
    expect(screen.getByTestId('metrics-chart').textContent).toContain('item_002');
  });

  it('renders a bar group for each item', () => {
    render(<MetricsChart item_results={SAMPLE_ITEM_RESULTS} />);
    expect(screen.getByTestId('metrics-bar-group-0')).toBeInTheDocument();
    expect(screen.getByTestId('metrics-bar-group-1')).toBeInTheDocument();
  });

  it('shows accuracy, fp_rate, fn_rate legend labels', () => {
    render(<MetricsChart item_results={SAMPLE_ITEM_RESULTS} />);
    const chart = screen.getByTestId('metrics-chart');
    expect(chart.textContent).toContain('accuracy');
    expect(chart.textContent).toContain('fp_rate');
    expect(chart.textContent).toContain('fn_rate');
  });

  it('renders single item correctly', () => {
    render(<MetricsChart item_results={[SAMPLE_ITEM_RESULTS[0]]} />);
    expect(screen.getByTestId('metrics-bar-group-0')).toBeInTheDocument();
    expect(screen.queryByTestId('metrics-bar-group-1')).not.toBeInTheDocument();
  });
});
