import React, { useState } from 'react';
import { Layout, PageId } from './components/Layout';
import { Overview } from './pages/Overview';
import { MealPlanner } from './pages/MealPlanner';
import { RushTimeline } from './pages/RushTimeline';
import { ContextAvailability } from './pages/ContextAvailability';
import { WasteDiagnosis } from './pages/WasteDiagnosis';
import { KitchenSimulation } from './pages/KitchenSimulation';
import { MenuAnalytics } from './pages/MenuAnalytics';
import { Evaluation } from './pages/Evaluation';
import { AgentTrace } from './pages/AgentTrace';
import { SettingsData } from './pages/SettingsData';
import type { MealType } from './types';

export const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<PageId>('overview');
  const [selectedDate, setSelectedDate] = useState<string>('2026-09-01');
  const [selectedMeal, setSelectedMeal] = useState<MealType>('breakfast');

  const renderCurrentPage = () => {
    switch (currentPage) {
      case 'overview':
        return (
          <Overview
            selectedDate={selectedDate}
            selectedMeal={selectedMeal}
            onNavigate={(page) => setCurrentPage(page as PageId)}
          />
        );
      case 'meal-planner':
        return (
          <MealPlanner
            selectedDate={selectedDate}
            selectedMeal={selectedMeal}
            onNavigate={(page) => setCurrentPage(page as PageId)}
          />
        );
      case 'rush-timeline':
        return (
          <RushTimeline
            selectedDate={selectedDate}
            selectedMeal={selectedMeal}
            onNavigate={(page) => setCurrentPage(page as PageId)}
          />
        );
      case 'context-availability':
        return (
          <ContextAvailability
            selectedDate={selectedDate}
            selectedMeal={selectedMeal}
          />
        );
      case 'waste-diagnosis':
        return (
          <WasteDiagnosis
            selectedDate={selectedDate}
            selectedMeal={selectedMeal}
          />
        );
      case 'kitchen-simulation':
        return (
          <KitchenSimulation
            selectedDate={selectedDate}
            selectedMeal={selectedMeal}
            onNavigate={(page) => setCurrentPage(page as PageId)}
          />
        );
      case 'menu-analytics':
        return <MenuAnalytics selectedMeal={selectedMeal} />;
      case 'evaluation':
        return (
          <Evaluation
            selectedDate={selectedDate}
            selectedMeal={selectedMeal}
          />
        );
      case 'agent-trace':
        return (
          <AgentTrace
            selectedDate={selectedDate}
            selectedMeal={selectedMeal}
          />
        );
      case 'settings-data':
        return <SettingsData />;
      default:
        return (
          <Overview
            selectedDate={selectedDate}
            selectedMeal={selectedMeal}
            onNavigate={(page) => setCurrentPage(page as PageId)}
          />
        );
    }
  };

  return (
    <Layout
      currentPage={currentPage}
      onNavigate={setCurrentPage}
      selectedDate={selectedDate}
      onDateChange={setSelectedDate}
      selectedMeal={selectedMeal}
      onMealChange={setSelectedMeal}
    >
      {renderCurrentPage()}
    </Layout>
  );
};

export default App;
