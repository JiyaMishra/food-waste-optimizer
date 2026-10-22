import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingStateProps {
  message?: string;
  subtext?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading data from backend...',
  subtext = 'Connecting to FastAPI simulation engine',
}) => {
  return (
    <div className="loading-state-box">
      <div className="loading-spinner-wrapper">
        <Loader2 className="animate-spin text-indigo-400" size={36} />
      </div>
      <h3 className="loading-state-title">{message}</h3>
      {subtext && <p className="loading-state-subtext">{subtext}</p>}
      <div className="loading-skeleton-lines">
        <div className="skeleton-line skeleton-line--long" />
        <div className="skeleton-line skeleton-line--med" />
        <div className="skeleton-line skeleton-line--short" />
      </div>
    </div>
  );
};
