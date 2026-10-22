import React, { useCallback, useEffect, useState } from 'react';
import {
  Settings,
  Database,
  Cpu,
  Download,
  Play,
  RotateCw,
  CheckCircle,
  FileSpreadsheet,
  FileCode,
  HardDrive,
  Info,
} from 'lucide-react';
import { api, API_BASE_URL } from '../api/client';
import { MetricCard } from '../components/MetricCard';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import type { HealthResponse, MealRun, ReadinessResponse } from '../types';

export const SettingsData: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);
  const [runs, setRuns] = useState<MealRun[]>([]);
  const [selectedExportRunId, setSelectedExportRunId] = useState<string>('');

  // Generation parameters
  const [months, setMonths] = useState<number>(2);
  const [seed, setSeed] = useState<number>(42);
  const [residents, setResidents] = useState<number>(200);

  const loadStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [hRes, rRes, runsRes] = await Promise.allSettled([
        api.getHealth(),
        api.getReadiness(),
        api.listSimulationRuns({ limit: 10 }),
      ]);

      if (hRes.status === 'fulfilled') setHealth(hRes.value);
      if (rRes.status === 'fulfilled') setReadiness(rRes.value);
      if (runsRes.status === 'fulfilled') {
        setRuns(runsRes.value.items);
        if (runsRes.value.items.length > 0 && !selectedExportRunId) {
          setSelectedExportRunId(runsRes.value.items[0].id);
        }
      }
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, [selectedExportRunId]);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  const handleGenerateData = async () => {
    setActionLoading('generate');
    setActionMessage(null);
    setError(null);
    try {
      const res = await api.generateData({ months, seed, residents, validate_after: true });
      setActionMessage(
        `Generated ${res.months} months of synthetic data (Seed: ${res.seed}, Residents: ${res.residents}). Validation: ${
          res.validation.ok ? 'Passed' : 'Warnings'
        }`
      );
      await loadStatus();
    } catch (err) {
      setError(err as Error);
    } finally {
      setActionLoading(null);
    }
  };

  const handleSyncData = async () => {
    setActionLoading('sync');
    setActionMessage(null);
    setError(null);
    try {
      const res = await api.syncData();
      const counts = Object.entries(res.inserted_counts)
        .map(([k, v]) => `${k}: ${v}`)
        .join(', ');
      setActionMessage(`Synced data into database successfully. (${counts})`);
      await loadStatus();
    } catch (err) {
      setError(err as Error);
    } finally {
      setActionLoading(null);
    }
  };

  const handleSyncMenu = async () => {
    setActionLoading('menu');
    setActionMessage(null);
    setError(null);
    try {
      const res = await api.syncMenu();
      setActionMessage(`Synced vegetarian menu catalogue (${res.count} dishes).`);
      await loadStatus();
    } catch (err) {
      setError(err as Error);
    } finally {
      setActionLoading(null);
    }
  };

  const handleTrainModel = async () => {
    setActionLoading('train');
    setActionMessage(null);
    setError(null);
    try {
      const res = await api.trainModel();
      setActionMessage(
        `Demand model trained (${res.model_version})! Test MAE: ${res.metrics.mae.toFixed(2)}, RMSE: ${res.metrics.rmse.toFixed(2)}, R²: ${res.metrics.r2.toFixed(3)} across ${res.metrics.n_samples} samples.`
      );
      await loadStatus();
    } catch (err) {
      setError(err as Error);
    } finally {
      setActionLoading(null);
    }
  };

  if (loading && !health) {
    return <LoadingState message="Checking system environment and backend services..." />;
  }

  return (
    <div className="page-container">
      <div className="page-header-row">
        <div>
          <h2 className="page-title">System Settings &amp; Data Pipeline Management</h2>
          <p className="page-desc">
            Configuration parameters, synthetic dataset seeding, machine learning model retraining, and export endpoints.
          </p>
        </div>

        <div className="header-action-group">
          <button type="button" className="btn btn--secondary" onClick={loadStatus}>
            <RotateCw size={15} />
            <span>Refresh Status</span>
          </button>
        </div>
      </div>

      {actionMessage && (
        <div className="action-success-banner">
          <CheckCircle size={18} className="text-emerald-400" />
          <span>{actionMessage}</span>
        </div>
      )}

      {error && <ErrorState error={error} onRetry={loadStatus} />}

      {/* System Status Metrics */}
      <div className="metric-cards-grid">
        <MetricCard
          title="Backend API Status"
          value={health?.status === 'ok' ? 'Healthy' : 'Degraded'}
          unit={health?.version || '1.0.0'}
          variant={health?.status === 'ok' ? 'success' : 'danger'}
          subtitle={`FastAPI Base: ${API_BASE_URL}`}
          icon={<Cpu size={20} className="text-indigo-400" />}
        />

        <MetricCard
          title="Database Connection"
          value={readiness?.database === 'ok' ? 'Connected' : 'Checking'}
          unit={readiness?.migrations || 'SQLite/Postgres'}
          subtitle="Alembic Migrations Head"
          icon={<Database size={20} className="text-cyan-400" />}
          denominatorNote="Managed by SQLAlchemy / Alembic migration 2d8896a08ce2"
        />

        <MetricCard
          title="Model Artifact Status"
          value={readiness?.model_artifact ? 'Ready' : 'Trained'}
          unit="context-rf-v4"
          variant={readiness?.model_artifact ? 'success' : 'warning'}
          subtitle="ml/artifacts/context_model.joblib"
          icon={<HardDrive size={20} className="text-amber-400" />}
        />

        <MetricCard
          title="Execution Environment"
          value={health?.environment ?? 'local'}
          unit="synthetic-only"
          subtitle="Strict synthetic simulation guardrails"
          icon={<Settings size={20} className="text-emerald-400" />}
        />
      </div>

      {/* Action Controls Grid */}
      <div className="overview-two-col-grid">
        {/* Synthetic Data Generator */}
        <div className="card-panel">
          <div className="panel-header">
            <div>
              <h4 className="panel-title">Synthetic Data Generation (Person A Pipeline)</h4>
              <p className="panel-subtitle">
                Generate student occupancy, mess timetable, and weather records
              </p>
            </div>
            <Database size={18} className="text-indigo-400" />
          </div>

          <div className="form-grid-three">
            <div className="form-group">
              <label>Duration (Months):</label>
              <input
                type="number"
                className="form-input"
                value={months}
                onChange={(e) => setMonths(Number(e.target.value))}
                min={1}
                max={12}
              />
            </div>

            <div className="form-group">
              <label>Random Seed:</label>
              <input
                type="number"
                className="form-input"
                value={seed}
                onChange={(e) => setSeed(Number(e.target.value))}
              />
            </div>

            <div className="form-group">
              <label>Resident Cohort:</label>
              <input
                type="number"
                className="form-input"
                value={residents}
                onChange={(e) => setResidents(Number(e.target.value))}
                min={50}
                max={1000}
              />
            </div>
          </div>

          <div className="btn-group-actions mt-4">
            <button
              type="button"
              className="btn btn--primary"
              onClick={handleGenerateData}
              disabled={actionLoading !== null}
            >
              <Play size={14} />
              <span>{actionLoading === 'generate' ? 'Generating Records...' : 'Generate Synthetic Data'}</span>
            </button>

            <button
              type="button"
              className="btn btn--secondary"
              onClick={handleSyncData}
              disabled={actionLoading !== null}
            >
              <span>{actionLoading === 'sync' ? 'Syncing...' : 'Sync Data into DB'}</span>
            </button>

            <button
              type="button"
              className="btn btn--secondary"
              onClick={handleSyncMenu}
              disabled={actionLoading !== null}
            >
              <span>{actionLoading === 'menu' ? 'Syncing...' : 'Sync Menu Catalogue'}</span>
            </button>
          </div>
        </div>

        {/* Model Training & Inference Engine */}
        <div className="card-panel">
          <div className="panel-header">
            <div>
              <h4 className="panel-title">Demand Model Training (Person A ML Pipeline)</h4>
              <p className="panel-subtitle">
                Train Random Forest regressor with chronological train/test split
              </p>
            </div>
            <Cpu size={18} className="text-cyan-400" />
          </div>

          <div className="info-box-note mb-4">
            <Info size={16} className="text-indigo-400 shrink-0" />
            <p className="text-xs text-slate-300">
              Features include day-of-week, weather rainfall &amp; temperature, hostel occupancy,
              exam overlap, and dish category popularity. Residual quantiles (10th/90th) are saved
              into the artifact for uncertainty intervals.
            </p>
          </div>

          <button
            type="button"
            className="btn btn--accent btn--full"
            onClick={handleTrainModel}
            disabled={actionLoading !== null}
          >
            <Play size={15} />
            <span>{actionLoading === 'train' ? 'Training Random Forest...' : 'Train Demand Model Artifact'}</span>
          </button>
        </div>
      </div>

      {/* Data Export Center */}
      <div className="card-panel">
        <div className="panel-header">
          <div>
            <h4 className="panel-title">Auditable Data Export Center</h4>
            <p className="panel-subtitle">
              Export simulation runs and multi-stage agent traces in standardized JSON and CSV formats
            </p>
          </div>
          <FileSpreadsheet size={20} className="text-emerald-400" />
        </div>

        <div className="export-controls-grid">
          <div className="export-col">
            <span className="export-label">Export Simulation Run:</span>
            <select
              className="select-meal w-full"
              value={selectedExportRunId}
              onChange={(e) => setSelectedExportRunId(e.target.value)}
            >
              {runs.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.id.substring(0, 8)}... ({r.service_date} {r.meal_type} • {r.policy_id})
                </option>
              ))}
            </select>

            <div className="export-buttons-row mt-3">
              <a
                href={api.getRunExportJsonUrl(selectedExportRunId || (runs[0]?.id ?? ''))}
                className="btn btn--secondary btn--sm"
                target="_blank"
                rel="noopener noreferrer"
              >
                <FileCode size={14} />
                <span>Download Run JSON</span>
              </a>

              <a
                href={api.getRunExportCsvUrl(selectedExportRunId || (runs[0]?.id ?? ''))}
                className="btn btn--secondary btn--sm"
                target="_blank"
                rel="noopener noreferrer"
              >
                <FileSpreadsheet size={14} />
                <span>Download Run CSV</span>
              </a>
            </div>
          </div>

          <div className="export-col">
            <span className="export-label">Export Agent Audit Traces:</span>
            <p className="text-xs text-slate-400 mb-3">
              Downloads complete chronological records of every specialized agent stage, duration,
              and tool call payload.
            </p>
            <a
              href={api.getTraceExportCsvUrl()}
              className="btn btn--primary btn--sm"
              target="_blank"
              rel="noopener noreferrer"
            >
              <Download size={14} />
              <span>Export All Agent Traces (CSV)</span>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};
