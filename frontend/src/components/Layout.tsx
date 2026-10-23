import React, { useEffect, useState } from 'react';
import {
  LayoutDashboard,
  CalendarCheck,
  TrendingUp,
  MapPin,
  Stethoscope,
  Flame,
  PieChart,
  Award,
  Cpu,
  Settings,
  Server,
  AlertTriangle,
  Menu,
  X,
  Utensils,
  ChevronRight,
} from 'lucide-react';
import { SyntheticBanner } from './SyntheticBanner';
import { api } from '../api/client';
import type { MealType } from '../types';

export type PageId =
  | 'messwise'
  | 'overview'
  | 'meal-planner'
  | 'rush-timeline'
  | 'context-availability'
  | 'waste-diagnosis'
  | 'kitchen-simulation'
  | 'menu-analytics'
  | 'evaluation'
  | 'agent-trace'
  | 'settings-data';

interface LayoutProps {
  currentPage: PageId;
  onNavigate: (page: PageId) => void;
  selectedDate: string;
  onDateChange: (date: string) => void;
  selectedMeal: MealType;
  onMealChange: (meal: MealType) => void;
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({
  currentPage,
  onNavigate,
  selectedDate,
  onDateChange,
  selectedMeal,
  onMealChange,
  children,
}) => {
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    let isMounted = true;
    api
      .getHealth()
      .then((res) => {
        if (isMounted) setBackendHealthy(res.status === 'ok');
      })
      .catch(() => {
        if (isMounted) setBackendHealthy(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const navItems = [
    { id: 'messwise' as PageId, label: 'MessWise Kitchen Operations', icon: <Utensils size={18} /> },
    { id: 'overview' as PageId, label: 'Executive Overview', icon: <LayoutDashboard size={18} /> },
    { id: 'meal-planner' as PageId, label: 'Smart Meal Planner', icon: <CalendarCheck size={18} /> },
    { id: 'rush-timeline' as PageId, label: 'Rush Timeline', icon: <TrendingUp size={18} /> },
    { id: 'context-availability' as PageId, label: 'Context & Availability', icon: <MapPin size={18} /> },
    { id: 'waste-diagnosis' as PageId, label: 'Waste Diagnosis', icon: <Stethoscope size={18} /> },
    { id: 'kitchen-simulation' as PageId, label: 'Kitchen Simulation', icon: <Flame size={18} /> },
    { id: 'menu-analytics' as PageId, label: 'Menu Analytics', icon: <PieChart size={18} /> },
    { id: 'evaluation' as PageId, label: 'Policy Evaluation', icon: <Award size={18} /> },
    { id: 'agent-trace' as PageId, label: 'Agent Orchestrator Trace', icon: <Cpu size={18} /> },
    { id: 'settings-data' as PageId, label: 'Settings & Data Management', icon: <Settings size={18} /> },
  ];

  return (
    <div className="app-shell">
      {/* Top Header */}
      <header className="top-navbar">
        <div className="top-navbar__left">
          <button
            type="button"
            className="mobile-menu-btn"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle navigation"
          >
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>

          <div className="brand-logo" onClick={() => onNavigate('messwise')}>
            <span className="brand-icon">🌱</span>
            <div className="brand-text">
              <span className="brand-title">MessWise</span>
              <span className="brand-subtitle">AI Food Waste Optimizer</span>
            </div>
          </div>
        </div>

        {/* Global Controls */}
        <div className="top-navbar__center">
          <div className="global-scenario-selector">
            <span className="selector-label">Service Date:</span>
            <input
              type="date"
              className="input-date"
              value={selectedDate}
              onChange={(e) => onDateChange(e.target.value)}
            />

            <span className="selector-label">Meal:</span>
            <select
              className="select-meal"
              value={selectedMeal}
              onChange={(e) => onMealChange(e.target.value as MealType)}
            >
              <option value="breakfast">Breakfast (07:00–09:30)</option>
              <option value="lunch">Lunch (12:00–14:00)</option>
              <option value="snacks">Snacks (16:30–18:15)</option>
              <option value="dinner">Dinner (19:00–21:00)</option>
            </select>
          </div>
        </div>

        <div className="top-navbar__right">
          <div className="backend-status-indicator">
            <Server size={14} />
            <span className="status-label">Backend:</span>
            {backendHealthy === null ? (
              <span className="status-pill status-pill--checking">Checking...</span>
            ) : backendHealthy ? (
              <span className="status-pill status-pill--online" title="FastAPI connected">
                Online (:8000)
              </span>
            ) : (
              <span className="status-pill status-pill--offline" title="FastAPI unreachable">
                Offline
              </span>
            )}
          </div>
        </div>
      </header>

      {/* Main Body with Sidebar + Content */}
      <div className="app-container">
        {/* Sidebar Navigation */}
        <nav className={`sidebar ${mobileMenuOpen ? 'sidebar--open' : ''}`}>
          <div className="sidebar-section-title">PRIMARY OPERATIONS</div>
          <ul className="nav-list" style={{ marginBottom: '16px' }}>
            <li className="nav-item">
              <button
                type="button"
                id="nav-messwise"
                className={`nav-button ${currentPage === 'messwise' ? 'nav-button--active' : ''}`}
                style={{
                  background: currentPage === 'messwise' ? 'rgba(99, 102, 241, 0.25)' : 'rgba(99, 102, 241, 0.1)',
                  borderColor: 'rgba(99, 102, 241, 0.4)',
                  fontWeight: 600,
                }}
                onClick={() => {
                  onNavigate('messwise');
                  setMobileMenuOpen(false);
                }}
              >
                <span className="nav-icon" style={{ color: '#818cf8' }}><Utensils size={18} /></span>
                <span className="nav-label">MessWise Kitchen Dashboard</span>
                {currentPage === 'messwise' && <span className="nav-active-pip" />}
              </button>
            </li>
          </ul>

          <div className="sidebar-section-title">RESEARCH & OPERATIONS CONSOLE</div>
          <ul className="nav-list">
            {navItems.slice(1).map((item) => {
              const isActive = currentPage === item.id;
              return (
                <li key={item.id} className="nav-item">
                  <button
                    type="button"
                    id={`nav-${item.id}`}
                    className={`nav-button ${isActive ? 'nav-button--active' : ''}`}
                    onClick={() => {
                      onNavigate(item.id);
                      setMobileMenuOpen(false);
                    }}
                  >
                    <span className="nav-icon">{item.icon}</span>
                    <span className="nav-label">{item.label}</span>
                    {isActive && <span className="nav-active-pip" />}
                  </button>
                </li>
              );
            })}
          </ul>

          <div className="sidebar-footer">
            <div className="sidebar-meta-card">
              <div className="meta-row">
                <span>Demand Model:</span>
                <code>rf_v1 (RF)</code>
              </div>
              <div className="meta-row">
                <span>Dataset:</span>
                <code>Synthetic 973 Records</code>
              </div>
            </div>
          </div>
        </nav>

        {/* Main Content Pane */}
        <main className="main-content">
          <SyntheticBanner />
          <div className="page-wrapper">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};

