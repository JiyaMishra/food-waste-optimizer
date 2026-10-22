import React, { useState } from 'react';

export interface TimelineIntervalData {
  time: string;
  arrivals: number; // in portions
  expected?: number; // predicted portions
  rushClass: 'low' | 'normal' | 'high';
  contextNote?: string;
}

interface ArrivalsTimelineChartProps {
  data: TimelineIntervalData[];
  title?: string;
  unit?: string;
  selectedInterval?: string | null;
  onSelectInterval?: (interval: string) => void;
}

export const ArrivalsTimelineChart: React.FC<ArrivalsTimelineChartProps> = ({
  data,
  title = 'Student Arrival Flow by Service Interval',
  unit = 'portions',
  selectedInterval,
  onSelectInterval,
}) => {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  if (!data || data.length === 0) {
    return <div className="chart-empty">No interval arrival data to display.</div>;
  }

  const maxVal = Math.max(...data.map((d) => Math.max(d.arrivals, d.expected || 0)), 10) * 1.15;
  const chartHeight = 180;

  return (
    <div className="chart-container">
      <div className="chart-header">
        <div>
          <h4 className="chart-title">{title}</h4>
          <span className="chart-subtitle">
            Synthetic attendance waves across 30-minute intervals (unit: {unit})
          </span>
        </div>
        <div className="chart-legend">
          <span className="legend-item">
            <span className="legend-color legend-color--realized" /> Realized Arrivals
          </span>
          <span className="legend-item">
            <span className="legend-color legend-color--predicted" /> Forecast Demand
          </span>
          <span className="legend-item">
            <span className="legend-color legend-color--high" /> Peak Rush
          </span>
        </div>
      </div>

      <div className="chart-body" style={{ height: `${chartHeight}px` }}>
        {/* Y-axis labels */}
        <div className="chart-y-axis">
          <span>{Math.round(maxVal)} {unit}</span>
          <span>{Math.round(maxVal / 2)} {unit}</span>
          <span>0 {unit}</span>
        </div>

        {/* Bars and lines */}
        <div className="chart-bars-track">
          {data.map((item, idx) => {
            const barHeightPct = Math.min(100, (item.arrivals / maxVal) * 100);
            const expectedHeightPct = item.expected ? Math.min(100, (item.expected / maxVal) * 100) : null;
            const isSelected = selectedInterval === item.time;
            const isHovered = hoveredIdx === idx;

            return (
              <div
                key={item.time}
                className={`chart-bar-col ${isSelected ? 'is-selected' : ''}`}
                onClick={() => onSelectInterval && onSelectInterval(item.time)}
                onMouseEnter={() => setHoveredIdx(idx)}
                onMouseLeave={() => setHoveredIdx(null)}
              >
                {/* Tooltip */}
                {isHovered && (
                  <div className="chart-tooltip">
                    <strong>{item.time}</strong>
                    <div>Arrivals: {item.arrivals.toFixed(1)} {unit}</div>
                    {item.expected !== undefined && (
                      <div>Forecast: {item.expected.toFixed(1)} {unit}</div>
                    )}
                    <div className={`rush-tag rush-tag--${item.rushClass}`}>
                      Rush: {item.rushClass.toUpperCase()}
                    </div>
                    {item.contextNote && <div className="tooltip-note">{item.contextNote}</div>}
                  </div>
                )}

                <div className="bar-wrapper">
                  {/* Expected forecast marker line */}
                  {expectedHeightPct !== null && (
                    <div
                      className="forecast-target-line"
                      style={{ bottom: `${expectedHeightPct}%` }}
                      title={`Forecast: ${item.expected?.toFixed(1)}`}
                    />
                  )}

                  {/* Realized bar */}
                  <div
                    className={`chart-bar bar--${item.rushClass} ${isSelected ? 'bar--active' : ''}`}
                    style={{ height: `${barHeightPct}%` }}
                  />
                </div>

                <span className="chart-x-label">{item.time}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
