import React from 'react';
import type { SimulationEvent } from '../types';

interface StockFlowChartProps {
  events: SimulationEvent[];
  capacity?: number;
  unit?: string;
}

export const StockFlowChart: React.FC<StockFlowChartProps> = ({
  events,
  capacity = 500,
  unit = 'portions',
}) => {
  if (!events || events.length === 0) {
    return <div className="chart-empty">No simulation interval events to chart yet.</div>;
  }

  const maxStock = Math.max(
    ...events.map((e) => Math.max(e.stock_before, e.stock_after, e.prepared_qty)),
    capacity,
    100
  );
  const chartHeight = 200;

  return (
    <div className="chart-container">
      <div className="chart-header">
        <div>
          <h4 className="chart-title">Kitchen Inventory &amp; Service Stock Dynamics</h4>
          <span className="chart-subtitle">
            Remaining food stock across intervals vs incoming student consumption ({unit})
          </span>
        </div>
        <div className="chart-legend">
          <span className="legend-item">
            <span className="legend-color legend-color--stock" /> Remaining Stock
          </span>
          <span className="legend-item">
            <span className="legend-color legend-color--served" /> Served / Consumed
          </span>
          <span className="legend-item">
            <span className="legend-color legend-color--unmet" /> Unmet Demand
          </span>
        </div>
      </div>

      <div className="chart-body" style={{ height: `${chartHeight}px` }}>
        <div className="chart-y-axis">
          <span>{Math.round(maxStock)}</span>
          <span>{Math.round(maxStock / 2)}</span>
          <span>0</span>
        </div>

        <div className="chart-bars-track">
          {events.map((e) => {
            const stockPct = Math.min(100, (e.stock_after / maxStock) * 100);
            const servedPct = Math.min(100, (e.served_qty / maxStock) * 100);
            const unmetPct = Math.min(100, (e.unmet_qty / maxStock) * 100);

            return (
              <div key={e.interval_index} className="chart-bar-col">
                <div className="bar-wrapper bar-wrapper--multi">
                  {/* Stock bar */}
                  <div
                    className="stock-bar stock-bar--current"
                    style={{ height: `${stockPct}%` }}
                    title={`Interval ${e.interval_index} (${e.interval_start}): Remaining Stock ${e.stock_after.toFixed(1)} ${unit}`}
                  />
                  {/* Served bar */}
                  <div
                    className="stock-bar stock-bar--served"
                    style={{ height: `${servedPct}%` }}
                    title={`Served: ${e.served_qty.toFixed(1)} ${unit}`}
                  />
                  {/* Unmet bar if any */}
                  {e.unmet_qty > 0 && (
                    <div
                      className="stock-bar stock-bar--unmet"
                      style={{ height: `${unmetPct}%` }}
                      title={`Shortage: ${e.unmet_qty.toFixed(1)} ${unit}`}
                    />
                  )}
                </div>

                {e.action && e.action !== 'none' && (
                  <span className="replenish-action-dot" title={`Action: ${e.action}`}>
                    ⚡
                  </span>
                )}

                <span className="chart-x-label">{e.interval_start.substring(0, 5)}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
