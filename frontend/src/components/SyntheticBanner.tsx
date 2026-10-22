import React from 'react';
import { AlertTriangle, Info } from 'lucide-react';

interface SyntheticBannerProps {
  compact?: boolean;
}

export const SyntheticBanner: React.FC<SyntheticBannerProps> = ({ compact = false }) => {
  if (compact) {
    return (
      <div
        id="synthetic-banner-compact"
        className="synthetic-badge-pill"
        title="All records, forecasts, diagnoses and outcomes are synthetic simulations. No live kitchen action is executed."
      >
        <span className="pulsing-dot" />
        <strong>SYNTHETIC DEMO DATA</strong>
        <span>•</span>
        <span>Simulation Only (No Live Kitchen Actions)</span>
      </div>
    );
  }

  return (
    <aside
      id="synthetic-banner"
      aria-label="Synthetic Data Notice"
      className="synthetic-banner-card"
    >
      <div className="synthetic-banner-icon-box">
        <AlertTriangle className="synthetic-banner-icon" size={20} />
      </div>
      <div className="synthetic-banner-content">
        <div className="synthetic-banner-title">
          <span>SYNTHETIC PROTOTYPE &amp; SIMULATED DATA</span>
          <span className="synthetic-pill-tag">Research &amp; Demonstration Only</span>
        </div>
        <p className="synthetic-banner-text">
          All resident counts, meal arrivals, demand forecasts, waste diagnoses, and kitchen batch interventions
          are entirely <strong>synthetic</strong>. No real VIT cafeteria systems, biometric attendance, or live
          appliances are connected. All optimizer actions are strictly simulated.
        </p>
      </div>
      <div className="synthetic-banner-meta">
        <Info size={16} />
        <span>Scenario: <code>synthetic_baseline_v1</code></span>
      </div>
    </aside>
  );
};
