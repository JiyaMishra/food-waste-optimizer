import React from 'react';

export type BadgeVariant =
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'neutral'
  | 'purple'
  | 'rush-high'
  | 'rush-normal'
  | 'rush-low';

interface StatusBadgeProps {
  label: string;
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
  dot?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  label,
  variant = 'neutral',
  size = 'md',
  dot = false,
}) => {
  return (
    <span className={`status-badge status-badge--${variant} status-badge--${size}`}>
      {dot && <span className="status-badge__dot" />}
      {label}
    </span>
  );
};
