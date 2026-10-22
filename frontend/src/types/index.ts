/**
 * TypeScript Data Types and API Contracts for Food Waste Optimizer Frontend.
 * Matches Person B's FastAPI Pydantic contracts and database schemas.
 */

export type MealType = 'breakfast' | 'lunch' | 'snacks' | 'dinner';

export interface ApiErrorDetail {
  type?: string;
  loc?: string[];
  msg: string;
  input?: string;
}

export interface ApiErrorPayload {
  error: {
    code: string;
    message: string;
    details?: ApiErrorDetail[] | Record<string, unknown> | null;
    request_id?: string | null;
  };
}

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  environment: string;
  synthetic_only: boolean;
}

export interface ReadinessResponse {
  status: string;
  database: string;
  migrations: string;
  model_artifact: boolean;
}

// Menu and Catalogue
export interface Dish {
  id?: string;
  external_id: string;
  name: string;
  meal_type: MealType;
  category: string;
  is_active: boolean;
  vegetarian_flag?: boolean;
  typical_portion_size?: number;
  base_popularity?: number;
  allergens?: string[];
}

export interface MenuItem {
  id?: string;
  date: string;
  meal_type: MealType;
  dish_external_id: string;
  dish_name?: string;
  planned_qty?: number;
}

// Synthetic Context & Availability
export interface SyntheticContext {
  id?: string;
  date: string;
  hostel_id: string;
  mess_id: string;
  capacity: number;
  occupied_count: number;
  occupancy_rate: number;
  rain_mm: number;
  temperature_c: number;
  weather_label: string;
  event_id?: string | null;
  event_expected_participants?: number | null;
  occupancy_delta_vs_7d?: number | null;
  data_sources?: string[];
  is_synthetic: boolean;
}

export interface AcademicSlot {
  group_id: string;
  unavailable_share: number;
}

export interface AvailabilityRequest {
  date: string;
  meal_type: MealType;
  hostel_id?: string;
  mess_id?: string;
  attendance_probability?: number;
  academic_slots?: AcademicSlot[];
  group_sizes?: Record<string, number>;
  persist?: boolean;
}

export interface AvailabilityResponse {
  id?: string;
  date: string;
  meal_type: MealType;
  occupied_population: number;
  unavailable_population: number;
  available_population: number;
  expected_arrivals: number;
  attendance_probability: number;
  academic_unavailability_share?: number;
  event_unavailability_share?: number;
  caveats: string[];
  is_synthetic: boolean;
}

// Demand Forecasts
export interface DishForecastRow {
  date: string;
  meal_type: MealType;
  dish_id: string;
  dish_name?: string;
  prediction: number; // in portions
  lower_bound: number; // in portions
  upper_bound: number; // in portions
  model_version: string;
  selected_model?: string;
  forecast_cutoff?: string;
  feature_schema_version?: string;
  interval_method?: string;
  interval_is_calibrated?: boolean;
  unit: string;
  is_synthetic: boolean;
}

export interface ForecastResponse {
  forecast_run_id: string;
  requested_date: string;
  meal_type: MealType;
  model_version: string;
  selected_model: string;
  forecast_cutoff: string;
  feature_schema_version: string;
  interval_method: string;
  interval_is_calibrated: boolean;
  unit: string;
  is_synthetic: boolean;
  rows: DishForecastRow[];
}

// Batch Optimizer & Plans
export interface IntervalDemand {
  interval_start: string;
  expected: number;
  lower: number;
  upper: number;
}

export interface PlanRequest {
  service_date: string;
  meal_type: MealType;
  dish_external_id?: string | null;
  intervals: IntervalDemand[];
  current_stock?: number;
  batch_min?: number;
  batch_max?: number;
  kitchen_capacity?: number;
  prep_lead_minutes?: number;
  service_start?: string;
  service_close?: string;
  forecast_run_id?: string | null;
  model_version?: string | null;
  persist?: boolean;
}

export interface ConstraintCheck {
  satisfied: boolean;
  detail: string;
  margin?: number;
}

export interface PlanResponse {
  id?: string;
  service_date: string;
  meal_type: MealType;
  dish_external_id?: string | null;
  initial_quantity: number;
  reserve_quantity: number;
  replenishment_trigger: number;
  expected_leftover: number;
  expected_shortage: number;
  expected_prepared: number;
  objective_value: number;
  constraint_checks: Record<string, ConstraintCheck>;
  rationale: string;
  uncertainty: {
    expected_demand: number;
    lower_demand: number;
    upper_demand: number;
    reserve_use_probability?: number;
  };
  approval_state: string; // "proposed"
  requires_human_approval: boolean;
  simulation_only: boolean;
  is_synthetic: boolean;
}

// Live Simulations & Runs
export interface SimulationEvent {
  id?: string;
  run_id?: string;
  interval_index: number;
  interval_start: string;
  arrivals: number;
  stock_before: number;
  stock_after: number;
  prepared_qty: number;
  served_qty: number;
  unmet_qty: number;
  projected_demand: number;
  action: string; // e.g. "none", "reserve_triggered", "replenished"
  action_reason?: string | null;
}

export interface Outcome {
  id?: string;
  run_id: string;
  prepared_total: number;
  served_total: number;
  consumed_total: number;
  untouched_leftover: number;
  plate_waste: number;
  shortage: number;
  excess_preparation: number;
  forecast_error_abs?: number | null;
  forecast_error_pct?: number | null;
  waste_rate_per_prepared?: number | null;
  leftover_rate_per_prepared?: number | null;
  plate_waste_rate_per_served?: number | null;
  shortage_rate_per_demand?: number | null;
  is_synthetic: boolean;
}

export interface MealRun {
  id: string;
  scenario_id: string;
  dataset_version: string;
  seed: number;
  service_date: string;
  meal_type: MealType;
  dish_external_id?: string | null;
  policy_id: string; // "fixed_baseline" | "context_aware_split"
  policy_version: string;
  model_version?: string | null;
  forecast_run_id?: string | null;
  status: 'created' | 'running' | 'finished' | 'failed';
  current_interval: number;
  intervals_total: number;
  demand_realization: number[];
  config: Record<string, unknown>;
  started_at?: string | null;
  finished_at?: string | null;
  is_synthetic: boolean;
  events?: SimulationEvent[];
  outcome?: Outcome | null;
}

export interface SimulationCompareResponse {
  baseline_run: {
    run: MealRun;
    events: SimulationEvent[];
    outcome?: Outcome;
  };
  context_run: {
    run: MealRun;
    events: SimulationEvent[];
    outcome?: Outcome;
  };
  demand_realization: number[];
}

// Waste Diagnosis
export interface EvidenceItem {
  field: string;
  value: unknown;
  comparison?: string | null;
  source: string;
}

export interface DiagnosisCause {
  code: string;
  title: string;
  confidence: number;
  evidence: EvidenceItem[];
  rationale?: string;
}

export interface DiagnosisRecord {
  id: string;
  diagnosis_type: 'pre_meal' | 'post_meal';
  target_date: string;
  meal_type: MealType;
  dish_external_id?: string | null;
  risk_score: number;
  confidence: number;
  causes: DiagnosisCause[];
  evidence_sources: string[];
  caveats: string[];
  llm_used: boolean;
  is_synthetic: boolean;
  created_at: string;
}

// Agent Traces
export interface AgentStageOut {
  stage: string;
  agent_name: string;
  status: 'started' | 'completed' | 'failed' | 'rejected';
  duration_ms: number;
  output: Record<string, unknown>;
  error?: string | null;
}

export interface PlanningWorkflowResponse {
  trace_id: string;
  status: string;
  stages: AgentStageOut[];
  forecast_run_id?: string | null;
  plan_id?: string | null;
  diagnosis_id?: string | null;
  requires_human_approval: boolean;
  simulation_only: boolean;
}

export interface AgentTraceItem {
  id: string;
  trace_id: string;
  run_id?: string | null;
  stage: string;
  agent_name: string;
  status: string;
  input_summary: Record<string, unknown>;
  output_summary: Record<string, unknown>;
  tool_calls: Array<{ tool: string; stage: string }>;
  duration_ms: number;
  error?: string | null;
  created_at: string;
}

// Evaluation Metrics
export interface ModelForecastMetrics {
  mae: number;
  rmse: number;
  r2?: number | null;
  sample_count: number;
  model_version: string;
}

export type EvaluationMetrics = EvaluationOut['metrics'];

export interface EvaluationOut {
  id: string;
  run_id: string;
  policy_id: string;
  scenario_id: string;
  seed: number;
  policy_version: string;
  model_version?: string | null;
  metrics: {
    total_waste: number;
    untouched_leftover: number;
    plate_waste: number;
    shortage: number;
    prepared_total: number;
    served_total: number;
    consumed_total: number;
    waste_rate_per_prepared: number | null;
    leftover_rate_per_prepared: number | null;
    plate_waste_rate_per_served: number | null;
    shortage_rate_per_demand: number | null;
    [key: string]: unknown;
  };
  denominators: Record<string, number>;
  model_metrics?: Record<string, unknown> | null;
  is_synthetic: boolean;
  created_at: string;
}

export interface EvaluationComparison {
  baseline: EvaluationOut;
  context: EvaluationOut;
  deltas: {
    waste_reduction_portions?: number;
    waste_reduction_pct?: number | null;
    leftover_reduction_portions?: number;
    shortage_difference?: number;
    [key: string]: number | null | undefined;
  };
  caveats?: string[];
}

// Data Generation & Sync
export interface DataGenerateResponse {
  ok: boolean;
  output_dir: string;
  months: number;
  seed: number;
  residents: number;
  scenario_id: string;
  dataset_version: string;
  validation: {
    ok: boolean;
    errors: string[];
    files: Record<string, unknown>;
  };
}

export interface DataSyncResponse {
  ok: boolean;
  inserted_counts: Record<string, number>;
  scenario_id: string;
  dataset_version: string;
}

export interface ModelTrainResponse {
  ok: boolean;
  artifact_path: string;
  model_version: string;
  metrics: {
    mae: number;
    rmse: number;
    r2: number;
    n_samples: number;
  };
  feature_names: string[];
}
