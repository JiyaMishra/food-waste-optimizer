import React from 'react';
import { Database, PlusCircle } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  icon?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  actionLabel,
  onAction,
  icon,
}) => {
  return (
    <div className="empty-state-box">
      <div className="empty-state-icon">
        {icon || <Database size={40} className="text-slate-500" />}
      </div>
      <h3 className="empty-state-title">{title}</h3>
      <p className="empty-state-desc">{description}</p>
      {actionLabel && onAction && (
        <button type="button" onClick={onAction} className="btn btn--primary">
          <PlusCircle size={16} />
          <span>{actionLabel}</span>
        </button>
      )}
    </div>
  );
};
