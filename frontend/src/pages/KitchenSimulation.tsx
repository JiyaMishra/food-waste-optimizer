import React, { useEffect, useState } from 'react';
import {
  Flame,
  Play,
  SkipForward,
  CheckCircle,
  RotateCcw,
  Zap,
  Clock,
  Layers,
  ShieldCheck,
  AlertOctagon,
  TrendingDown,
  Info,
} from 'lucide-react';
import { api } from '../api/client';
import { MetricCard } from '../components/MetricCard';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { StockFlowChart } from '../charts/StockFlowChart';
import type { MealRun, MealType, Outcome, SimulationEvent } from '../types';

interface KitchenSimulationProps {
  selectedDate: string;
  selectedMeal: MealType;
  onNavigate: (page: string) => void;
}

export const KitchenSimulation: React.FC<KitchenSimulationProps> = ({
  selectedDate,
  selectedMeal,
  onNavigate,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // Active simulation run state
  const [activeRun, setActiveRun] = useState<MealRun | null>(null);
  const [events, setEvents] = useState<SimulationEvent[]>([]);
  const [outcome, setOutcome] = useState<Outcome | null>(null);

  // Simulation controls state
  const [advancing, setAdvancing] = useState(false);
  const [policyType, setPolicyType] = useState<'context_aware_split' | 'baseline_fixed'>(
    'context_aware_split'
  );
  const [initialQty, setInitialQty] = useState<number>(380);
  const [reserveQty, setReserveQty] = useState<number>(100);
  const [triggerQty, setTriggerQty] = useState<number>(80);

  // Load latest run on mount if any
  const loadLatestRun = async () => {
    setLoading(true);
    setError(null);
    try {
      const runs = await api.listSimulationRuns({ limit: 1 });
      if (runs.items && runs.items.length > 0) {
        const runId = runs.items[0].id;
        const detail = await api.getSimulationRun(runId);
        setActiveRun(detail.run);
        setEvents(detail.events || []);
        if (detail.outcome) setOutcome(detail.outcome as Outcome);
      }
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLatestRun();
  }, []);

  // Action: Start new simulation
  const handleStartSimulation = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.startSimulation({
        service_date: selectedDate,
        meal_type: selectedMeal,
        dish_external_id: 'D001',
        policy: policyType,
        use_historical: true,
        historical_date: '2026-08-31',
        plan: {
          initial_qty: initialQty,
          reserve_qty: policyType === 'context_aware_split' ? reserveQty : 0,
          trigger_qty: policyType === 'context_aware_split' ? triggerQty : 0,
        },
        capacity: 500,
        consumption_rate: 0.85,
        prep_lead_intervals: 1,
        forecast_expected: 288,
        persist: true,
      });

      const detail = await api.getSimulationRun(res.id);
      setActiveRun(detail.run);
      setEvents(detail.events || []);
      setOutcome(null);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  };

  // Action: Step one interval
  const handleStepInterval = async () => {
    if (!activeRun) return;
    setAdvancing(true);
    setError(null);
    try {
      const res = await api.stepSimulation(activeRun.id);
      setActiveRun(res.run);
      setEvents((prev) => [...prev, res.event]);

      if (res.finished) {
        // Automatically fetch final outcome
        const finalDetail = await api.getSimulationRun(activeRun.id);
        if (finalDetail.outcome) setOutcome(finalDetail.outcome as Outcome);
      }
    } catch (err) {
      setError(err as Error);
    } finally {
      setAdvancing(false);
    }
  };

  // Action: Finish meal service
  const handleFinishSimulation = async () => {
    if (!activeRun) return;
    setAdvancing(true);
    setError(null);
    try {
      const res = await api.finishSimulation(activeRun.id);
      setActiveRun(res.run);
      if (res.outcome) setOutcome(res.outcome as Outcome);
      if (res.events) setEvents(res.events);
    } catch (err) {
      setError(err as Error);
    } finally {
      setAdvancing(false);
    }
  };

  // Action: Quick comparison run (Baseline vs Context-Aware)
  const handleRunFullComparison = async () => {
    setLoading(true);
    setError(null);
    try {
      const comp = await api.compareSimulations({
        service_date: selectedDate,
        meal_type: selectedMeal,
        dish_external_id: 'D001',
        use_historical: true,
        historical_date: '2026-08-31',
        capacity: 500,
        forecast_expected: 288.38,
        persist: true,
      });

      // Show context-aware run by default
      setActiveRun(comp.context_run.run);
      setEvents(comp.context_run.events);
      if (comp.context_run.outcome) setOutcome(comp.context_run.outcome);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  };

  const isRunning = activeRun && activeRun.status === 'running';
  const isFinished = activeRun && activeRun.status === 'finished';
  const latestEvent = events[events.length - 1];

  return (
    <div className="page-container">
      <div className="page-header-row">
        <div>
          <h2 className="page-title">Live Kitchen Dispatch Simulation</h2>
          <p className="page-desc">
            Step through real-time 30-minute intervals to observe stock depletion, dynamic reserve triggers, and final food waste outcomes.
          </p>
        </div>

        <div className="header-action-group">
          <button
            type="button"
            className="btn btn--accent"
            onClick={handleRunFullComparison}
            disabled={loading}
            title="Automatically run and compare both policies on identical synthetic arrivals"
          >
            <Zap size={15} />
            <span>Simulate Compare (Auto)</span>
          </button>
        </div>
      </div>

      {error && <ErrorState error={error} onRetry={loadLatestRun} />}

      {/* Control Panel Strip */}
      <div className="card-panel simulation-controls-strip">
        <div className="controls-left">
          <div className="control-group">
            <span className="control-label">Policy Model:</span>
            <select
              className="select-meal"
              value={policyType}
              onChange={(e) =>
                setPolicyType(e.target.value as 'context_aware_split' | 'baseline_fixed')
              }
              disabled={isRunning || advancing}
            >
              <option value="context_aware_split">Context-Aware Split Batch (Adaptive Reserve)</option>
              <option value="baseline_fixed">Fixed Single Batch (Baseline Policy)</option>
            </select>
          </div>

          {policyType === 'context_aware_split' && (
            <>
              <div className="control-group">
                <span className="control-label">Initial Qty:</span>
                <input
                  type="number"
                  className="form-input form-input--sm"
                  value={initialQty}
                  onChange={(e) => setInitialQty(Number(e.target.value))}
                  disabled={isRunning || advancing}
                />
              </div>

              <div className="control-group">
                <span className="control-label">Reserve Qty:</span>
                <input
                  type="number"
                  className="form-input form-input--sm"
                  value={reserveQty}
                  onChange={(e) => setReserveQty(Number(e.target.value))}
                  disabled={isRunning || advancing}
                />
              </div>

              <div className="control-group">
                <span className="control-label">Trigger Qty:</span>
                <input
                  type="number"
                  className="form-input form-input--sm"
                  value={triggerQty}
                  onChange={(e) => setTriggerQty(Number(e.target.value))}
                  disabled={isRunning || advancing}
                />
              </div>
            </>
          )}
        </div>

        <div className="controls-right">
          {!isRunning && (
            <button
              type="button"
              className="btn btn--primary"
              onClick={handleStartSimulation}
              disabled={loading || advancing}
              id="btn-start-sim"
            >
              <Play size={15} />
              <span>Start New Service Run</span>
            </button>
          )}

          {isRunning && (
            <>
              <button
                type="button"
                className="btn btn--accent"
                onClick={handleStepInterval}
                disabled={advancing}
                id="btn-step-interval"
              >
                <SkipForward size={15} />
                <span>{advancing ? 'Simulating...' : 'Advance One Interval (+30m)'}</span>
              </button>

              <button
                type="button"
                className="btn btn--secondary"
                onClick={handleFinishSimulation}
                disabled={advancing}
                id="btn-finish-meal"
              >
                <CheckCircle size={15} />
                <span>Finish Meal Service</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Live Run HUD (Heads-up Display) */}
      {activeRun ? (
        <>
          <div className="metric-cards-grid">
            <MetricCard
              title="Simulation State"
              value={activeRun.status.toUpperCase()}
              unit={activeRun.policy_id}
              variant={isFinished ? 'success' : isRunning ? 'accent' : 'default'}
              subtitle={`Run ID: ${activeRun.id.substring(0, 8)}...`}
              icon={<Clock size={20} className="text-cyan-400" />}
            />

            <MetricCard
              title="Current Service Interval"
              value={`${activeRun.current_interval} / ${activeRun.intervals_total}`}
              unit="intervals"
              subtitle={
                latestEvent
                  ? `Time: ${latestEvent.interval_start.substring(0, 5)}`
                  : 'Starting at 07:00'
              }
              icon={<Flame size={20} className="text-amber-400" />}
            />

            <MetricCard
              title="Current Kitchen Stock"
              value={latestEvent ? latestEvent.stock_after.toFixed(1) : initialQty}
              unit="portions"
              subtitle={
                latestEvent && latestEvent.action !== 'none'
                  ? `⚡ Action: ${latestEvent.action} (${latestEvent.action_reason || ''})`
                  : 'Stock in hot-holding serving trays'
              }
              variant={
                latestEvent && latestEvent.stock_after < triggerQty ? 'warning' : 'default'
              }
              icon={<Layers size={20} className="text-indigo-400" />}
            />

            <MetricCard
              title="Cumulative Shortage (Unmet)"
              value={outcome ? outcome.shortage.toFixed(1) : '0.0'}
              unit="portions"
              variant={outcome && outcome.shortage > 0 ? 'danger' : 'success'}
              subtitle="Protection against stockouts"
              icon={<ShieldCheck size={20} className="text-emerald-400" />}
            />
          </div>

          {/* Interactive Stock Flow Chart */}
          <div className="card-panel">
            <StockFlowChart events={events} unit="portions" />
          </div>

          {/* Meal Close Final Outcome Section (Person C requirement: separate plate waste, leftovers, shortages) */}
          {isFinished && outcome && (
            <div className="card-panel final-outcome-panel" id="final-outcomes-card">
              <div className="panel-header">
                <div>
                  <h4 className="panel-title text-emerald-400">Meal Service Concluded — Final Outcomes</h4>
                  <p className="panel-subtitle">
                    Persisted verified quantities separating untouched leftovers, consumer plate waste, and shortages
                  </p>
                </div>
                <StatusBadge label="Run Completed" variant="success" />
              </div>

              <div className="outcome-metrics-grid">
                <div className="outcome-box">
                  <span className="outcome-label">Prepared Total</span>
                  <span className="outcome-val">{outcome.prepared_total.toFixed(1)}</span>
                  <span className="outcome-unit">portions</span>
                  <span className="outcome-sub">Total batch dispatch</span>
                </div>

                <div className="outcome-box">
                  <span className="outcome-label">Served Total</span>
                  <span className="outcome-val text-indigo-300">{outcome.served_total.toFixed(1)}</span>
                  <span className="outcome-unit">portions</span>
                  <span className="outcome-sub">Given to students</span>
                </div>

                <div className="outcome-box">
                  <span className="outcome-label">Consumed Total</span>
                  <span className="outcome-val text-cyan-300">{outcome.consumed_total.toFixed(1)}</span>
                  <span className="outcome-unit">portions</span>
                  <span className="outcome-sub">Actual food eaten (85%)</span>
                </div>

                <div className="outcome-box outcome-box--highlight">
                  <span className="outcome-label">Untouched Leftovers</span>
                  <span className="outcome-val text-amber-400">
                    {outcome.untouched_leftover.toFixed(1)}
                  </span>
                  <span className="outcome-unit">portions</span>
                  <span className="outcome-sub">Left in kitchen trays</span>
                </div>

                <div className="outcome-box outcome-box--highlight">
                  <span className="outcome-label">Plate Waste</span>
                  <span className="outcome-val text-rose-400">{outcome.plate_waste.toFixed(1)}</span>
                  <span className="outcome-unit">portions</span>
                  <span className="outcome-sub">Scrapped by diners</span>
                </div>

                <div className="outcome-box">
                  <span className="outcome-label">Shortage (Unmet)</span>
                  <span className="outcome-val text-emerald-400">{outcome.shortage.toFixed(1)}</span>
                  <span className="outcome-unit">portions</span>
                  <span className="outcome-sub">Students unserved</span>
                </div>
              </div>

              <div className="card-panel-footer mt-4">
                <span className="text-muted text-xs">
                  All metrics persisted in database <code>outcomes</code> table. Total Waste = {outcome.untouched_leftover.toFixed(1)} untouched + {outcome.plate_waste.toFixed(1)} plate waste.
                </span>
                <button
                  type="button"
                  className="btn btn--accent btn--sm"
                  onClick={() => onNavigate('evaluation')}
                >
                  View Full Evaluation &amp; Baselines
                </button>
              </div>
            </div>
          )}

          {/* Events Audit Trail Table */}
          <div className="card-panel">
            <div className="panel-header">
              <div>
                <h4 className="panel-title">Interval Simulation Events Log</h4>
                <p className="panel-subtitle">Confirmed simulation steps logged by backend</p>
              </div>
            </div>

            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Interval</th>
                    <th>Time Window</th>
                    <th>Arrivals</th>
                    <th>Stock Before</th>
                    <th>Stock After</th>
                    <th>Prepared</th>
                    <th>Served</th>
                    <th>Shortage</th>
                    <th>Action Taken</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((e) => (
                    <tr key={e.interval_index}>
                      <td>#{e.interval_index}</td>
                      <td>
                        <strong>{e.interval_start.substring(0, 5)}</strong>
                      </td>
                      <td>{e.arrivals.toFixed(1)}</td>
                      <td>{e.stock_before.toFixed(1)}</td>
                      <td className="font-semibold text-indigo-300">{e.stock_after.toFixed(1)}</td>
                      <td>{e.prepared_qty > 0 ? `+${e.prepared_qty.toFixed(0)}` : '0'}</td>
                      <td>{e.served_qty.toFixed(1)}</td>
                      <td>
                        {e.unmet_qty > 0 ? (
                          <span className="text-rose-400 font-bold">{e.unmet_qty.toFixed(1)}</span>
                        ) : (
                          '0.0'
                        )}
                      </td>
                      <td>
                        {e.action && e.action !== 'none' ? (
                          <span className="action-pill action-pill--triggered">
                            ⚡ {e.action}
                          </span>
                        ) : (
                          <span className="action-pill action-pill--none">Normal Serving</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        <div className="card-panel text-center p-6">
          <p className="text-slate-400 mb-4">No active or completed simulation run loaded.</p>
          <button type="button" className="btn btn--primary" onClick={handleStartSimulation}>
            <Play size={15} />
            <span>Launch Simulation Run</span>
          </button>
        </div>
      )}
    </div>
  );
};
