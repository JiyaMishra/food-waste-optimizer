import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { ApiError } from '../api/client';

interface ErrorStateProps {
  error: Error | ApiError | string | null;
  onRetry?: () => void;
  title?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  error,
  onRetry,
  title = 'An API error occurred',
}) => {
  if (!error) return null;

  const isApiError = error instanceof ApiError;
  const errorCode = isApiError ? error.code : 'CLIENT_ERROR';
  const errorMessage = typeof error === 'string' ? error : error.message;
  const requestId = isApiError ? error.requestId : null;
  const details = isApiError ? error.details : null;

  // Helpful remedies for known Person B domain error codes
  let remedy: string | null = null;
  if (errorCode === 'MODEL_ARTIFACT_MISSING') {
    remedy = 'The ML model artifact has not been trained yet. Go to Settings & Data and click "Train Demand Model" first.';
  } else if (errorCode === 'CONTEXT_NOT_FOUND') {
    remedy = 'No synthetic context was found for the requested date. Go to Settings & Data to generate synthetic data.';
  } else if (errorCode === 'FORECAST_DATE_NOT_FUTURE') {
    remedy = 'Forecast date must be strictly after the training cutoff (e.g. 2026-09-01).';
  } else if (errorCode === 'NETWORK_ERROR') {
    remedy = 'Cannot connect to backend at http://localhost:8000. Ensure uvicorn is running.';
  }

  return (
    <div className="error-state-card" role="alert">
      <div className="error-state-header">
        <div className="error-icon-box">
          <AlertCircle size={24} className="text-rose-400" />
        </div>
        <div>
          <h4 className="error-state-title">{title}</h4>
          <span className="error-code-badge">Error Code: {errorCode}</span>
        </div>
      </div>

      <p className="error-state-message">{errorMessage}</p>

      {remedy && (
        <div className="error-remedy-box">
          <strong>Suggested Remedy:</strong> {remedy}
        </div>
      )}

      {Boolean(details && typeof details === 'object') && (
        <details className="error-details-accordion">
          <summary>Technical Details &amp; Validation Payload</summary>
          <pre className="error-details-pre">{JSON.stringify(details, null, 2)}</pre>
        </details>
      )}

      <div className="error-state-actions">
        {onRetry && (
          <button type="button" onClick={onRetry} className="btn btn--secondary btn--sm">
            <RefreshCw size={14} />
            <span>Retry Request</span>
          </button>
        )}
        {requestId && <span className="request-id-tag">Request ID: {requestId}</span>}
      </div>
    </div>
  );
};
