import React, { useCallback, useEffect, useState } from 'react';
import {
  MapPin,
  Building,
  Users,
  CloudRain,
  AlertCircle,
  HelpCircle,
  RefreshCw,
  Info,
} from 'lucide-react';
import { api } from '../api/client';
import { MetricCard } from '../components/MetricCard';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import type { AvailabilityResponse, MealType, SyntheticContext } from '../types';

interface ContextAvailabilityProps {
  selectedDate: string;
  selectedMeal: MealType;
}

export const ContextAvailability: React.FC<ContextAvailabilityProps> = ({
  selectedDate,
  selectedMeal,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const [context, setContext] = useState<SyntheticContext | null>(null);
  const [availability, setAvailability] = useState<AvailabilityResponse | null>(null);

  const loadContextData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [ctxRes, availRes] = await Promise.all([
        api.getContext({ date: selectedDate, hostel_id: 'H01' }),
        api.calculateAvailability({
          date: selectedDate,
          meal_type: selectedMeal,
          hostel_id: 'H01',
          mess_id: 'M01',
          attendance_probability: 0.65,
          academic_slots: [{ group_id: 'H01_COHORT', unavailable_share: 0.2 }],
          group_sizes: { H01_COHORT: 200 },
          persist: true,
        }),
      ]);

      setContext(ctxRes);
      setAvailability(availRes);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, [selectedDate, selectedMeal]);

  useEffect(() => {
    loadContextData();
  }, [loadContextData]);

  if (loading) {
    return <LoadingState message="Fetching hostel occupancy, weather, and timetable availability..." />;
  }

  if (error && !context && !availability) {
    return (
      <div className="page-section">
        <ErrorState error={error} onRetry={loadContextData} title="Could not load context" />
      </div>
    );
  }

  const occupiedPop = availability?.occupied_population ?? context?.occupied_count ?? 574;
  const unavailPop = availability?.unavailable_population ?? 0;
  const availPop = availability?.available_population ?? occupiedPop;
  const expectedArrivals = availability?.expected_arrivals ?? Math.round(availPop * 0.65);

  return (
    <div className="page-container">
      <div className="page-header-row">
        <div>
          <h2 className="page-title">Hostel Context &amp; Population Availability</h2>
          <p className="page-desc">
            Multi-source synthetic context modeling: resident occupancy, academic schedule conflicts, and weather factors.
          </p>
        </div>

        <div className="header-action-group">
          <button type="button" className="btn btn--secondary" onClick={loadContextData}>
            <RefreshCw size={15} />
            <span>Refresh Context</span>
          </button>
        </div>
      </div>

      {/* KPI Row */}
      <div className="metric-cards-grid">
        <MetricCard
          title="Occupied Hostel Population"
          value={occupiedPop}
          unit="residents"
          subtitle={`Capacity: ${context?.capacity ?? 650} • Occupancy Rate: ${((context?.occupancy_rate ?? 0.88) * 100).toFixed(1)}%`}
          icon={<Building size={20} className="text-indigo-400" />}
          denominatorNote="Source: hostel_daily_state (synthetic)"
        />

        <MetricCard
          title="Academic / Event Unavailable"
          value={unavailPop}
          unit="residents"
          variant={unavailPop > 0 ? 'warning' : 'default'}
          subtitle={`Unavailable Share: ${((availability?.academic_unavailability_share ?? 0) * 100).toFixed(0)}%`}
          icon={<AlertCircle size={20} className="text-amber-400" />}
          denominatorNote="Conservative max() union between academic slot clashes & event participants"
        />

        <MetricCard
          title="Net Available Population"
          value={availPop}
          unit="residents"
          subtitle={`Available for ${selectedMeal} service`}
          icon={<Users size={20} className="text-cyan-400" />}
          denominatorNote="available_population = occupied_population - unavailable_population"
        />

        <MetricCard
          title="Expected Meal Diners"
          value={expectedArrivals}
          unit="diners"
          variant="accent"
          subtitle="Attendance Probability: 65%"
          icon={<MapPin size={20} className="text-emerald-400" />}
          denominatorNote="expected_arrivals = available_population × 0.65"
        />
      </div>

      {/* Weather & Event Details Panel */}
      <div className="overview-two-col-grid">
        <div className="card-panel">
          <div className="panel-header">
            <div>
              <h4 className="panel-title">Microclimate Weather Context</h4>
              <p className="panel-subtitle">Synthetically generated weather parameters for {selectedDate}</p>
            </div>
            <CloudRain size={20} className="text-indigo-400" />
          </div>

          <div className="weather-detail-grid">
            <div className="weather-card">
              <span className="weather-card-label">Conditions</span>
              <span className="weather-card-val capitalize">{context?.weather_label ?? 'Clear'}</span>
              <span className="weather-card-sub">Precipitation label</span>
            </div>

            <div className="weather-card">
              <span className="weather-card-label">Rainfall</span>
              <span className="weather-card-val">{context?.rain_mm?.toFixed(1) ?? 0} mm</span>
              <span className="weather-card-sub">Daily accumulation</span>
            </div>

            <div className="weather-card">
              <span className="weather-card-label">Temperature</span>
              <span className="weather-card-val">{context?.temperature_c?.toFixed(1) ?? 32}°C</span>
              <span className="weather-card-sub">Ambient average</span>
            </div>

            <div className="weather-card">
              <span className="weather-card-label">7-Day Occupancy Delta</span>
              <span className="weather-card-val">
                {context?.occupancy_delta_vs_7d !== null && context?.occupancy_delta_vs_7d !== undefined
                  ? `${(context.occupancy_delta_vs_7d * 100).toFixed(2)}%`
                  : '0.00%'}
              </span>
              <span className="weather-card-sub">Trending stability</span>
            </div>
          </div>

          <div className="data-sources-tag-row mt-4">
            <span className="text-xs text-muted">Ingested Sources:</span>
            {context?.data_sources?.map((src) => (
              <span key={src} className="data-source-tag">
                {src}
              </span>
            )) || <span className="data-source-tag">synthetic_context</span>}
          </div>
        </div>

        {/* Timetable Overlap & Limitations */}
        <div className="card-panel">
          <div className="panel-header">
            <div>
              <h4 className="panel-title">Schedule Overlap &amp; Limitations</h4>
              <p className="panel-subtitle">Academic cohort slots &amp; availability caveats</p>
            </div>
            <Info size={20} className="text-cyan-400" />
          </div>

          <div className="caveats-list">
            {availability?.caveats && availability.caveats.length > 0 ? (
              availability.caveats.map((c, i) => (
                <div key={i} className="caveat-item">
                  <AlertCircle size={16} className="text-amber-400 shrink-0" />
                  <span className="caveat-text">{c}</span>
                </div>
              ))
            ) : (
              <div className="caveat-item">
                <Info size={16} className="text-indigo-400 shrink-0" />
                <span className="caveat-text">
                  Standard timetable rules applied; no missing synthetic records detected for this date.
                </span>
              </div>
            )}

            <div className="caveat-item caveat-item--neutral">
              <HelpCircle size={16} className="text-slate-400 shrink-0" />
              <span className="caveat-text">
                Academic slots are modeled at cohort level. Event and academic unavailability may overlap;
                a conservative <code>max()</code> union is evaluated to prevent double subtraction.
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
