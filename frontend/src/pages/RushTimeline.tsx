import React, { useEffect, useState } from 'react';
import {
  TrendingUp,
  Clock,
  AlertTriangle,
  Info,
  Calendar,
  CloudRain,
  GraduationCap,
  Sparkles,
} from 'lucide-react';
import { api } from '../api/client';
import { ArrivalsTimelineChart, TimelineIntervalData } from '../charts/ArrivalsTimelineChart';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import type { ForecastResponse, MealType, SyntheticContext } from '../types';

interface RushTimelineProps {
  selectedDate: string;
  selectedMeal: MealType;
  onNavigate: (page: string) => void;
}

export const RushTimeline: React.FC<RushTimelineProps> = ({
  selectedDate,
  selectedMeal,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [context, setContext] = useState<SyntheticContext | null>(null);
  const [selectedIntervalTime, setSelectedIntervalTime] = useState<string>('07:30');

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [fRes, cRes] = await Promise.all([
        api.getForecasts({ date: selectedDate, meal_type: selectedMeal, persist: false }),
        api.getContext({ date: selectedDate, hostel_id: 'H01' }),
      ]);
      setForecast(fRes);
      setContext(cRes);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedDate, selectedMeal]);

  if (loading) {
    return <LoadingState message="Loading arrival intervals and context rationale..." />;
  }

  if (error && !forecast) {
    return (
      <div className="page-section">
        <ErrorState error={error} onRetry={loadData} title="Could not load rush timeline" />
      </div>
    );
  }

  const totalDemand = forecast?.rows
    ? forecast.rows.reduce((sum, r) => sum + r.prediction, 0)
    : 288;

  // Build interval timeline based on meal type
  const intervalMap: Record<
    MealType,
    Array<{ time: string; share: number; rush: 'low' | 'normal' | 'high'; note: string; factor: string }>
  > = {
    breakfast: [
      {
        time: '07:00',
        share: 0.15,
        rush: 'low',
        note: 'Early morning sports and morning lab cohort arrivals',
        factor: 'Gymnasium & early class schedules',
      },
      {
        time: '07:30',
        share: 0.35,
        rush: 'high',
        note: 'Primary attendance surge ahead of 08:00 AM core lectures',
        factor: 'Hostel release wave + 08:00 class bell',
      },
      {
        time: '08:00',
        share: 0.3,
        rush: 'normal',
        note: 'Secondary arrival wave for students with 09:00 AM slots',
        factor: 'Later morning academic cohorts',
      },
      {
        time: '08:30',
        share: 0.2,
        rush: 'low',
        note: 'Late arrivals, service tapering before kitchen closure',
        factor: 'Service close prep',
      },
    ],
    lunch: [
      {
        time: '12:00',
        share: 0.2,
        rush: 'normal',
        note: 'First lecture period end arrivals',
        factor: 'Block A classroom releases',
      },
      {
        time: '12:30',
        share: 0.45,
        rush: 'high',
        note: 'Peak university lunch rush across all hostel blocks',
        factor: 'Campus-wide lecture interval',
      },
      {
        time: '13:00',
        share: 0.25,
        rush: 'normal',
        note: 'Afternoon cohort arriving before 14:00 lab slots',
        factor: 'Laboratory shift change',
      },
      {
        time: '13:30',
        share: 0.1,
        rush: 'low',
        note: 'Closing wave',
        factor: 'Mess wind-down',
      },
    ],
    snacks: [
      {
        time: '16:00',
        share: 0.25,
        rush: 'normal',
        note: 'Evening tea kickoff',
        factor: 'Classroom release',
      },
      {
        time: '16:30',
        share: 0.45,
        rush: 'high',
        note: 'Peak snacks rush after afternoon lab completions',
        factor: 'Full hostel attendance',
      },
      {
        time: '17:00',
        share: 0.2,
        rush: 'low',
        note: 'Post-sports intake',
        factor: 'Playground crowd',
      },
      {
        time: '17:30',
        share: 0.1,
        rush: 'low',
        note: 'Snacks wrap-up',
        factor: 'Service transition',
      },
    ],
    dinner: [
      {
        time: '19:00',
        share: 0.2,
        rush: 'normal',
        note: 'Early dinner diners',
        factor: 'Library & evening study cohort',
      },
      {
        time: '19:30',
        share: 0.35,
        rush: 'high',
        note: 'Peak hostel dinner influx',
        factor: 'Main campus return wave',
      },
      {
        time: '20:00',
        share: 0.3,
        rush: 'high',
        note: 'Secondary dinner rush',
        factor: 'Hostel common hall activities',
      },
      {
        time: '20:30',
        share: 0.15,
        rush: 'low',
        note: 'Late dinner students before curfew',
        factor: 'Mess closing hour',
      },
    ],
  };

  const currentIntervals = intervalMap[selectedMeal] || intervalMap.breakfast;
  const timelineData: TimelineIntervalData[] = currentIntervals.map((intv) => ({
    time: intv.time,
    arrivals: totalDemand * intv.share,
    expected: totalDemand * intv.share,
    rushClass: intv.rush,
    contextNote: intv.note,
  }));

  const activeInterval =
    currentIntervals.find((i) => i.time === selectedIntervalTime) || currentIntervals[1];

  return (
    <div className="page-container">
      <div className="page-header-row">
        <div>
          <h2 className="page-title">Rush Timeline &amp; Context Overlays</h2>
          <p className="page-desc">
            Granular 30-minute arrival curves with academic timetables, weather dampening, and rush classifications.
          </p>
        </div>
      </div>

      {/* Main Timeline Chart */}
      <div className="card-panel">
        <ArrivalsTimelineChart
          data={timelineData}
          title={`${selectedMeal.toUpperCase()} Predicted Rush Curve — ${selectedDate}`}
          selectedInterval={selectedIntervalTime}
          onSelectInterval={(time) => setSelectedIntervalTime(time)}
        />
        <div className="card-panel-footer">
          <span className="text-muted text-xs">
            Unit: portions • Low (&lt;25%), Normal (25–35%), Peak/High (&gt;35% of meal demand)
          </span>
          <span className="text-indigo-400 text-xs">
            Click any bar to inspect interval context and driving factors.
          </span>
        </div>
      </div>

      {/* Selected Interval Detail Inspector */}
      <div className="card-panel">
        <div className="panel-header">
          <div>
            <h4 className="panel-title">
              Interval Rationale Inspector: <code>{activeInterval.time}</code>
            </h4>
            <p className="panel-subtitle">Why the system predicts this arrival velocity</p>
          </div>
          <StatusBadge
            label={`${activeInterval.rush.toUpperCase()} RUSH`}
            variant={
              activeInterval.rush === 'high'
                ? 'rush-high'
                : activeInterval.rush === 'normal'
                ? 'rush-normal'
                : 'rush-low'
            }
          />
        </div>

        <div className="interval-inspector-grid">
          <div className="inspector-card">
            <div className="inspector-card-header">
              <Clock size={16} className="text-indigo-400" />
              <span>Interval Window</span>
            </div>
            <div className="inspector-card-value">{activeInterval.time} – {activeInterval.time.substring(0, 2)}:30</div>
            <p className="inspector-card-sub">
              Expected arrivals: <strong>{(totalDemand * activeInterval.share).toFixed(0)} portions</strong> ({(activeInterval.share * 100).toFixed(0)}% of service)
            </p>
          </div>

          <div className="inspector-card">
            <div className="inspector-card-header">
              <GraduationCap size={16} className="text-cyan-400" />
              <span>Academic Timetable Factor</span>
            </div>
            <div className="inspector-card-value">{activeInterval.factor}</div>
            <p className="inspector-card-sub">{activeInterval.note}</p>
          </div>

          <div className="inspector-card">
            <div className="inspector-card-header">
              <CloudRain size={16} className="text-amber-400" />
              <span>Weather Dampening</span>
            </div>
            <div className="inspector-card-value">
              {context?.weather_label ?? 'Clear'} ({context?.rain_mm ?? 0}mm)
            </div>
            <p className="inspector-card-sub">
              {context?.rain_mm && context.rain_mm > 10
                ? 'Rain shifts student arrivals by 10-15 minutes into later intervals'
                : 'Favorable weather; standard punctuality pattern'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
