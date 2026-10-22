import React, { useCallback, useEffect, useState } from 'react';
import {
  Utensils,
  Layers,
  Clock,
  ShieldCheck,
  AlertCircle,
  RefreshCw,
  Calculator,
  Sliders,
  CheckCircle,
  ArrowRight,
} from 'lucide-react';
import { api } from '../api/client';
import { MetricCard } from '../components/MetricCard';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { DemandUncertaintyChart } from '../charts/DemandUncertaintyChart';
import type {
  Dish,
  ForecastResponse,
  MealType,
  PlanRequest,
  PlanResponse,
} from '../types';

interface MealPlannerProps {
  selectedDate: string;
  selectedMeal: MealType;
  onNavigate: (page: string) => void;
}

const mealWindows: Record<MealType, { start: string; close: string; intervals: string[] }> = {
  breakfast: { start: '07:00', close: '09:30', intervals: ['07:00', '07:30', '08:00', '08:30'] },
  lunch: { start: '12:00', close: '14:00', intervals: ['12:00', '12:30', '13:00', '13:30'] },
  snacks: { start: '16:30', close: '18:15', intervals: ['16:30', '17:00', '17:30', '18:00'] },
  dinner: { start: '19:00', close: '21:00', intervals: ['19:00', '19:30', '20:00', '20:30'] },
};

export const MealPlanner: React.FC<MealPlannerProps> = ({
  selectedDate,
  selectedMeal,
  onNavigate,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const [menuItems, setMenuItems] = useState<Dish[]>([]);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [activePlan, setActivePlan] = useState<PlanResponse | null>(null);
  const [selectedDishId, setSelectedDishId] = useState<string>('D001');

  // Optimizer parameters
  const [batchMin, setBatchMin] = useState<number>(20);
  const [batchMax, setBatchMax] = useState<number>(500);
  const [capacity, setCapacity] = useState<number>(500);
  const [prepLeadMinutes, setPrepLeadMinutes] = useState<number>(30);
  const [currentStock, setCurrentStock] = useState<number>(0);
  const [recomputing, setRecomputing] = useState(false);

  const runOptimizer = useCallback(
    async (dishId: string, currentForecast?: ForecastResponse | null) => {
      const fcast = currentForecast || forecast;
      if (!fcast || fcast.rows.length === 0) return;

      const row = fcast.rows.find((r) => r.dish_id === dishId) || fcast.rows[0];
      const totalExp = row.prediction;
      const lowerExp = row.lower_bound;
      const upperExp = row.upper_bound;

      const win = mealWindows[selectedMeal] || mealWindows.breakfast;
      const shares = [0.2, 0.35, 0.3, 0.15];
      const intervals = win.intervals.map((t, idx) => ({
        interval_start: t,
        expected: totalExp * shares[idx],
        lower: lowerExp * shares[idx],
        upper: upperExp * shares[idx],
      }));

      setRecomputing(true);
      try {
        const planPayload: PlanRequest = {
          service_date: selectedDate,
          meal_type: selectedMeal,
          dish_external_id: dishId,
          intervals,
          current_stock: currentStock,
          batch_min: batchMin,
          batch_max: batchMax,
          kitchen_capacity: capacity,
          prep_lead_minutes: prepLeadMinutes,
          service_start: win.start,
          service_close: win.close,
          forecast_run_id: fcast.forecast_run_id,
          model_version: fcast.model_version,
          persist: true,
        };

        const planRes = await api.createPlan(planPayload);
        setActivePlan(planRes);
      } catch (err) {
        setError(err as Error);
      } finally {
        setRecomputing(false);
      }
    },
    [forecast, selectedDate, selectedMeal, currentStock, batchMin, batchMax, capacity, prepLeadMinutes]
  );

  const loadPlannerData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [menuRes, forecastRes] = await Promise.all([
        api.getMenu({ meal_type: selectedMeal }),
        api.getForecasts({ date: selectedDate, meal_type: selectedMeal, persist: true }),
      ]);

      setMenuItems(menuRes.items);
      setForecast(forecastRes);

      const targetDishId = forecastRes.rows[0]?.dish_id || 'D001';
      setSelectedDishId(targetDishId);

      await runOptimizer(targetDishId, forecastRes);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, [selectedDate, selectedMeal, runOptimizer]);

  useEffect(() => {
    loadPlannerData();
  }, [loadPlannerData]);

  if (loading) {
    return <LoadingState message="Calculating dish demand forecasts and batch constraints..." />;
  }

  if (error && !forecast) {
    return (
      <div className="page-section">
        <ErrorState
          error={error}
          onRetry={loadPlannerData}
          title="Demand Forecasting & Planning Failed"
        />
      </div>
    );
  }

  const selectedDishRow = forecast?.rows?.find((r) => r.dish_id === selectedDishId) || forecast?.rows?.[0];

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header-row">
        <div>
          <h2 className="page-title">Constrained Kitchen Meal Planner</h2>
          <p className="page-desc">
            Dish-level demand forecasts with empirical uncertainty bounds and split-batch kitchen optimization.
          </p>
        </div>

        <div className="header-action-group">
          <button
            type="button"
            className="btn btn--secondary"
            onClick={loadPlannerData}
            title="Refresh forecasts"
          >
            <RefreshCw size={15} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Uncertainty Bounds Chart */}
      {forecast?.rows && forecast.rows.length > 0 && (
        <div className="card-panel">
          <DemandUncertaintyChart rows={forecast.rows} unit="portions" />
          <div className="card-panel-footer">
            <span className="text-muted text-xs">
              Model: <code>{forecast.model_version}</code> • Schema: <code>{forecast.feature_schema_version}</code> •
              Residual Method: {forecast.interval_method}
            </span>
            <span className="text-amber-400 text-xs">
              Calibrated: {forecast.interval_is_calibrated ? 'Yes' : 'No (Empirical 10th/90th quantiles)'}
            </span>
          </div>
        </div>
      )}

      {/* Dish Selection & Optimizer Configuration */}
      <div className="overview-two-col-grid">
        {/* Menu Items Table */}
        <div className="card-panel">
          <div className="panel-header">
            <div>
              <h4 className="panel-title">Menu Catalogue for {selectedMeal.toUpperCase()}</h4>
              <p className="panel-subtitle">Select a dish to inspect and optimize batch preparation</p>
            </div>
            <StatusBadge label={`${menuItems.length} Dishes`} variant="info" size="sm" />
          </div>

          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Dish</th>
                  <th>ID</th>
                  <th>Category</th>
                  <th>Expected Demand</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {menuItems.map((dish) => {
                  const fRow = forecast?.rows.find((r) => r.dish_id === dish.external_id);
                  const isSelected = selectedDishId === dish.external_id;

                  return (
                    <tr
                      key={dish.external_id}
                      className={isSelected ? 'row--selected' : ''}
                      onClick={() => {
                        setSelectedDishId(dish.external_id);
                        runOptimizer(dish.external_id);
                      }}
                      style={{ cursor: 'pointer' }}
                    >
                      <td>
                        <strong>{dish.name}</strong>
                      </td>
                      <td>
                        <code>{dish.external_id}</code>
                      </td>
                      <td>{dish.category}</td>
                      <td>
                        {fRow ? (
                          <span className="font-semibold text-indigo-300">
                            {fRow.prediction.toFixed(0)} <span className="text-xs text-muted">portions</span>
                          </span>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td>
                        <button
                          type="button"
                          className={`btn btn--sm ${isSelected ? 'btn--accent' : 'btn--secondary'}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedDishId(dish.external_id);
                            runOptimizer(dish.external_id);
                          }}
                        >
                          {isSelected ? 'Selected' : 'Select'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Optimizer Parameter Controls */}
        <div className="card-panel">
          <div className="panel-header">
            <div>
              <h4 className="panel-title">Batch Optimizer Constraints</h4>
              <p className="panel-subtitle">
                Fine-tune constraints for dish <code>{selectedDishId}</code>
              </p>
            </div>
            <Sliders size={18} className="text-indigo-400" />
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              runOptimizer(selectedDishId);
            }}
            className="optimizer-form"
          >
            <div className="form-grid-two">
              <div className="form-group">
                <label>Kitchen Capacity (portions)</label>
                <input
                  type="number"
                  className="form-input"
                  value={capacity}
                  onChange={(e) => setCapacity(Number(e.target.value))}
                  min={50}
                  max={2000}
                />
              </div>

              <div className="form-group">
                <label>Lead Time (minutes)</label>
                <input
                  type="number"
                  className="form-input"
                  value={prepLeadMinutes}
                  onChange={(e) => setPrepLeadMinutes(Number(e.target.value))}
                  min={10}
                  max={120}
                />
              </div>

              <div className="form-group">
                <label>Batch Min (portions)</label>
                <input
                  type="number"
                  className="form-input"
                  value={batchMin}
                  onChange={(e) => setBatchMin(Number(e.target.value))}
                  min={5}
                  max={100}
                />
              </div>

              <div className="form-group">
                <label>Batch Max (portions)</label>
                <input
                  type="number"
                  className="form-input"
                  value={batchMax}
                  onChange={(e) => setBatchMax(Number(e.target.value))}
                  min={100}
                  max={1000}
                />
              </div>

              <div className="form-group">
                <label>Current Initial Stock (portions)</label>
                <input
                  type="number"
                  className="form-input"
                  value={currentStock}
                  onChange={(e) => setCurrentStock(Number(e.target.value))}
                  min={0}
                  max={500}
                />
              </div>
            </div>

            <button
              type="submit"
              className="btn btn--primary btn--full mt-4"
              disabled={recomputing}
            >
              <Calculator size={15} />
              <span>{recomputing ? 'Recomputing Plan...' : 'Recompute Split-Batch Plan'}</span>
            </button>
          </form>
        </div>
      </div>

      {/* Optimized Batch Plan Output Card */}
      {activePlan && (
        <div className="card-panel">
          <div className="panel-header">
            <div>
              <h4 className="panel-title">Optimized Batch Dispatch Recommendation</h4>
              <p className="panel-subtitle">
                Deterministic constrained plan balancing leftover risk against shortage risk (8× weight)
              </p>
            </div>
            <div className="header-badges">
              <StatusBadge label="Approval: Proposed" variant="warning" />
              <StatusBadge label="Simulation Only" variant="purple" />
            </div>
          </div>

          <div className="metric-cards-grid">
            <MetricCard
              title="Initial Batch (Prep Before Service)"
              value={activePlan.initial_quantity.toFixed(0)}
              unit="portions"
              subtitle="Covers expected demand up to first replenishment window"
              variant="accent"
              icon={<Layers size={20} className="text-cyan-400" />}
            />

            <MetricCard
              title="Dynamic Reserve Batch"
              value={activePlan.reserve_quantity.toFixed(0)}
              unit="portions"
              subtitle="Held unpeeled / uncooked until replenishment trigger"
              variant="default"
              icon={<Utensils size={20} className="text-indigo-400" />}
            />

            <MetricCard
              title="Replenishment Trigger"
              value={activePlan.replenishment_trigger.toFixed(0)}
              unit="portions"
              subtitle="Reserve prep initiated if stock drops below this threshold"
              variant="warning"
              icon={<Clock size={20} className="text-amber-400" />}
            />

            <MetricCard
              title="Expected Leftover / Shortage"
              value={`${activePlan.expected_leftover.toFixed(1)} / ${activePlan.expected_shortage.toFixed(1)}`}
              unit="portions"
              subtitle={`Objective Value: ${activePlan.objective_value.toFixed(2)}`}
              variant="default"
              icon={<ShieldCheck size={20} className="text-emerald-400" />}
            />
          </div>

          {/* Rationale & Constraint Checks */}
          <div className="plan-details-box mt-4">
            <h5 className="details-title">Optimizer Rationale</h5>
            <p className="details-text">{activePlan.rationale}</p>

            <h5 className="details-title mt-3">Hard Constraint Checks</h5>
            <div className="constraints-checklist">
              {Object.entries(activePlan.constraint_checks || {}).map(([key, check]) => (
                <div key={key} className="constraint-item">
                  {check.satisfied ? (
                    <CheckCircle size={16} className="text-emerald-400" />
                  ) : (
                    <AlertCircle size={16} className="text-rose-400" />
                  )}
                  <span className="constraint-name">{key}:</span>
                  <span className="constraint-desc">{check.detail}</span>
                </div>
              ))}
            </div>

            <div className="plan-action-footer mt-4 flex items-center justify-between pt-3 border-t border-slate-700/50">
              <span className="text-sm text-slate-400">
                Active Dish: <strong className="text-emerald-400">{selectedDishRow?.dish_name || activePlan.dish_external_id}</strong> (Forecast: {selectedDishRow?.prediction.toFixed(0) ?? 280} portions)
              </span>
              <button
                type="button"
                className="btn btn--primary"
                onClick={() => onNavigate('kitchen-simulation')}
              >
                <span>Launch Kitchen Simulation</span>
                <ArrowRight size={15} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
