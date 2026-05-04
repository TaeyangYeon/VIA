import React from 'react';
import { BarChart2 } from 'lucide-react';
import {
  text_secondary,
  border_default,
  accent_success,
  accent_error,
  accent_warning,
} from '../styles/design-tokens';

interface ItemMetrics {
  accuracy: number;
  fp_rate: number;
  fn_rate: number;
  coord_error: number;
  success_rate: number;
}

interface ItemTestResult {
  item_id: number;
  item_name: string;
  passed: boolean;
  metrics: ItemMetrics;
  details: string;
}

interface MetricsChartProps {
  item_results: ItemTestResult[];
}

const CHART_HEIGHT = 120;

export default function MetricsChart({ item_results }: MetricsChartProps) {
  if (!item_results || item_results.length === 0) {
    return (
      <div
        data-testid="metrics-chart-empty"
        className="flex flex-col items-center justify-center gap-2 py-8"
        style={{ color: text_secondary }}
      >
        <BarChart2 size={24} strokeWidth={1.5} />
        <span className="text-xs">No metrics data</span>
      </div>
    );
  }

  return (
    <div data-testid="metrics-chart" className="flex flex-col gap-3">
      {/* Legend */}
      <div className="flex gap-4 text-xs" style={{ color: text_secondary }}>
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block w-2.5 h-2.5 rounded-sm"
            style={{ backgroundColor: accent_success }}
          />
          accuracy
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block w-2.5 h-2.5 rounded-sm"
            style={{ backgroundColor: accent_error }}
          />
          fp_rate
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block w-2.5 h-2.5 rounded-sm"
            style={{ backgroundColor: accent_warning }}
          />
          fn_rate
        </span>
      </div>

      {/* Chart area */}
      <div
        className="flex items-end gap-5 overflow-x-auto pb-1 pt-2 border-b"
        style={{ borderColor: border_default }}
      >
        {item_results.map((item, i) => (
          <div
            key={item.item_id}
            data-testid={`metrics-bar-group-${i}`}
            className="flex flex-col items-center gap-2 shrink-0"
          >
            {/* Bars */}
            <div className="flex items-end gap-1" style={{ height: CHART_HEIGHT }}>
              <div
                className="w-4 rounded-t transition-all duration-150"
                title={`accuracy: ${(item.metrics.accuracy * 100).toFixed(1)}%`}
                style={{
                  height: `${Math.max(item.metrics.accuracy * 100, 1)}%`,
                  backgroundColor: accent_success,
                  opacity: 0.85,
                }}
              />
              <div
                className="w-4 rounded-t transition-all duration-150"
                title={`fp_rate: ${(item.metrics.fp_rate * 100).toFixed(1)}%`}
                style={{
                  height: `${Math.max(item.metrics.fp_rate * 100, 1)}%`,
                  backgroundColor: accent_error,
                  opacity: 0.85,
                }}
              />
              <div
                className="w-4 rounded-t transition-all duration-150"
                title={`fn_rate: ${(item.metrics.fn_rate * 100).toFixed(1)}%`}
                style={{
                  height: `${Math.max(item.metrics.fn_rate * 100, 1)}%`,
                  backgroundColor: accent_warning,
                  opacity: 0.85,
                }}
              />
            </div>
            {/* Item name label */}
            <span
              className="text-xs max-w-20 truncate text-center"
              style={{ color: text_secondary }}
              title={item.item_name}
            >
              {item.item_name}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
