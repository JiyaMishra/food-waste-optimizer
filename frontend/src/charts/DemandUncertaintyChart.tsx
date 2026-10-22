import React from 'react';
import type { DishForecastRow } from '../types';

interface DemandUncertaintyChartProps {
  rows: DishForecastRow[];
  unit?: string;
}

export const DemandUncertaintyChart: React.FC<DemandUncertaintyChartProps> = ({
  rows,
  unit = 'portions',
}) => {
  if (!rows || rows.length === 0) {
    return <div className="chart-empty">No forecast items to chart.</div>;
  }

  const maxVal = Math.max(...rows.map((r) => r.upper_bound), 50) * 1.15;
  const chartHeight = 180;

  return (
    <div className="chart-container">
      <div className="chart-header">
        <div>
          <h4 className="chart-title">Dish Demand Predictions &amp; Uncertainty Bounds</h4>
          <span className="chart-subtitle">
            Expected portions with 80% empirical quantile residual bounds ({rows[0]?.interval_method || 'Empirical'})
          </span>
        </div>
        <div className="chart-legend">
          <span className="legend-item">
            <span className="legend-color legend-color--uncertainty-range" /> 10th–90th Quantile Range
          </span>
          <span className="legend-item">
            <span className="legend-color legend-color--point" /> Expected Prediction
          </span>
        </div>
      </div>

      <div className="chart-body" style={{ height: `${chartHeight}px` }}>
        <div className="chart-y-axis">
          <span>{Math.round(maxVal)} {unit}</span>
          <span>{Math.round(maxVal / 2)} {unit}</span>
          <span>0 {unit}</span>
        </div>

        <div className="uncertainty-tracks">
          {rows.map((row) => {
            const lowerPct = (row.lower_bound / maxVal) * 100;
            const predPct = (row.prediction / maxVal) * 100;
            const upperPct = (row.upper_bound / maxVal) * 100;
            const rangeHeight = Math.max(4, upperPct - lowerPct);

            return (
              <div key={row.dish_id} className="uncertainty-col">
                <div className="uncertainty-range-wrapper">
                  {/* Shaded quantile range */}
                  <div
                    className="uncertainty-shaded-band"
                    style={{
                      bottom: `${lowerPct}%`,
                      height: `${rangeHeight}%`,
                    }}
                    title={`80% Interval: ${row.lower_bound.toFixed(1)} – ${row.upper_bound.toFixed(1)} ${unit}`}
                  />

                  {/* Point forecast marker */}
                  <div
                    className="uncertainty-point-marker"
                    style={{ bottom: `${predPct}%` }}
                    title={`Expected: ${row.prediction.toFixed(1)} ${unit}`}
                  >
                    <span className="point-marker-label">{row.prediction.toFixed(0)}</span>
                  </div>
                </div>

                <span className="chart-x-label" title={row.dish_name || row.dish_id}>
                  {row.dish_name || row.dish_id}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
