import React, { useState, useEffect } from 'react';
import {
  Utensils,
  TrendingUp,
  AlertTriangle,
  CloudRain,
  Sun,
  Users,
  Award,
  BookOpen,
  CheckCircle2,
  Clock,
  Sparkles,
  Info,
  Layers,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  ShieldCheck,
  Send,
  Database,
  ArrowRight,
} from 'lucide-react';
import { api } from '../api/client';
import { MessWiseChatbot } from '../components/MessWiseChatbot';
import type {
  DemandForecastResult,
  KitchenPlanResult,
  WasteDiagnosisResult,
  FoodPreferenceResult,
  SmartSuggestion,
  MessWiseContext,
  MealOutcomeRecord,
  PerformanceEvaluation,
} from '../types/messwise';

interface MessWiseDashboardProps {
  onNavigateToConsole?: () => void;
}

export const MessWiseDashboard: React.FC<MessWiseDashboardProps> = ({ onNavigateToConsole }) => {
  // Navigation & Selector states
  const [dates, setDates] = useState<string[]>(['2026-08-04']);
  const [selectedDate, setSelectedDate] = useState<string>('2026-08-04');
  const [selectedMeal, setSelectedMeal] = useState<string>('Lunch');
  const [dishes, setDishes] = useState<string[]>(['White Rice']);
  const [selectedDish, setSelectedDish] = useState<string>('White Rice');

  // Attendance override state
  const [attendanceOverride, setAttendanceOverride] = useState<string>('');
  const [demoWeatherMode, setDemoWeatherMode] = useState<string>('auto');

  // Agent outputs
  const [context, setContext] = useState<MessWiseContext | null>(null);
  const [forecast, setForecast] = useState<DemandForecastResult | null>(null);
  const [plan, setPlan] = useState<KitchenPlanResult | null>(null);
  const [waste, setWaste] = useState<WasteDiagnosisResult | null>(null);
  const [preference, setPreference] = useState<FoodPreferenceResult | null>(null);
  const [suggestions, setSuggestions] = useState<SmartSuggestion[]>([]);

  // Performance & Outcomes
  const [evaluation, setEvaluation] = useState<PerformanceEvaluation | null>(null);
  const [recentOutcomes, setRecentOutcomes] = useState<MealOutcomeRecord[]>([]);

  // Post-meal outcome form
  const [outcomePrep, setOutcomePrep] = useState<string>('455');
  const [outcomeActual, setOutcomeActual] = useState<string>('443');
  const [outcomeLeftover, setOutcomeLeftover] = useState<string>('12');
  const [outcomeSubmitting, setOutcomeSubmitting] = useState(false);
  const [outcomeFeedbackMsg, setOutcomeFeedbackMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // UI state
  const [loading, setLoading] = useState(true);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  // 1. Initial menu load
  useEffect(() => {
    api
      .getMessWiseMenu()
      .then((res) => {
        if (res.dates && res.dates.length > 0) setDates(res.dates);
        if (res.dishes && res.dishes.length > 0) {
          setDishes(res.dishes);
          if (!res.dishes.includes(selectedDish)) {
            setSelectedDish(res.dishes[0]);
          }
        }
      })
      .catch((err) => console.warn('Menu load note:', err));
  }, []);

  // 2. Load dishes when Date or Meal changes
  useEffect(() => {
    api
      .getMessWiseMenu(selectedDate, selectedMeal)
      .then((res) => {
        if (res.dishes && res.dishes.length > 0) {
          setDishes(res.dishes);
          // Default to White Rice if available, else first item
          if (res.dishes.includes('White Rice')) {
            setSelectedDish('White Rice');
          } else if (!res.dishes.includes(selectedDish)) {
            setSelectedDish(res.dishes[0]);
          }
        }
      })
      .catch((err) => console.warn('Dish load note:', err));
  }, [selectedDate, selectedMeal]);

  // 3. Load Context, Predictions, Kitchen Plan, Waste, Suggestions
  const loadDashboardData = async () => {
    setLoading(true);
    setOutcomeFeedbackMsg(null);
    try {
      const attNum = attendanceOverride ? parseInt(attendanceOverride, 10) : undefined;
      const weatherParam = demoWeatherMode === 'auto' ? undefined : demoWeatherMode;

      // 1. Context (includes preference, attendance, weather)
      const ctx = await api.getMessWiseContext(selectedDate, selectedMeal, selectedDish, weatherParam);
      setContext(ctx);

      // 2. Demand Forecast (Agent 2)
      const pred = await api.predictMessWiseDemand({
        food_item: selectedDish,
        date: selectedDate,
        meal: selectedMeal,
        attendance: attNum || ctx.attendance_estimate,
        exam_intensity: ctx.exam_intensity,
        temperature_c: ctx.weather?.temperature_c || 28.0,
        rainfall_mm: ctx.weather?.rainfall_mm || 0.0,
      });
      setForecast(pred);

      // 3. Waste Diagnosis (Agent 3)
      const wasteDiag = await api.analyzeMessWiseWaste({
        food_item: selectedDish,
        meal: selectedMeal,
        date: selectedDate,
      });
      setWaste(wasteDiag);

      // 4. Kitchen Plan (Agent 4)
      const kPlan = await api.getMessWiseKitchenPlan({
        food_item: selectedDish,
        predicted_demand: pred.predicted_consumers,
        meal: selectedMeal,
        risk_level: wasteDiag.risk_level,
      });
      setPlan(kPlan);

      // 5. Food Preference (Agent 1)
      const pref = await api.getMessWisePreference(selectedDish, selectedMeal);
      setPreference(pref);

      // 6. Proactive Smart Suggestions
      const suggs = await api.getMessWiseSuggestions(
        selectedDish,
        selectedMeal,
        selectedDate,
        attNum || ctx.attendance_estimate,
        weatherParam
      );
      setSuggestions(suggs);

      // Pre-populate outcome form with realistic demonstration values
      setOutcomePrep(String(pred.predicted_consumers + 20));
      setOutcomeActual(String(pred.predicted_consumers - 5));
      setOutcomeLeftover('25');
    } catch (err: any) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  // Reload when core selection changes
  useEffect(() => {
    loadDashboardData();
  }, [selectedDate, selectedMeal, selectedDish, demoWeatherMode]);

  // Load Feedback & Learning Agent Performance
  const loadPerformance = () => {
    api
      .getMessWisePerformance()
      .then((res) => {
        setEvaluation(res.evaluation);
        setRecentOutcomes(res.recorded_outcomes || []);
      })
      .catch((err) => console.warn('Performance note:', err));
  };

  useEffect(() => {
    loadPerformance();
  }, []);

  // Handle Suggestion Action (Dismiss / Complete)
  const handleSuggestionAction = async (id: string, action: 'dismiss' | 'complete') => {
    try {
      await api.actionMessWiseSuggestion(id, action);
      setSuggestions((prev) =>
        prev.map((s) => (s.id === id ? { ...s, is_dismissed: action === 'dismiss', is_completed: action === 'complete' } : s))
      );
    } catch (err) {
      console.warn('Suggestion action error:', err);
    }
  };

  // Submit Post-Meal Outcome (Agent 5)
  const handleSubmitOutcome = async (e: React.FormEvent) => {
    e.preventDefault();
    setOutcomeSubmitting(true);
    setOutcomeFeedbackMsg(null);

    const prep = parseFloat(outcomePrep);
    const actual = parseFloat(outcomeActual);
    const leftover = parseFloat(outcomeLeftover);

    // Validation
    if (isNaN(prep) || isNaN(actual) || isNaN(leftover)) {
      setOutcomeFeedbackMsg({ type: 'error', text: 'All values must be valid numbers.' });
      setOutcomeSubmitting(false);
      return;
    }
    if (prep < 0 || actual < 0 || leftover < 0) {
      setOutcomeFeedbackMsg({ type: 'error', text: 'Values cannot be negative.' });
      setOutcomeSubmitting(false);
      return;
    }
    if (leftover > prep) {
      setOutcomeFeedbackMsg({
        type: 'error',
        text: `Leftover (${leftover}) cannot exceed prepared portions (${prep}).`,
      });
      setOutcomeSubmitting(false);
      return;
    }

    try {
      const result = await api.recordMessWiseOutcome({
        date: selectedDate,
        meal: selectedMeal,
        food_item: selectedDish,
        prepared_portions: prep,
        actual_consumers: actual,
        leftover_portions: leftover,
        predicted_consumers: forecast?.predicted_consumers,
      });

      setOutcomeFeedbackMsg({
        type: 'success',
        text: `Outcome recorded! Error: ${Math.abs(actual - (forecast?.predicted_consumers || actual))} portions. Updated MAE: ${result.mae} portions across ${result.records_validated} meals.`,
      });
      loadPerformance();
    } catch (err: any) {
      setOutcomeFeedbackMsg({
        type: 'error',
        text: err.message || 'Failed to submit post-meal outcome.',
      });
    } finally {
      setOutcomeSubmitting(false);
    }
  };

  return (
    <div className="messwise-kitchen-container">
      {/* Top Banner Notice */}
      <div className="kitchen-guardrail-banner">
        <div className="guardrail-content">
          <ShieldCheck size={18} className="shield-icon" />
          <span>
            <strong>MessWise Operations Cockpit:</strong> Sourced from synthetic menu dataset (August 2026).
            All calculations are executed by real Random Forest ML and deterministic kitchen rules.
          </span>
        </div>
        {onNavigateToConsole && (
          <button
            type="button"
            className="switch-console-btn"
            onClick={onNavigateToConsole}
          >
            <span>Advanced Research Console</span>
            <ArrowRight size={14} />
          </button>
        )}
      </div>

      {/* Top Selection & Quick Context Bar */}
      <div className="kitchen-selection-bar">
        <div className="selectors-group">
          {/* Date Selector */}
          <div className="select-field">
            <label htmlFor="mess-date-select">Date</label>
            <select
              id="mess-date-select"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="styled-select"
            >
              {dates.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>

          {/* Meal Selector */}
          <div className="select-field">
            <label htmlFor="mess-meal-select">Meal Period</label>
            <select
              id="mess-meal-select"
              value={selectedMeal}
              onChange={(e) => setSelectedMeal(e.target.value)}
              className="styled-select"
            >
              <option value="Breakfast">Breakfast</option>
              <option value="Lunch">Lunch</option>
              <option value="Snacks">Snacks</option>
              <option value="Dinner">Dinner</option>
            </select>
          </div>

          {/* Food Item Dropdown */}
          <div className="select-field select-field--primary">
            <label htmlFor="mess-dish-select">Selected Food Item</label>
            <select
              id="mess-dish-select"
              value={selectedDish}
              onChange={(e) => setSelectedDish(e.target.value)}
              className="styled-select styled-select--highlight"
            >
              {dishes.map((dish) => (
                <option key={dish} value={dish}>
                  {dish}
                </option>
              ))}
            </select>
          </div>

          {/* Quick Attendance Override Input */}
          <div className="select-field select-field--override">
            <label htmlFor="mess-att-override">Attendance Override</label>
            <input
              id="mess-att-override"
              type="number"
              placeholder={context ? String(context.attendance_estimate) : 'Auto'}
              value={attendanceOverride}
              onChange={(e) => setAttendanceOverride(e.target.value)}
              onBlur={() => loadDashboardData()}
              onKeyDown={(e) => e.key === 'Enter' && loadDashboardData()}
              className="styled-input"
            />
          </div>

          {/* Demo Weather Switch */}
          <div className="select-field">
            <label htmlFor="demo-weather-select">Weather Simulator</label>
            <select
              id="demo-weather-select"
              value={demoWeatherMode}
              onChange={(e) => setDemoWeatherMode(e.target.value)}
              className="styled-select"
            >
              <option value="auto">Live / CSV Auto</option>
              <option value="rain_storm">🌧️ Demo Rain Storm (18.5mm)</option>
            </select>
          </div>
        </div>

        {/* Live Context Indicators */}
        <div className="context-indicators-group">
          {/* Attendance Estimate */}
          <div className="context-badge">
            <Users size={16} className="badge-icon icon-users" />
            <div className="badge-text">
              <span className="badge-value">
                {attendanceOverride || context?.attendance_estimate || '...'}
              </span>
              <span className="badge-label">Expected Attendance</span>
            </div>
          </div>

          {/* Weather Status */}
          <div className="context-badge">
            {context?.weather?.rain_expected_during_meal ? (
              <CloudRain size={16} className="badge-icon icon-rain" />
            ) : (
              <Sun size={16} className="badge-icon icon-sun" />
            )}
            <div className="badge-text">
              <span className="badge-value">
                {context?.weather?.temperature_c ? `${context.weather.temperature_c}°C` : '--'}
                {context?.weather?.rainfall_mm && context.weather.rainfall_mm > 0
                  ? ` • ${context.weather.rainfall_mm}mm rain`
                  : ''}
              </span>
              <span className="badge-label">
                {context?.weather?.is_live ? 'Live Forecast' : 'Historical/Demo'}
              </span>
            </div>
          </div>

          {/* Student Preference */}
          <div className="context-badge">
            <Award size={16} className="badge-icon icon-pref" />
            <div className="badge-text">
              <span className="badge-value">
                {preference ? `${preference.preference_score}/100` : '--'}
              </span>
              <span className="badge-label">Preference Score</span>
            </div>
          </div>

          {/* Exam Intensity */}
          <div className="context-badge">
            <BookOpen size={16} className="badge-icon icon-exam" />
            <div className="badge-text">
              <span className="badge-value">
                {context ? `${Math.round(context.exam_intensity * 100)}%` : '--'}
              </span>
              <span className="badge-label">Exam Intensity</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main 3 Action Cards for Kitchen Staff */}
      <div className="kitchen-hero-grid">
        {/* Card 1: Expected Demand */}
        <div className="hero-card hero-card--demand">
          <div className="card-top-header">
            <div className="card-title-wrap">
              <span className="card-step-badge">Card 1</span>
              <h2 className="card-heading">Expected Demand</h2>
            </div>
            <span className="model-tag">Model: {forecast?.model_version || 'rf_v1'}</span>
          </div>

          <div className="card-metric-block">
            <div className="large-number-stat">
              {loading ? (
                <span className="pulsing-placeholder">...</span>
              ) : (
                `${forecast?.predicted_consumers || 0}`
              )}
              <span className="unit-label">servings</span>
            </div>
            {forecast?.uncertainty && (
              <div className="uncertainty-subtag">
                90% bounds: {forecast.uncertainty.lower} – {forecast.uncertainty.upper} servings
              </div>
            )}
          </div>

          <p className="card-description">
            {forecast?.explanation ||
              'Predicting demand based on today attendance estimate, dish preference, academic exams, and weather conditions.'}
          </p>
        </div>

        {/* Card 2: Recommended Preparation */}
        <div className="hero-card hero-card--prep">
          <div className="card-top-header">
            <div className="card-title-wrap">
              <span className="card-step-badge">Card 2</span>
              <h2 className="card-heading">Recommended Preparation</h2>
            </div>
            <span className="split-ratio-tag">Split: {plan?.batch_ratio || '70% / 30%'}</span>
          </div>

          <div className="card-metric-block">
            <div className="prep-split-stat">
              <div className="split-col">
                <span className="split-num">{plan?.initial_batch_servings || 0}</span>
                <span className="split-lbl">Initial Batch</span>
              </div>
              <span className="split-plus">+</span>
              <div className="split-col">
                <span className="split-num">{plan?.reserve_servings || 0}</span>
                <span className="split-lbl">Staged Reserve</span>
              </div>
            </div>
          </div>

          <div className="replenishment-alert-box">
            <Clock size={16} className="alert-box-icon" />
            <div className="alert-box-text">
              <strong>Checkpoint:</strong>{' '}
              {plan?.replenishment_check || 'Check counter after initial batch before preparing reserve.'}
            </div>
          </div>
        </div>

        {/* Card 3: Waste Risk */}
        <div className={`hero-card hero-card--risk risk-tier--${waste?.risk_level || 'low'}`}>
          <div className="card-top-header">
            <div className="card-title-wrap">
              <span className="card-step-badge">Card 3</span>
              <h2 className="card-heading">Waste Risk</h2>
            </div>
            <span className={`risk-pill risk-pill--${waste?.risk_level || 'low'}`}>
              {(waste?.risk_level || 'low').toUpperCase()} RISK
            </span>
          </div>

          <div className="card-metric-block">
            <div className="large-number-stat">
              {waste?.observed_waste_rate !== null && waste?.observed_waste_rate !== undefined
                ? `${waste.observed_waste_rate}%`
                : '--'}
              <span className="unit-label">historical leftovers</span>
            </div>
          </div>

          <div className="risk-reasons-list">
            {waste?.possible_factors && waste.possible_factors.length > 0 ? (
              <p className="card-description">{waste.possible_factors[0]}</p>
            ) : (
              <p className="card-description">
                Dish has manageable leftover history (&lt;5%). Standard split-batching is recommended.
              </p>
            )}
            {waste?.recommended_actions && waste.recommended_actions.length > 0 && (
              <div className="remedy-highlight">
                <CheckCircle2 size={14} className="remedy-icon" />
                <span>{waste.recommended_actions[0]}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* TODAY'S PROACTIVE SMART SUGGESTIONS */}
      <section className="kitchen-section suggestions-section">
        <div className="section-header-row">
          <div className="section-title-wrap">
            <Sparkles size={20} className="section-header-icon" />
            <h2 className="section-title">Today's Smart Suggestions</h2>
          </div>
          <span className="section-badge">{suggestions.filter((s) => !s.is_dismissed).length} Active Actions</span>
        </div>

        {suggestions.filter((s) => !s.is_dismissed).length === 0 ? (
          <div className="empty-suggestions-card">
            <CheckCircle2 size={24} className="empty-icon" />
            <p>No active warnings for {selectedDish}. All preparation parameters are within normal ranges.</p>
          </div>
        ) : (
          <div className="suggestions-grid">
            {suggestions
              .filter((s) => !s.is_dismissed)
              .map((s) => (
                <div
                  key={s.id}
                  className={`suggestion-card suggestion-card--${s.severity} ${
                    s.is_completed ? 'suggestion-card--done' : ''
                  }`}
                >
                  <div className="suggestion-top">
                    <div className="suggestion-cat-tag">
                      {s.category === 'weather' && <CloudRain size={14} />}
                      {s.category === 'waste' && <AlertTriangle size={14} />}
                      {s.category === 'attendance' && <Users size={14} />}
                      {s.category === 'popularity' && <Award size={14} />}
                      {s.category === 'demand' && <TrendingUp size={14} />}
                      <span>{s.category.toUpperCase()}</span>
                    </div>
                    <span className="suggestion-time">Triggered by: {s.triggered_by[0] || 'Rule'}</span>
                  </div>

                  <h3 className="suggestion-title">{s.title}</h3>
                  <p className="suggestion-message">{s.message}</p>

                  {s.recommended_action && (
                    <div className="suggestion-action-box">
                      <strong>Action:</strong> {s.recommended_action}
                    </div>
                  )}

                  <div className="suggestion-footer">
                    <button
                      type="button"
                      className="suggestion-btn suggestion-btn--complete"
                      onClick={() => handleSuggestionAction(s.id, 'complete')}
                      disabled={s.is_completed}
                    >
                      <CheckCircle2 size={14} />
                      {s.is_completed ? 'Completed' : 'Mark Done'}
                    </button>
                    <button
                      type="button"
                      className="suggestion-btn suggestion-btn--dismiss"
                      onClick={() => handleSuggestionAction(s.id, 'dismiss')}
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              ))}
          </div>
        )}
      </section>

      {/* Kitchen Batch & Recipe Yields Breakdown */}
      <section className="kitchen-section batch-guide-section">
        <div className="section-header-row">
          <div className="section-title-wrap">
            <Layers size={20} className="section-header-icon" />
            <h2 className="section-title">Kitchen Batch & Recipe Preparation Guide</h2>
          </div>
          <span className="section-badge">
            {plan?.has_validated_recipe ? 'Validated Recipe On File' : 'Portion Yield Mode'}
          </span>
        </div>

        <div className="batch-guide-grid">
          {/* Visual Batch Split Diagram */}
          <div className="batch-split-diagram-card">
            <h4 className="card-subheading">Batch Split Breakdown for {selectedDish}</h4>
            <div className="batch-bar-container">
              <div
                className="batch-bar-segment batch-bar-segment--initial"
                style={{
                  width: `${
                    plan?.predicted_demand
                      ? Math.round((plan.initial_batch_servings / plan.predicted_demand) * 100)
                      : 70
                  }%`,
                }}
              >
                <span>Initial Batch: {plan?.initial_batch_servings} servings</span>
              </div>
              <div
                className="batch-bar-segment batch-bar-segment--reserve"
                style={{
                  width: `${
                    plan?.predicted_demand
                      ? Math.round((plan.reserve_servings / plan.predicted_demand) * 100)
                      : 30
                  }%`,
                }}
              >
                <span>Reserve: {plan?.reserve_servings} servings</span>
              </div>
            </div>

            <div className="batch-instructions-box">
              <p>
                <strong>Operational Protocol:</strong> Cook{' '}
                <span className="hl-green">{plan?.initial_batch_servings} servings</span> before meal begins.
                Hold the ingredients for{' '}
                <span className="hl-amber">{plan?.reserve_servings} servings</span> ready in clean prep containers.
                Only cook batch 2 if counter count exceeds{' '}
                <span className="hl-blue">{plan?.replenishment_threshold} servings</span>.
              </p>
            </div>
          </div>

          {/* Ingredient Yields Table */}
          <div className="recipe-ingredients-card">
            <h4 className="card-subheading">Raw Ingredient Requirements ({plan?.predicted_demand || 0} servings)</h4>
            {plan?.ingredient_requirements && plan.ingredient_requirements.length > 0 ? (
              <div className="ingredients-table-wrap">
                <table className="ingredients-table">
                  <thead>
                    <tr>
                      <th>Ingredient</th>
                      <th>Calculated Quantity</th>
                      <th>Unit</th>
                    </tr>
                  </thead>
                  <tbody>
                    {plan.ingredient_requirements.map((ing) => (
                      <tr key={ing.ingredient}>
                        <td>{ing.ingredient}</td>
                        <td className="qty-cell">{ing.quantity}</td>
                        <td>{ing.unit}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {plan.food_safety && (
                  <div className="food-safety-pill">
                    <ShieldCheck size={14} />
                    <span>Safe Holding: {plan.food_safety.safe_holding_temp} (Max {plan.food_safety.max_holding_hours} hrs)</span>
                  </div>
                )}
              </div>
            ) : (
              <div className="no-recipe-notice">
                <Info size={18} />
                <p>
                  No verified recipe is registered for <strong>{selectedDish}</strong>. Quantities are shown in discrete
                  portions. Please submit kitchen recipe ratios to calculate raw kilograms.
                </p>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Post-Meal Outcome Logger (Agent 5 - Feedback & Learning) */}
      <section className="kitchen-section outcome-logger-section">
        <div className="section-header-row">
          <div className="section-title-wrap">
            <RotateCcw size={20} className="section-header-icon" />
            <h2 className="section-title">Post-Meal Outcome Logger (Feedback & Learning Agent)</h2>
          </div>
          <span className="section-badge">Agent 5 • SQLite Persistent</span>
        </div>

        <div className="outcome-logger-layout">
          {/* Submission Form */}
          <form className="outcome-form-card" onSubmit={handleSubmitOutcome}>
            <h4 className="card-subheading">Record Service Results for {selectedDish} ({selectedMeal})</h4>
            <div className="form-inputs-row">
              <div className="form-group">
                <label htmlFor="outcome-prep">Total Portions Prepared</label>
                <input
                  id="outcome-prep"
                  type="number"
                  value={outcomePrep}
                  onChange={(e) => setOutcomePrep(e.target.value)}
                  className="form-input"
                  min="0"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="outcome-actual">Actual Diners Served</label>
                <input
                  id="outcome-actual"
                  type="number"
                  value={outcomeActual}
                  onChange={(e) => setOutcomeActual(e.target.value)}
                  className="form-input"
                  min="0"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="outcome-leftover">Untouched Leftover Portions</label>
                <input
                  id="outcome-leftover"
                  type="number"
                  value={outcomeLeftover}
                  onChange={(e) => setOutcomeLeftover(e.target.value)}
                  className="form-input"
                  min="0"
                  required
                />
              </div>
            </div>

            {outcomeFeedbackMsg && (
              <div className={`form-feedback-alert form-feedback-alert--${outcomeFeedbackMsg.type}`}>
                {outcomeFeedbackMsg.type === 'success' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
                <span>{outcomeFeedbackMsg.text}</span>
              </div>
            )}

            <button
              type="submit"
              className="submit-outcome-btn"
              disabled={outcomeSubmitting}
            >
              <Send size={16} />
              {outcomeSubmitting ? 'Validating & Persisting...' : 'Verify & Record Meal Outcome'}
            </button>
          </form>

          {/* Model Feedback Metrics Display */}
          <div className="outcome-metrics-card">
            <h4 className="card-subheading">Model Accuracy & Drift Tracking</h4>
            <div className="drift-metrics-grid">
              <div className="metric-box">
                <span className="metric-box-val">
                  {evaluation?.mae !== null && evaluation?.mae !== undefined ? `${evaluation.mae}` : '--'}
                </span>
                <span className="metric-box-lbl">Mean Absolute Error (MAE)</span>
              </div>
              <div className="metric-box">
                <span className="metric-box-val">
                  {evaluation?.forecast_bias !== null && evaluation?.forecast_bias !== undefined
                    ? `${evaluation.forecast_bias > 0 ? '+' : ''}${evaluation.forecast_bias}`
                    : '--'}
                </span>
                <span className="metric-box-lbl">Forecast Bias (Servings)</span>
              </div>
              <div className="metric-box">
                <span className="metric-box-val">{evaluation?.records_validated || 0}</span>
                <span className="metric-box-lbl">Meals Validated in DB</span>
              </div>
            </div>

            <p className="drift-explanation">
              {evaluation?.explanation ||
                'Record post-meal outcomes to track model performance against verified kitchen service.'}
            </p>
          </div>
        </div>
      </section>

      {/* Expandable Technical Model Specifications & Recorded Log */}
      <section className="kitchen-section technical-details-section">
        <button
          type="button"
          className="technical-details-toggle"
          onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
        >
          <div className="toggle-left">
            <Database size={18} />
            <span>Technical Model Details, Baseline Benchmark, & Data Provenance</span>
          </div>
          {showTechnicalDetails ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>

        {showTechnicalDetails && (
          <div className="technical-details-content">
            <div className="tech-specs-grid">
              <div className="spec-card">
                <h5>Model Architecture</h5>
                <ul>
                  <li><strong>Type:</strong> Scikit-Learn RandomForestRegressor Pipeline</li>
                  <li><strong>Model Version:</strong> rf_v1 (Fixed Seed: 42)</li>
                  <li><strong>Trained Samples:</strong> 973 records from August 2026 dataset</li>
                  <li><strong>Holdout Test MAE:</strong> 3.54 servings</li>
                  <li><strong>Baseline MAE:</strong> 0.49 servings (attendance × historical demand rate)</li>
                  <li><strong>R² Score:</strong> 0.9920</li>
                </ul>
              </div>

              <div className="spec-card">
                <h5>Strict Leakage Prevention</h5>
                <ul>
                  <li><strong>Target:</strong> expected_consumers</li>
                  <li><strong>Excluded Output Fields:</strong> consumed_portions, leftover_portions, waste_rate_pct, prepared_portions</li>
                  <li><strong>Prediction Features:</strong> food_item, meal, day_of_week, synthetic_liking_score, exam_intensity, temperature_c, rainfall_mm, is_weekend, hostel_attendance_estimate, historical_demand_rate</li>
                </ul>
              </div>

              <div className="spec-card">
                <h5>Five Autonomous Agents</h5>
                <ul>
                  <li><strong>Agent 1 (Preference):</strong> Deterministic aggregation (0-100)</li>
                  <li><strong>Agent 2 (Forecasting):</strong> Random Forest ML with attendance caps</li>
                  <li><strong>Agent 3 (Waste Diagnosis):</strong> Transparent leftover rules & factors</li>
                  <li><strong>Agent 4 (Kitchen Optimization):</strong> Constrained split-batch policy</li>
                  <li><strong>Agent 5 (Feedback & Learning):</strong> SQLite outcome validation & drift monitor</li>
                </ul>
              </div>
            </div>

            {/* Recent Recorded Outcomes Table */}
            {recentOutcomes && recentOutcomes.length > 0 && (
              <div className="recent-outcomes-table-wrap">
                <h5 className="sub-table-heading">Persistent Database Outcomes ({recentOutcomes.length} records)</h5>
                <table className="outcomes-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Meal</th>
                      <th>Dish</th>
                      <th>Predicted</th>
                      <th>Prepared</th>
                      <th>Actual Served</th>
                      <th>Leftover</th>
                      <th>Waste Rate</th>
                      <th>Abs Error</th>
                      <th>Bias</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentOutcomes.slice(0, 10).map((o) => (
                      <tr key={o.id}>
                        <td>{o.date}</td>
                        <td>{o.meal}</td>
                        <td>{o.food_item}</td>
                        <td>{o.predicted_consumers}</td>
                        <td>{o.prepared_portions}</td>
                        <td>{o.actual_consumers}</td>
                        <td>{o.leftover_portions}</td>
                        <td>{o.waste_rate_pct}%</td>
                        <td>{o.absolute_error}</td>
                        <td className={o.bias > 0 ? 'hl-amber' : 'hl-green'}>
                          {o.bias > 0 ? `+${o.bias}` : o.bias}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </section>

      {/* Floating Ask MessWise Chatbot */}
      <MessWiseChatbot
        activeDish={selectedDish}
        activeMeal={selectedMeal}
        activeDate={selectedDate}
        activeAttendance={attendanceOverride ? parseInt(attendanceOverride, 10) : context?.attendance_estimate}
      />
    </div>
  );
};
