import React from 'react';
import { HelpCircle } from 'lucide-react';

interface MetricCardProps {
  id?: string;
  title: string;
  value: string | number | null | undefined;
  unit?: string; // e.g. "portions", "kg", "%", "min"
  subtitle?: string;
  trend?: {
    value: string;
    positive?: boolean; // true if good
    neutral?: boolean;
  };
  icon?: React.ReactNode;
  denominatorNote?: string;
  uncertaintyRange?: string; // e.g. "183.86 – 346.12"
  variant?: 'default' | 'accent' | 'warning' | 'danger' | 'success';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  id,
  title,
  value,
  unit,
  subtitle,
  trend,
  icon,
  denominatorNote,
  uncertaintyRange,
  variant = 'default',
}) => {
  const isUndefined = value === null || value === undefined || value === 'null';

  return (
    <div id={id} className={`metric-card metric-card--${variant}`}>
      <div className="metric-card__header">
        <span className="metric-card__title">{title}</span>
        {icon && <div className="metric-card__icon">{icon}</div>}
      </div>

      <div className="metric-card__body">
        <div className="metric-card__value-row">
          <span className="metric-card__value">
            {isUndefined ? '—' : value}
          </span>
          {unit && !isUndefined && (
            <span className="metric-card__unit" title={`Unit: ${unit}`}>
              {unit}
            </span>
          )}
        </div>

        {trend && (
          <div
            className={`metric-card__trend ${
              trend.neutral
                ? 'trend-neutral'
                : trend.positive
                ? 'trend-positive'
                : 'trend-negative'
            }`}
          >
            <span>{trend.value}</span>
          </div>
        )}
      </div>

      {(subtitle || uncertaintyRange || denominatorNote) && (
        <div className="metric-card__footer">
          {uncertaintyRange && (
            <div className="metric-card__uncertainty">
              <span className="uncertainty-label">80% Uncertainty:</span>
              <span className="uncertainty-val">{uncertaintyRange}</span>
            </div>
          )}

          {subtitle && <p className="metric-card__subtitle">{subtitle}</p>}

          {denominatorNote && (
            <div className="metric-card__denominator" title={denominatorNote}>
              <HelpCircle size={13} />
              <span>{denominatorNote}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
