/**
 * Centralized API client with request timeout, typed error handling,
 * and base URL configuration.
 */

import type {
  ApiErrorPayload,
  AvailabilityRequest,
  AvailabilityResponse,
  DataGenerateResponse,
  DataSyncResponse,
  DiagnosisRecord,
  Dish,
  EvaluationComparison,
  EvaluationMetrics,
  ForecastResponse,
  HealthResponse,
  MealRun,
  MealType,
  ModelTrainResponse,
  PlanningWorkflowResponse,
  PlanRequest,
  PlanResponse,
  ReadinessResponse,
  SimulationCompareResponse,
  SimulationEvent,
  SyntheticContext,
} from '../types';
import type {
  MessWiseWeather,
  FoodPreferenceResult,
  DemandForecastResult,
  WasteDiagnosisResult,
  KitchenPlanResult,
  SmartSuggestion,
  ChatResponse,
  MealOutcomeRecord,
  PerformanceEvaluation,
  MessWiseContext,
} from '../types/messwise';

export const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ||
  'http://localhost:8000';

export class ApiError extends Error {
  code: string;
  statusCode: number;
  details?: unknown;
  requestId?: string | null;

  constructor(code: string, message: string, statusCode: number, details?: unknown, requestId?: string | null) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.statusCode = statusCode;
    this.details = details;
    this.requestId = requestId;
  }
}

async function request<T>(path: string, options: RequestInit = {}, timeoutMs = 15000): Promise<T> {
  const url = `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const headers = new Headers(options.headers || {});
  if (!headers.has('Content-Type') && options.body && typeof options.body === 'string') {
    headers.set('Content-Type', 'application/json');
  }
  if (!headers.has('X-Request-ID')) {
    headers.set('X-Request-ID', `req_${Math.random().toString(36).substring(2, 10)}`);
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });

    const isJson = response.headers.get('content-type')?.includes('application/json');
    const data = isJson ? await response.json() : await response.text();

    if (!response.ok) {
      if (typeof data === 'object' && data !== null && 'error' in data) {
        const payload = data as ApiErrorPayload;
        throw new ApiError(
          payload.error.code || 'API_ERROR',
          payload.error.message || response.statusText,
          response.status,
          payload.error.details,
          payload.error.request_id || response.headers.get('x-request-id')
        );
      }
      throw new ApiError(
        `HTTP_${response.status}`,
        typeof data === 'string' ? data : response.statusText,
        response.status,
        data,
        response.headers.get('x-request-id')
      );
    }

    return data as T;
  } catch (err: unknown) {
    if (err instanceof ApiError) {
      throw err;
    }
    if (err instanceof Error && err.name === 'AbortError') {
      throw new ApiError('TIMEOUT_ERROR', `Request to ${path} timed out after ${timeoutMs}ms`, 408);
    }
    throw new ApiError(
      'NETWORK_ERROR',
      err instanceof Error ? err.message : 'Network request failed. Is backend running?',
      0
    );
  } finally {
    clearTimeout(timeoutId);
  }
}

// Health & System
export const api = {
  getHealth: () => request<HealthResponse>('/health'),
  getReadiness: () => request<ReadinessResponse>('/ready'),

  // Data & Model
  generateData: (payload: { months?: number; seed?: number; residents?: number; validate_after?: boolean } = {}) =>
    request<DataGenerateResponse>('/api/v1/data/generate', {
      method: 'POST',
      body: JSON.stringify({
        months: payload.months ?? 2,
        seed: payload.seed ?? 42,
        residents: payload.residents ?? 200,
        validate_after: payload.validate_after ?? true,
      }),
    }),
  syncData: () => request<DataSyncResponse>('/api/v1/data/sync', { method: 'POST' }),
  syncMenu: () => request<{ ok: boolean; count: number }>('/api/v1/menu/sync', { method: 'POST' }),
  trainModel: () => request<ModelTrainResponse>('/api/v1/forecasts/model/train', { method: 'POST' }),

  // Menu catalogue
  getMenu: (params?: { meal_type?: MealType; active_only?: boolean }) => {
    const q = new URLSearchParams();
    if (params?.meal_type) q.append('meal_type', params.meal_type);
    if (params?.active_only !== undefined) q.append('active_only', String(params.active_only));
    return request<{ items: Dish[]; total: number }>(`/api/v1/menu?${q.toString()}`);
  },

  // Context & Availability
  getContext: (params?: { date?: string; hostel_id?: string; mess_id?: string }) => {
    const q = new URLSearchParams();
    if (params?.date) q.append('date', params.date);
    if (params?.hostel_id) q.append('hostel_id', params.hostel_id);
    if (params?.mess_id) q.append('mess_id', params.mess_id);
    return request<SyntheticContext>(`/api/v1/context?${q.toString()}`);
  },
  calculateAvailability: (payload: AvailabilityRequest) =>
    request<AvailabilityResponse>('/api/v1/context/availability', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Forecasts
  getForecasts: (payload: { date: string; meal_type: MealType; persist?: boolean }) =>
    request<ForecastResponse>('/api/v1/forecasts', {
      method: 'POST',
      body: JSON.stringify({
        date: payload.date,
        meal_type: payload.meal_type,
        persist: payload.persist ?? true,
      }),
    }),

  // Plans & Optimization
  createPlan: (payload: PlanRequest) =>
    request<PlanResponse>('/api/v1/plans', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Simulations
  startSimulation: (payload: {
    scenario_id?: string;
    dataset_version?: string;
    service_date: string;
    meal_type: MealType;
    dish_external_id?: string;
    policy: 'baseline_fixed' | 'context_aware_split';
    seed?: number;
    use_historical?: boolean;
    historical_date?: string;
    plan?: { initial_qty: number; reserve_qty: number; trigger_qty: number };
    prep_lead_intervals?: number;
    consumption_rate?: number;
    capacity?: number;
    forecast_expected?: number;
    forecast_run_id?: string;
    model_version?: string;
    persist?: boolean;
  }) =>
    request<MealRun>('/api/v1/simulations', {
      method: 'POST',
      body: JSON.stringify({
        ...payload,
        policy: payload.policy || 'context_aware_split',
        use_historical: payload.use_historical ?? true,
        historical_date: payload.historical_date ?? '2026-08-31',
        persist: true,
      }),
    }),

  stepSimulation: (runId: string) =>
    request<{ run: MealRun; event: SimulationEvent; finished: boolean }>(`/api/v1/simulations/${runId}/step`, {
      method: 'POST',
    }),

  finishSimulation: (runId: string) =>
    request<{ run: MealRun; outcome: unknown; events: SimulationEvent[] }>(`/api/v1/simulations/${runId}/finish`, {
      method: 'POST',
    }),

  compareSimulations: (payload: {
    scenario_id?: string;
    dataset_version?: string;
    service_date: string;
    meal_type: MealType;
    dish_external_id: string;
    seed?: number;
    service_start?: string;
    use_historical?: boolean;
    historical_date?: string;
    current_stock?: number;
    capacity?: number;
    batch_min?: number;
    batch_max?: number;
    consumption_rate?: number;
    prep_lead_intervals?: number;
    forecast_expected: number;
    forecast_run_id?: string;
    model_version?: string;
    persist?: boolean;
  }) =>
    request<SimulationCompareResponse>('/api/v1/simulations/compare', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  listSimulationRuns: (params?: { limit?: number; offset?: number; status?: string }) => {
    const q = new URLSearchParams();
    if (params?.limit) q.append('limit', String(params.limit));
    if (params?.offset) q.append('offset', String(params.offset));
    if (params?.status) q.append('status', params.status);
    return request<{ items: MealRun[]; total: number }>(`/api/v1/simulations?${q.toString()}`);
  },

  getSimulationRun: (runId: string) =>
    request<{ run: MealRun; events: SimulationEvent[]; outcome: unknown }>(`/api/v1/simulations/${runId}`),

  // Waste Diagnosis
  diagnosePreMeal: (payload: {
    service_date: string;
    meal_type: MealType;
    forecasts: Array<{ dish_id: string; prediction: number; lower_bound: number; upper_bound: number }>;
    planned_quantities: Array<{ dish_id: string; prepared_qty: number }>;
    historical_waste_rate?: number;
    persist?: boolean;
  }) =>
    request<DiagnosisRecord>('/api/v1/diagnoses/pre-meal', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  diagnosePostMeal: (payload: { run_id: string; persist?: boolean }) =>
    request<DiagnosisRecord>('/api/v1/diagnoses/post-meal', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  listDiagnoses: (params?: { diagnosis_type?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.diagnosis_type) q.append('diagnosis_type', params.diagnosis_type);
    if (params?.limit) q.append('limit', String(params.limit));
    return request<{ items: DiagnosisRecord[]; total: number }>(`/api/v1/diagnoses?${q.toString()}`);
  },

  // Evaluation
  evaluateRun: (runId: string) =>
    request<{ run_id: string; metrics: EvaluationMetrics }>(`/api/v1/evaluation/runs/${runId}`, {
      method: 'POST',
    }),

  compareEvaluation: (payload: { baseline_run_id: string; context_run_id: string; persist?: boolean }) =>
    request<EvaluationComparison>('/api/v1/evaluation/compare', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Agents
  runPlanningAgent: (payload: {
    service_date: string;
    meal_type: MealType;
    hostel_id?: string;
    mess_id?: string;
    attendance_probability?: number;
    current_stock?: number;
    batch_min?: number;
    batch_max?: number;
    kitchen_capacity?: number;
    prep_lead_minutes?: number;
    service_start?: string;
    service_close?: string;
    persist?: boolean;
  }) =>
    request<PlanningWorkflowResponse>('/api/v1/agents/planning', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  runReviewAgent: (payload: { run_id: string; persist?: boolean }) =>
    request<{ trace_id: string; run_id: string; status: string; stages: unknown[] }>('/api/v1/agents/review', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getAgentTraces: (params?: { trace_id?: string; run_id?: string; limit?: number; offset?: number }) => {
    const q = new URLSearchParams();
    if (params?.trace_id) q.append('trace_id', params.trace_id);
    if (params?.run_id) q.append('run_id', params.run_id);
    if (params?.limit) q.append('limit', String(params.limit));
    if (params?.offset) q.append('offset', String(params.offset));
    return request<{ items: unknown[]; total: number }>(`/api/v1/agents/traces?${q.toString()}`);
  },

  // Exports URLs
  getRunExportJsonUrl: (runId: string) => `${API_BASE_URL}/api/v1/exports/runs/${runId}?format=json`,
  getRunExportCsvUrl: (runId: string) => `${API_BASE_URL}/api/v1/exports/runs/${runId}?format=csv`,
  getTraceExportCsvUrl: (traceId?: string) =>
    `${API_BASE_URL}/api/v1/exports/agent-traces?format=csv${traceId ? `&trace_id=${traceId}` : ''}`,

  // MessWise Five Agents & Kitchen Operations Endpoints
  getMessWiseHealth: () => request<Record<string, any>>('/api/health'),

  getMessWiseMenu: (date?: string, meal?: string) => {
    const q = new URLSearchParams();
    if (date) q.append('date', date);
    if (meal) q.append('meal', meal);
    return request<{ dates: string[]; meals: string[]; selected_date: string; selected_meal: string; dishes: string[]; count: number }>(`/api/menu?${q.toString()}`);
  },

  getMessWiseContext: (date: string, meal: string, foodItem: string, demoWeather?: string) => {
    const q = new URLSearchParams({ date, meal, food_item: foodItem });
    if (demoWeather) q.append('demo_weather', demoWeather);
    return request<MessWiseContext>(`/api/context?${q.toString()}`);
  },

  getMessWiseWeather: (date: string, meal: string, demoMode?: string) => {
    const q = new URLSearchParams({ date, meal });
    if (demoMode) q.append('demo_mode', demoMode);
    return request<MessWiseWeather>(`/api/weather?${q.toString()}`);
  },

  getMessWisePreference: (foodItem: string, meal?: string) => {
    const q = new URLSearchParams({ food_item: foodItem });
    if (meal) q.append('meal', meal);
    return request<FoodPreferenceResult>(`/api/preference?${q.toString()}`);
  },

  predictMessWiseDemand: (payload: {
    food_item: string;
    date: string;
    meal: string;
    attendance?: number;
    exam_intensity?: number;
    temperature_c?: number;
    rainfall_mm?: number;
    preference_score?: number;
  }) =>
    request<DemandForecastResult>('/api/predict-demand', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  analyzeMessWiseWaste: (payload: {
    food_item: string;
    meal?: string;
    date?: string;
    prepared_portions?: number;
    consumed_portions?: number;
    leftover_portions?: number;
  }) =>
    request<WasteDiagnosisResult>('/api/analyze-waste', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getMessWiseKitchenPlan: (payload: {
    food_item: string;
    predicted_demand: number;
    meal?: string;
    risk_level?: string;
    kitchen_capacity?: number;
  }) =>
    request<KitchenPlanResult>('/api/kitchen-plan', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getMessWiseSuggestions: (foodItem: string, meal: string, date: string, attendance?: number, demoWeather?: string) => {
    const q = new URLSearchParams({ food_item: foodItem, meal, date });
    if (attendance) q.append('attendance', String(attendance));
    if (demoWeather) q.append('demo_weather', demoWeather);
    return request<SmartSuggestion[]>(`/api/suggestions?${q.toString()}`);
  },

  actionMessWiseSuggestion: (suggestionId: string, action: 'dismiss' | 'complete') =>
    request<{ status: string; suggestion_id: string; action: string }>('/api/suggestions/action', {
      method: 'POST',
      body: JSON.stringify({ suggestion_id: suggestionId, action }),
    }),

  sendMessWiseChat: (payload: {
    message: string;
    food_item?: string;
    meal?: string;
    date?: string;
    attendance?: number;
  }) =>
    request<ChatResponse>('/api/chat', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  recordMessWiseOutcome: (payload: {
    date: string;
    meal: string;
    food_item: string;
    prepared_portions: number;
    actual_consumers: number;
    leftover_portions: number;
    predicted_consumers?: number;
  }) =>
    request<PerformanceEvaluation>('/api/meal-outcomes', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getMessWisePerformance: () =>
    request<{
      evaluation: PerformanceEvaluation;
      recorded_outcomes: MealOutcomeRecord[];
      model_metadata: Record<string, any>;
    }>('/api/performance'),

  getMessWiseAgentStatus: () => request<{ agents: Array<{ id: string; name: string; status: string; type: string; purpose: string }> }>('/api/agent-status'),
};

