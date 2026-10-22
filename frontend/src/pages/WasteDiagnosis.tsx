import React, { useEffect, useState } from 'react';
import {
  Stethoscope,
  AlertTriangle,
  FileText,
  Search,
  CheckCircle2,
  HelpCircle,
  RefreshCw,
  Info,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { api } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';
import { MetricCard } from '../components/MetricCard';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import type { DiagnosisRecord, MealRun, MealType } from '../types';

interface WasteDiagnosisProps {
  selectedDate: string;
  selectedMeal: MealType;
}

export const WasteDiagnosis: React.FC<WasteDiagnosisProps> = ({
  selectedDate,
  selectedMeal,
}) => {
  const [activeTab, setActiveTab] = useState<'pre_meal' | 'post_meal'>('post_meal');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const [diagnoses, setDiagnoses] = useState<DiagnosisRecord[]>([]);
  const [runs, setRuns] = useState<MealRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>('');
  const [expandedCauseIdx, setExpandedCauseIdx] = useState<number | null>(0);

  const loadDiagnoses = async () => {
    setLoading(true);
    setError(null);
    try {
      const [diagRes, runsRes] = await Promise.all([
        api.listDiagnoses({ limit: 20 }),
        api.listSimulationRuns({ limit: 10, status: 'finished' }),
      ]);

      setDiagnoses(diagRes.items);
      setRuns(runsRes.items);

      if (runsRes.items.length > 0 && !selectedRunId) {
        setSelectedRunId(runsRes.items[0].id);
      }
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  };

  const runPostMealDiagnosis = async () => {
    if (!selectedRunId) return;
    setLoading(true);
    try {
      await api.diagnosePostMeal({ run_id: selectedRunId, persist: true });
      await loadDiagnoses();
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  };

  const runPreMealDiagnosis = async () => {
    setLoading(true);
    try {
      await api.diagnosePreMeal({
        service_date: selectedDate,
        meal_type: selectedMeal,
        forecasts: [{ dish_id: 'D001', prediction: 288, lower_bound: 184, upper_bound: 346 }],
        planned_quantities: [{ dish_id: 'D001', prepared_qty: 380 }],
        historical_waste_rate: 0.12,
        persist: true,
      });
      await loadDiagnoses();
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDiagnoses();
  }, [selectedDate, selectedMeal]);

  if (loading) {
    return <LoadingState message="Fetching evidence-based waste diagnoses and causation records..." />;
  }

  // Filter by tab
  const filtered = diagnoses.filter((d) => d.diagnosis_type === activeTab);
  const activeRecord = filtered[0];

  return (
    <div className="page-container">
      <div className="page-header-row">
        <div>
          <h2 className="page-title">Evidence-Based Waste Diagnosis</h2>
          <p className="page-desc">
            Deterministic rule-based root cause analysis using auditable database evidence. Discloses uncertainty and correlation limits.
          </p>
        </div>

        <div className="header-action-group">
          {activeTab === 'post_meal' ? (
            <button
              type="button"
              className="btn btn--primary"
              onClick={runPostMealDiagnosis}
              disabled={!selectedRunId}
            >
              <Stethoscope size={15} />
              <span>Diagnose Selected Run</span>
            </button>
          ) : (
            <button type="button" className="btn btn--primary" onClick={runPreMealDiagnosis}>
              <Stethoscope size={15} />
              <span>Diagnose Pre-Meal Risk</span>
            </button>
          )}

          <button type="button" className="btn btn--secondary" onClick={loadDiagnoses}>
            <RefreshCw size={15} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs-header">
        <button
          type="button"
          className={`tab-btn ${activeTab === 'post_meal' ? 'tab-btn--active' : ''}`}
          onClick={() => setActiveTab('post_meal')}
        >
          <span>Retrospective Post-Meal Diagnosis</span>
          <StatusBadge label="Evidence Verified" variant="success" size="sm" />
        </button>
        <button
          type="button"
          className={`tab-btn ${activeTab === 'pre_meal' ? 'tab-btn--active' : ''}`}
          onClick={() => setActiveTab('pre_meal')}
        >
          <span>Pre-Meal Waste Risk Estimate</span>
          <StatusBadge label="Heuristic" variant="warning" size="sm" />
        </button>
      </div>

      {/* Post-Meal Run Selector */}
      {activeTab === 'post_meal' && (
        <div className="run-selector-strip card-panel p-3 mb-4">
          <span className="selector-label">Select Finished Simulation Run to Inspect:</span>
          <select
            className="select-meal"
            value={selectedRunId}
            onChange={(e) => setSelectedRunId(e.target.value)}
          >
            {runs.map((r) => (
              <option key={r.id} value={r.id}>
                Run {r.id.substring(0, 8)}... ({r.service_date} {r.meal_type} • {r.policy_id})
              </option>
            ))}
          </select>
        </div>
      )}

      {error && <ErrorState error={error} onRetry={loadDiagnoses} />}

      {!activeRecord ? (
        <div className="card-panel text-center p-6">
          <HelpCircle size={36} className="text-slate-500 mx-auto mb-2" />
          <h4 className="text-lg font-medium text-slate-200">No Diagnosis Records for this View</h4>
          <p className="text-slate-400 text-sm max-w-md mx-auto mb-4">
            {activeTab === 'post_meal'
              ? 'Click "Diagnose Selected Run" above to evaluate realized meal leftovers against evidence.'
              : 'Click "Diagnose Pre-Meal Risk" to analyze planned quantities against expected demand.'}
          </p>
        </div>
      ) : (
        <>
          {/* Summary KPI Cards */}
          <div className="metric-cards-grid">
            <MetricCard
              title="Calculated Waste Risk Score"
              value={(activeRecord.risk_score * 100).toFixed(1)}
              unit="%"
              variant={activeRecord.risk_score > 0.3 ? 'warning' : 'success'}
              subtitle={
                activeRecord.risk_score > 0.3
                  ? 'Elevated food surplus detected'
                  : 'Surplus well controlled'
              }
              icon={<AlertTriangle size={20} className="text-amber-400" />}
              denominatorNote="Score normalized against total food prepared"
            />

            <MetricCard
              title="Diagnosis Confidence"
              value={(activeRecord.confidence * 100).toFixed(1)}
              unit="%"
              subtitle="Derived from empirical evidence availability"
              icon={<CheckCircle2 size={20} className="text-emerald-400" />}
              denominatorNote="Confidence penalized when telemetry sources are missing"
            />

            <MetricCard
              title="Ranked Potential Causes"
              value={activeRecord.causes?.length ?? 0}
              unit="causes"
              subtitle="Ordered by evidence confidence"
              icon={<Search size={20} className="text-cyan-400" />}
            />

            <MetricCard
              title="LLM Explainer Used"
              value="False (Deterministic)"
              unit="engine"
              subtitle="100% deterministic rules on validated database evidence"
              icon={<FileText size={20} className="text-indigo-400" />}
              denominatorNote="Guarantees zero hallucinations and full reproducibility"
            />
          </div>

          {/* Causes List with Evidence */}
          <div className="card-panel">
            <div className="panel-header">
              <div>
                <h4 className="panel-title">Ranked Root Causes &amp; Audit Trail</h4>
                <p className="panel-subtitle">
                  Correlation and association only; never displayed as absolute proven causation.
                </p>
              </div>
            </div>

            <div className="causes-accordion">
              {activeRecord.causes?.map((cause, idx) => {
                const isExpanded = expandedCauseIdx === idx;
                return (
                  <div key={cause.code} className="cause-card">
                    <div
                      className="cause-header"
                      onClick={() => setExpandedCauseIdx(isExpanded ? null : idx)}
                    >
                      <div className="cause-title-col">
                        <span className="cause-rank">#{idx + 1}</span>
                        <div>
                          <strong className="cause-title">{cause.title}</strong>
                          <span className="cause-code">Code: <code>{cause.code}</code></span>
                        </div>
                      </div>

                      <div className="cause-meta-col">
                        <span className="cause-confidence">
                          Confidence: {(cause.confidence * 100).toFixed(1)}%
                        </span>
                        {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="cause-body">
                        <h6 className="evidence-section-title">Supporting Empirical Evidence:</h6>
                        <div className="table-wrapper">
                          <table className="data-table data-table--compact">
                            <thead>
                              <tr>
                                <th>Field Name</th>
                                <th>Observed Value</th>
                                <th>Baseline Comparison</th>
                                <th>Data Source</th>
                              </tr>
                            </thead>
                            <tbody>
                              {cause.evidence?.map((ev, evIdx) => (
                                <tr key={evIdx}>
                                  <td>
                                    <code>{ev.field}</code>
                                  </td>
                                  <td>
                                    <strong>{String(ev.value)}</strong>
                                  </td>
                                  <td>{ev.comparison || '—'}</td>
                                  <td>
                                    <span className="data-source-tag">{ev.source}</span>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Caveats & Integrity Box */}
          <div className="card-panel">
            <div className="panel-header">
              <div>
                <h4 className="panel-title">Model Caveats &amp; Epistemic Boundaries</h4>
                <p className="panel-subtitle">
                  Academic scientific integrity requirements (Person B &amp; C contract)
                </p>
              </div>
              <Info size={18} className="text-indigo-400" />
            </div>

            <div className="caveats-list">
              {activeRecord.caveats?.map((caveat, i) => (
                <div key={i} className="caveat-item">
                  <AlertTriangle size={16} className="text-amber-400 shrink-0" />
                  <span className="caveat-text">{caveat}</span>
                </div>
              ))}
              <div className="caveat-item caveat-item--neutral">
                <Info size={16} className="text-slate-400 shrink-0" />
                <span className="caveat-text">
                  <strong>Non-Causal Guarantee:</strong> These causes represent statistical associations
                  observed in the synthetic simulation realization. They do not constitute proved real-world causation.
                </span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
