import React from 'react';
import type { EvaluationOut } from '../types';

interface EvaluationComparisonChartProps {
  baseline: EvaluationOut;
  context: EvaluationOut;
  unit?: string;
}

export const EvaluationComparisonChart: React.FC<EvaluationComparisonChartProps> = ({
  baseline,
  context,
  unit = 'portions',
}) => {
  const bM = baseline.metrics as Record<string, number | undefined>;
  const cM = context.metrics as Record<string, number | undefined>;

  const metricsToCompare = [
    {
      key: 'prepared_total',
      label: 'Prepared Total',
      baselineVal: bM.prepared_portions ?? bM.prepared_total ?? 0,
      contextVal: cM.prepared_portions ?? cM.prepared_total ?? 0,
    },
    {
      key: 'untouched_leftover',
      label: 'Untouched Leftovers',
      baselineVal: bM.untouched_leftover_portions ?? bM.untouched_leftover ?? 0,
      contextVal: cM.untouched_leftover_portions ?? cM.untouched_leftover ?? 0,
    },
    {
      key: 'plate_waste',
      label: 'Plate Waste',
      baselineVal: bM.plate_waste_portions ?? bM.plate_waste ?? 0,
      contextVal: cM.plate_waste_portions ?? cM.plate_waste ?? 0,
    },
    {
      key: 'shortage',
      label: 'Shortage (Unmet)',
      baselineVal: bM.shortage_portions ?? bM.shortage ?? 0,
      contextVal: cM.shortage_portions ?? cM.shortage ?? 0,
    },
    {
      key: 'total_waste',
      label: 'Total Food Waste',
      baselineVal: bM.total_waste_portions ?? bM.total_waste ?? 0,
      contextVal: cM.total_waste_portions ?? cM.total_waste ?? 0,
    },
  ];

  const maxVal = Math.max(
    ...metricsToCompare.flatMap((m) => [m.baselineVal, m.contextVal]),
    10
  ) * 1.1;

  const chartHeight = 220;

  return (
    <div className="chart-container">
      <div className="chart-header">
        <div>
          <h4 className="chart-title">Policy Outcome Comparison</h4>
          <span className="chart-subtitle">
            Fixed Baseline vs Context-Aware Split-Batch Policy under identical demand realization ({unit})
          </span>
        </div>
        <div className="chart-legend">
          <span className="legend-item">
            <span className="legend-color legend-color--baseline" /> Fixed Baseline
          </span>
          <span className="legend-item">
            <span className="legend-color legend-color--context" /> Context-Aware Split Batch
          </span>
        </div>
      </div>

      <div className="chart-body" style={{ height: `${chartHeight}px` }}>
        <div className="chart-y-axis">
          <span>{Math.round(maxVal)} {unit}</span>
          <span>{Math.round(maxVal / 2)} {unit}</span>
          <span>0 {unit}</span>
        </div>

        <div className="grouped-bars-track">
          {metricsToCompare.map((metric) => {
            const baselinePct = Math.min(100, (metric.baselineVal / maxVal) * 100);
            const contextPct = Math.min(100, (metric.contextVal / maxVal) * 100);
            const diff = metric.baselineVal - metric.contextVal;
            const diffPct = metric.baselineVal > 0 ? (diff / metric.baselineVal) * 100 : 0;

            return (
              <div key={metric.key} className="grouped-bar-group">
                <div className="grouped-bar-pair">
                  <div
                    className="grouped-bar grouped-bar--baseline"
                    style={{ height: `${baselinePct}%` }}
                    title={`Fixed Baseline: ${metric.baselineVal.toFixed(1)} ${unit}`}
                  >
                    <span className="bar-top-value">{metric.baselineVal.toFixed(0)}</span>
                  </div>
                  <div
                    className="grouped-bar grouped-bar--context"
                    style={{ height: `${contextPct}%` }}
                    title={`Context-Aware: ${metric.contextVal.toFixed(1)} ${unit}`}
                  >
                    <span className="bar-top-value">{metric.contextVal.toFixed(0)}</span>
                  </div>
                </div>

                <span className="grouped-x-label">{metric.label}</span>

                {metric.key === 'total_waste' && diff > 0 && (
                  <span className="waste-diff-badge">
                    -{diff.toFixed(1)} {unit} (-{diffPct.toFixed(1)}%)
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
