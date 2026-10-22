import React, { useCallback, useEffect, useState } from 'react';
import {
  Clock,
  Play,
  RotateCw,
  Terminal,
  ChevronDown,
  ChevronUp,
  Download,
} from 'lucide-react';
import { api } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import type { AgentTraceItem, MealType, PlanningWorkflowResponse } from '../types';

interface AgentTraceProps {
  selectedDate: string;
  selectedMeal: MealType;
}

const mealWindows: Record<MealType, { start: string; close: string }> = {
  breakfast: { start: '07:00', close: '09:30' },
  lunch: { start: '12:00', close: '14:00' },
  snacks: { start: '16:30', close: '18:15' },
  dinner: { start: '19:00', close: '21:00' },
};

export const AgentTrace: React.FC<AgentTraceProps> = ({
  selectedDate,
  selectedMeal,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const [traceId, setTraceId] = useState<string>('');
  const [traces, setTraces] = useState<AgentTraceItem[]>([]);
  const [expandedTraceId, setExpandedTraceId] = useState<string | null>(null);
  const [runningAgent, setRunningAgent] = useState(false);

  const loadTraces = useCallback(async (targetTraceId?: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getAgentTraces({
        trace_id: targetTraceId || traceId || undefined,
        limit: 50,
      });
      const items = res.items as AgentTraceItem[];
      setTraces(items);

      if (items.length > 0 && !targetTraceId && !traceId) {
        setTraceId(items[0].trace_id);
      }
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, [traceId]);

  const runNewPlanningWorkflow = async () => {
    setRunningAgent(true);
    setError(null);
    const window = mealWindows[selectedMeal] || { start: '07:00', close: '10:00' };
    try {
      const res: PlanningWorkflowResponse = await api.runPlanningAgent({
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
        service_start: window.start,
        service_close: window.close,
        persist: true,
      });

      setTraceId(res.trace_id);
      await loadTraces(res.trace_id);
    } catch (err) {
      setError(err as Error);
    } finally {
      setRunningAgent(false);
    }
  };

  useEffect(() => {
    loadTraces();
  }, [loadTraces, selectedDate, selectedMeal]);

  if (loading && traces.length === 0) {
    return <LoadingState message="Fetching agent stage execution logs and tool call traces..." />;
  }

  const stagesInOrder = [
    { key: 'context_observation', name: 'Context Observer', desc: 'Hostel state & weather data fetch' },
    { key: 'availability_estimate', name: 'Availability Estimator', desc: 'Timetable conflict & diner calculation' },
    { key: 'demand_forecast', name: 'Demand Forecaster', desc: 'Random forest batch prediction inference' },
    { key: 'constrained_planning', name: 'Kitchen Planner', desc: 'Constrained split-batch optimizer' },
    { key: 'pre_meal_diagnosis', name: 'Pre-Meal Diagnostician', desc: 'Waste risk & heuristic check' },
    { key: 'post_meal_diagnosis', name: 'Post-Meal Diagnostician', desc: 'Retrospective outcome diagnosis' },
    { key: 'outcome_learning', name: 'Outcome Learner', desc: 'Candidate model retraining feedback' },
  ];

  return (
    <div className="page-container">
      <div className="page-header-row">
        <div>
          <h2 className="page-title">Autonomous Agent Trace &amp; Audit Log</h2>
          <p className="page-desc">
            Granular pipeline traces for each specialized agent module with typed contract validation and execution timing.
          </p>
        </div>

        <div className="header-action-group">
          <a
            href={api.getTraceExportCsvUrl(traceId)}
            className="btn btn--secondary"
            target="_blank"
            rel="noopener noreferrer"
            title="Download trace CSV"
          >
            <Download size={15} />
            <span>Export Trace CSV</span>
          </a>

          <button
            type="button"
            className="btn btn--primary"
            onClick={runNewPlanningWorkflow}
            disabled={runningAgent}
          >
            <Play size={15} />
            <span>{runningAgent ? 'Orchestrating...' : 'Trigger Agent Workflow'}</span>
          </button>

          <button type="button" className="btn btn--secondary" onClick={() => loadTraces(traceId)}>
            <RotateCw size={15} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {error && <ErrorState error={error} onRetry={() => loadTraces(traceId)} />}

      {/* Trace Search / Selector */}
      <div className="card-panel simulation-controls-strip mb-4">
        <div className="controls-left">
          <span className="control-label">Trace ID:</span>
          <input
            type="text"
            className="form-input form-input--lg"
            placeholder="Filter by Trace UUID..."
            value={traceId}
            onChange={(e) => setTraceId(e.target.value)}
          />
        </div>

        <div className="controls-right">
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            onClick={() => loadTraces(traceId)}
          >
            Filter Trace
          </button>
        </div>
      </div>

      {/* Visual Pipeline Stepper */}
      <div className="card-panel">
        <div className="panel-header">
          <div>
            <h4 className="panel-title">Multi-Agent Workflow Execution Pipeline</h4>
            <p className="panel-subtitle">Sequential stage validation and typed contract enforcement</p>
          </div>
          <StatusBadge label="Deterministic Contracts" variant="purple" />
        </div>

        <div className="agent-pipeline-track">
          {stagesInOrder.map((stageInfo, idx) => {
            const recorded = traces.find((t) => t.stage === stageInfo.key);
            const isCompleted = recorded && recorded.status === 'completed';
            const isFailed = recorded && (recorded.status === 'failed' || recorded.status === 'rejected');

            return (
              <div
                key={stageInfo.key}
                className={`agent-pipeline-node ${
                  isCompleted
                    ? 'node--completed'
                    : isFailed
                    ? 'node--failed'
                    : 'node--pending'
                }`}
              >
                <div className="node-number">{idx + 1}</div>
                <div className="node-label-group">
                  <span className="node-title">{stageInfo.name}</span>
                  <span className="node-stage-code"><code>{stageInfo.key}</code></span>
                  {recorded && (
                    <span className="node-duration text-xs text-indigo-300">
                      {recorded.duration_ms.toFixed(1)} ms
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Traces List Table / Accordion */}
      <div className="card-panel">
        <div className="panel-header">
          <div>
            <h4 className="panel-title">Stage Payload &amp; Tool Invocations</h4>
            <p className="panel-subtitle">Expand any stage to inspect validated input/output payloads</p>
          </div>
          <span className="text-muted text-xs">Total Stages: {traces.length}</span>
        </div>

        {traces.length === 0 ? (
          <div className="panel-empty-text">
            No agent traces found. Click "Trigger Agent Workflow" to run the master orchestrator.
          </div>
        ) : (
          <div className="agent-traces-list">
            {traces.map((trace) => {
              const isExpanded = expandedTraceId === trace.id;

              return (
                <div key={trace.id} className="agent-trace-row-card">
                  <div
                    className="agent-trace-header"
                    onClick={() => setExpandedTraceId(isExpanded ? null : trace.id)}
                  >
                    <div className="trace-info-left">
                      <Terminal size={18} className="text-indigo-400" />
                      <div>
                        <strong className="trace-stage-name">{trace.stage}</strong>
                        <span className="trace-agent-tag">Agent: {trace.agent_name}</span>
                      </div>
                    </div>

                    <div className="trace-info-right">
                      <span className="trace-timing">
                        <Clock size={13} />
                        <span>{trace.duration_ms.toFixed(2)} ms</span>
                      </span>

                      <StatusBadge
                        label={trace.status}
                        variant={trace.status === 'completed' ? 'success' : 'danger'}
                        size="sm"
                      />

                      {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="agent-trace-body">
                      <div className="trace-json-grid">
                        <div className="trace-json-box">
                          <span className="json-box-title">Input Summary</span>
                          <pre className="trace-pre">
                            {JSON.stringify(trace.input_summary, null, 2)}
                          </pre>
                        </div>

                        <div className="trace-json-box">
                          <span className="json-box-title">Output Summary</span>
                          <pre className="trace-pre">
                            {JSON.stringify(trace.output_summary, null, 2)}
                          </pre>
                        </div>
                      </div>

                      {trace.error && (
                        <div className="trace-error-box mt-3">
                          <strong>Error:</strong> {trace.error}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
