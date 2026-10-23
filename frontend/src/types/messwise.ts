export interface MessWiseWeather {
  source: string;
  is_live: boolean;
  city: string;
  target_date: string;
  meal: string;
  temperature_c: number | null;
  rainfall_mm: number | null;
  weather_condition: string;
  rain_expected_during_meal: boolean;
  rain_forecast_mm: number;
  pop: number;
  forecast_timestamp?: string;
  retrieval_time: string;
  notes: string;
}

export interface FoodPreferenceResult {
  agent: 'food_preference';
  food_item: string;
  meal: string;
  preference_score: number;
  evidence: string[];
  confidence: 'low' | 'medium' | 'high';
  warnings: string[];
  explanation: string;
}

export interface DemandForecastResult {
  agent: 'demand_forecasting';
  food_item: string;
  meal: string;
  date: string;
  predicted_consumers: number;
  lower_bound: number;
  upper_bound: number;
  model_version: string;
  input_summary: {
    food_item: string;
    date: string;
    meal: string;
    day_of_week: string;
    attendance_estimate: number;
    preference_score: number;
    historical_demand_rate: number;
    exam_intensity: number;
    temperature_c: number;
    rainfall_mm: number;
  };
  uncertainty: {
    method: string;
    lower: number;
    upper: number;
    validation_mae: number;
  } | null;
  explanation: string;
}

export interface WasteDiagnosisResult {
  agent: 'waste_diagnosis';
  food_item: string;
  meal: string;
  risk_level: 'low' | 'medium' | 'high' | 'unknown';
  observed_waste_rate: number | null;
  evidence: string[];
  possible_factors: string[];
  recommended_actions: string[];
  warnings: string[];
}

export interface IngredientRequirement {
  ingredient: string;
  quantity: number;
  unit: string;
}

export interface KitchenPlanResult {
  agent: 'kitchen_optimization';
  food_item: string;
  meal: string;
  predicted_demand: number;
  initial_batch_servings: number;
  reserve_servings: number;
  replenishment_threshold: number;
  replenishment_check: string;
  risk_level: string;
  batch_ratio: string;
  has_validated_recipe: boolean;
  ingredient_requirements: IngredientRequirement[];
  food_safety?: {
    safe_holding_temp: string;
    max_holding_hours: number;
    guideline: string;
  };
  assumptions: string[];
}

export interface SmartSuggestion {
  id: string;
  category: 'weather' | 'waste' | 'demand' | 'attendance' | 'popularity' | 'forecast_mismatch';
  severity: 'info' | 'warning' | 'alert';
  title: string;
  message: string;
  evidence: string[];
  recommended_action: string;
  triggered_by: string[];
  created_at: string;
  is_dismissed?: boolean;
  is_completed?: boolean;
}

export interface ChatResponse {
  reply: string;
  recommended_action: string;
  tools_called: string[];
  data: Record<string, any>;
}

export interface MealOutcomeRecord {
  id: number;
  date: string;
  meal: string;
  food_item: string;
  predicted_consumers: number;
  actual_consumers: number;
  prepared_portions: number;
  leftover_portions: number;
  waste_rate_pct: number;
  absolute_error: number;
  bias: number;
  created_at: string;
}

export interface PerformanceEvaluation {
  agent: 'feedback_learning';
  records_validated: number;
  mae: number | null;
  forecast_bias: number | null;
  bias_direction?: string;
  average_waste_rate?: number;
  waste_rate_trend: number | null;
  retraining_recommended: boolean;
  warnings: string[];
  explanation: string;
}

export interface MessWiseContext {
  date: string;
  meal: string;
  food_item: string;
  attendance_estimate: number;
  exam_intensity: number;
  day_of_week: string;
  is_weekend: number;
  weather: MessWiseWeather;
  food_preference: FoodPreferenceResult;
  provenance: Record<string, string>;
}
