import React, { useCallback, useEffect, useState } from 'react';
import {
  Users,
  Utensils,
  AlertTriangle,
  ShieldAlert,
  Play,
  RotateCw,
  ArrowRight,
  Activity,
} from 'lucide-react';
import { api } from '../api/client';
import { MetricCard } from '../components/MetricCard';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { ArrivalsTimelineChart } from '../charts/ArrivalsTimelineChart';
import type {
  AvailabilityResponse,
  ForecastResponse,
  MealRun,
  MealType,
  SyntheticContext,
} from '../types';

interface OverviewProps {
  selectedDate: string;
  selectedMeal: MealType;
  onNavigate: (page: string) => void;
}

export const Overview: React.FC<OverviewProps> = ({
  selectedDate,
  selectedMeal,
  onNavigate,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [startingRun, setStartingRun] = useState(false);

  const [context, setContext] = useState<SyntheticContext | null>(null);
  const [availability, setAvailability] = useState<AvailabilityResponse | null>(null);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [latestRuns, setLatestRuns] = useState<MealRun[]>([]);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Parallel fetch of context, availability, forecast, and recent runs
      const [ctxRes, availRes, fcastRes, runsRes] = await Promise.allSettled([
        api.getContext({ date: selectedDate, hostel_id: 'H01' }),
        api.calculateAvailability({
          date: selectedDate,
          meal_type: selectedMeal,
          hostel_id: 'H01',
          mess_id: 'M01',
          attendance_probability: 0.65,
          persist: false,
        }),
        api.getForecasts({
          date: selectedDate,
          meal_type: selectedMeal,
          persist: false,
        }),
        api.listSimulationRuns({ limit: 5 }),
      ]);

      if (ctxRes.status === 'fulfilled') setContext(ctxRes.value);
      if (availRes.status === 'fulfilled') setAvailability(availRes.value);
      if (fcastRes.status === 'fulfilled') setForecast(fcastRes.value);
      if (runsRes.status === 'fulfilled') setLatestRuns(runsRes.value.items);

      if (
        ctxRes.status === 'rejected' &&
        availRes.status === 'rejected' &&
        fcastRes.status === 'rejected'
      ) {
        setError(ctxRes.reason as Error);
      }
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, [selectedDate, selectedMeal]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleStartRun = async () => {
    setStartingRun(true);
    try {
      await api.runPlanningAgent({
        service_date: selectedDate,
        meal_type: selectedMeal,
        hostel_id: 'H01',
        mess_id: 'M01',
        attendance_probability: 0.65,
        current_stock: 0,
        batch_min: 20,
        batch_max: 500,
        kitchen_capacity: 500,
        prep_lead_minutes: 30,
        persist: true,
      });
      await loadData();
      onNavigate('kitchen-simulation');
    } catch (err) {
      setError(err as Error);
    } finally {
      setStartingRun(false);
    }
  };

  if (loading) {
    return <LoadingState message="Fetching service overview and synthetic forecasts..." />;
  }

  if (error && !forecast && !context) {
    return (
      <div className="page-section">
        <ErrorState
          error={error}
          onRetry={loadData}
          title="Could not load overview data from backend"
        />
        <EmptyState
          title="No Synthetic Data Initialized"
          description="It appears the synthetic database has not been initialized or the ML model artifact is missing. Initialize synthetic data and train the model."
          actionLabel="Go to Settings & Data"
          onAction={() => onNavigate('settings-data')}
        />
      </div>
    );
  }

  const primaryDishForecast = forecast?.rows?.[0];
  const totalPredictedPortions = forecast?.rows
    ? forecast.rows.reduce((sum, r) => sum + r.prediction, 0)
    : (availability?.expected_arrivals ?? 280);

  // Interval timeline tailored to meal type
  const mealIntervalConfigs: Record<MealType, { times: string[]; notes: string[] }> = {
    breakfast: {
      times: ['07:00', '07:30', '08:00', '08:30'],
      notes: [
        'Early morning sports & early lab cohort arrivals',
        'Peak breakfast rush ahead of 08:00 AM lectures',
        'Secondary arrival wave for 09:00 AM classes',
        'Late breakfast service wind-down before 09:30 close',
      ],
    },
    lunch: {
      times: ['12:00', '12:30', '13:00', '13:30'],
      notes: [
        'Early lunch cohort release from morning blocks',
        'Peak lunch rush across academic hostels',
        'Secondary afternoon laboratory arrivals',
        'Afternoon service close before 14:00',
      ],
    },
    snacks: {
      times: ['16:30', '17:00', '17:30', '18:00'],
      notes: [
        'Evening tea kickoff & snack arrival surge (4:30 PM)',
        'Peak snack and beverage rush after lab completions',
        'Post-sports and evening study cohort arrivals',
        'Snack window close before 18:15',
      ],
    },
    dinner: {
      times: ['19:00', '19:30', '20:00', '20:30'],
      notes: [
        'Early diner influx from campus sports/library',
        'Core dinner rush across residential blocks',
        'Secondary evening diner wave',
        'Night service wind-down before 21:00 close',
      ],
    },
  };

  const currentMealConfig = mealIntervalConfigs[selectedMeal];
  const intervalShares = [0.18, 0.38, 0.28, 0.16];
  const rushClasses: Array<'low' | 'normal' | 'high'> = ['low', 'high', 'normal', 'low'];

  const sampleTimelineData = currentMealConfig.times.map((t, idx) => ({
    time: t,
    arrivals: totalPredictedPortions * intervalShares[idx],
    expected: totalPredictedPortions * intervalShares[idx],
    rushClass: rushClasses[idx],
    contextNote: currentMealConfig.notes[idx],
  }));

  return (
    <div className="page-container">
      {/* Top Banner and Quick Actions */}
      <div className="page-header-row">
        <div>
          <h2 className="page-title">Autonomous Meal Operations Overview</h2>
          <p className="page-desc">
            Synthetic demand intelligence, context-driven availability, and real-time intervention monitoring.
          </p>
        </div>

        <div className="header-action-group">
          <button
            type="button"
            className="btn btn--secondary"
            onClick={loadData}
            title="Refresh current service metrics"
          >
            <RotateCw size={15} />
            <span>Refresh</span>
          </button>

          <button
            type="button"
            className="btn btn--primary"
            onClick={handleStartRun}
            disabled={startingRun}
            id="btn-start-run"
          >
            <Play size={15} />
            <span>{startingRun ? 'Orchestrating Run...' : 'Start Meal Simulation'}</span>
          </button>
        </div>
      </div>

      {/* KPI Cards Row */}
      <div className="metric-cards-grid">
        <MetricCard
          id="metric-expected-attendance"
          title="Expected Attendance"
          value={availability?.expected_arrivals ?? '—'}
          unit="residents"
          subtitle={`Occupancy: ${((context?.occupancy_rate ?? 0) * 100).toFixed(1)}% (${context?.occupied_count ?? 0}/${context?.capacity ?? 0})`}
          icon={<Users size={20} className="text-cyan-400" />}
          denominatorNote="Calculated as available_population × 0.65 meal probability"
        />

        <MetricCard
          id="metric-forecast-demand"
          title="Forecast Meal Demand"
          value={totalPredictedPortions ? totalPredictedPortions.toFixed(0) : '—'}
          unit="portions"
          subtitle={
            primaryDishForecast
              ? `Main Dish (${primaryDishForecast.dish_id}): ${primaryDishForecast.prediction.toFixed(0)} portions`
              : 'Multi-dish aggregate'
          }
          uncertaintyRange={
            primaryDishForecast
              ? `${primaryDishForecast.lower_bound.toFixed(0)} – ${primaryDishForecast.upper_bound.toFixed(0)} portions`
              : undefined
          }
          icon={<Utensils size={20} className="text-indigo-400" />}
          denominatorNote="Model: context-rf-v4 with 80% empirical quantile residual bounds"
        />

        <MetricCard
          id="metric-waste-risk"
          title="Pre-Meal Waste Risk"
          value={context?.rain_mm && context.rain_mm > 15 ? 'Moderate' : 'Low'}
          unit="level"
          variant={context?.rain_mm && context.rain_mm > 15 ? 'warning' : 'success'}
          subtitle={
            context?.rain_mm && context.rain_mm > 15
              ? `Heavy rain (${context.rain_mm.toFixed(1)}mm) may delay arrivals`
              : 'Demand and attendance well aligned'
          }
          icon={<AlertTriangle size={20} className="text-amber-400" />}
          denominatorNote="Rule-based heuristic evaluated prior to kitchen preparation"
        />

        <MetricCard
          id="metric-shortage-risk"
          title="Shortage Risk"
          value="Low (<2%)"
          unit="risk"
          variant="success"
          subtitle="Protected by split-batch reserve buffer"
          icon={<ShieldAlert size={20} className="text-emerald-400" />}
          denominatorNote="Optimizer weighs shortage 8× heavier than leftover"
        />
      </div>

      {/* Main Grid: Arrivals Timeline + Quick Links */}
      <div className="overview-two-col-grid">
        {/* Arrival Flow Chart */}
        <div className="card-panel">
          <ArrivalsTimelineChart
            data={sampleTimelineData}
            title={`${selectedMeal.toUpperCase()} Arrival Flow — ${selectedDate}`}
            onSelectInterval={() => onNavigate('rush-timeline')}
          />
          <div className="card-panel-footer">
            <span className="text-muted text-xs">
              Showing 30-min intervals. Click bars to inspect timeline rationale.
            </span>
            <button
              type="button"
              className="btn-text-link"
              onClick={() => onNavigate('rush-timeline')}
            >
              <span>Detailed Timeline</span>
              <ArrowRight size={13} />
            </button>
          </div>
        </div>

        {/* System & Policy Status */}
        <div className="card-panel">
          <div className="panel-header">
            <div>
              <h4 className="panel-title">Optimization Pipeline Status</h4>
              <p className="panel-subtitle">Autonomous agents &amp; batch policy execution</p>
            </div>
            <StatusBadge label="Simulated Mode" variant="purple" />
          </div>

          <div className="pipeline-steps-list">
            <div className="pipeline-step-item">
              <div className="step-icon step-icon--completed">✓</div>
              <div className="step-details">
                <span className="step-name">Context &amp; Weather Ingestion</span>
                <span className="step-sub">
                  Temp: {context?.temperature_c ?? 32}°C • Rain: {context?.rain_mm ?? 0}mm ({context?.weather_label ?? 'clear'})
                </span>
              </div>
              <button
                type="button"
                className="step-link-btn"
                onClick={() => onNavigate('context-availability')}
              >
                Inspect
              </button>
            </div>

            <div className="pipeline-step-item">
              <div className="step-icon step-icon--completed">✓</div>
              <div className="step-details">
                <span className="step-name">Random Forest Demand Prediction</span>
                <span className="step-sub">
                  Artifact: <code>context_model.joblib</code> • Cutoff: {forecast?.forecast_cutoff ?? '2026-08-31'}
                </span>
              </div>
              <button
                type="button"
                className="step-link-btn"
                onClick={() => onNavigate('meal-planner')}
              >
                Planner
              </button>
            </div>

            <div className="pipeline-step-item">
              <div className="step-icon step-icon--completed">✓</div>
              <div className="step-details">
                <span className="step-name">Constrained Batch Optimizer</span>
                <span className="step-sub">
                  Initial Batch (70%) + Dynamic Reserve (30%) • Capacity: 500 portions
                </span>
              </div>
              <button
                type="button"
                className="step-link-btn"
                onClick={() => onNavigate('kitchen-simulation')}
              >
                Simulate
              </button>
            </div>

            <div className="pipeline-step-item">
              <div className="step-icon step-icon--completed">✓</div>
              <div className="step-details">
                <span className="step-name">Post-Meal Waste Evaluation</span>
                <span className="step-sub">
                  Separates plate waste, untouched leftovers &amp; shortage metrics
                </span>
              </div>
              <button
                type="button"
                className="step-link-btn"
                onClick={() => onNavigate('evaluation')}
              >
                Evaluate
              </button>
            </div>
          </div>

          <div className="pipeline-cta-box">
            <div className="cta-info">
              <Activity size={18} className="text-indigo-400" />
              <div>
                <strong>Ready for Service Execution</strong>
                <p>Run simulated kitchen dispatch with automated reserve batch triggers.</p>
              </div>
            </div>
            <button
              type="button"
              className="btn btn--accent btn--sm"
              onClick={() => onNavigate('kitchen-simulation')}
            >
              Open Live Simulation
            </button>
          </div>
        </div>
      </div>

      {/* Recent Simulation Runs Table */}
      <div className="card-panel">
        <div className="panel-header">
          <div>
            <h4 className="panel-title">Recent Simulation Runs</h4>
            <p className="panel-subtitle">Persisted policy runs comparing baseline vs context-aware batching</p>
          </div>
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            onClick={() => onNavigate('evaluation')}
          >
            Compare All Runs
          </button>
        </div>

        {latestRuns.length === 0 ? (
          <div className="panel-empty-text">
            No simulation runs recorded yet. Click "Start Meal Simulation" above to run the workflow.
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>Service Date</th>
                  <th>Meal</th>
                  <th>Policy ID</th>
                  <th>Status</th>
                  <th>Prepared</th>
                  <th>Leftover</th>
                  <th>Plate Waste</th>
                  <th>Shortage</th>
                </tr>
              </thead>
              <tbody>
                {latestRuns.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <code className="text-xs">{r.id.substring(0, 8)}...</code>
                    </td>
                    <td>{r.service_date}</td>
                    <td>
                      <span className="capitalize">{r.meal_type}</span>
                    </td>
                    <td>
                      <span
                        className={`policy-pill ${
                          r.policy_id.includes('context')
                            ? 'policy-pill--context'
                            : 'policy-pill--baseline'
                        }`}
                      >
                        {r.policy_id}
                      </span>
                    </td>
                    <td>
                      <StatusBadge
                        label={r.status}
                        variant={r.status === 'finished' ? 'success' : 'info'}
                        size="sm"
                      />
                    </td>
                    <td>{r.outcome?.prepared_total?.toFixed(0) ?? '—'}</td>
                    <td>{r.outcome?.untouched_leftover?.toFixed(1) ?? '—'}</td>
                    <td>{r.outcome?.plate_waste?.toFixed(1) ?? '—'}</td>
                    <td>{r.outcome?.shortage?.toFixed(1) ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
