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
} from 'lucide-react';
import { SyntheticBanner } from './SyntheticBanner';
import { api } from '../api/client';
import type { MealType } from '../types';

export type PageId =
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
    { id: 'overview' as PageId, label: 'Overview', icon: <LayoutDashboard size={18} /> },
    { id: 'meal-planner' as PageId, label: 'Meal Planner', icon: <CalendarCheck size={18} /> },
    { id: 'rush-timeline' as PageId, label: 'Rush Timeline', icon: <TrendingUp size={18} /> },
    { id: 'context-availability' as PageId, label: 'Context & Availability', icon: <MapPin size={18} /> },
    { id: 'waste-diagnosis' as PageId, label: 'Waste Diagnosis', icon: <Stethoscope size={18} /> },
    { id: 'kitchen-simulation' as PageId, label: 'Kitchen Live Simulation', icon: <Flame size={18} /> },
    { id: 'menu-analytics' as PageId, label: 'Menu Analytics', icon: <PieChart size={18} /> },
    { id: 'evaluation' as PageId, label: 'Evaluation', icon: <Award size={18} /> },
    { id: 'agent-trace' as PageId, label: 'Agent Trace', icon: <Cpu size={18} /> },
    { id: 'settings-data' as PageId, label: 'Settings & Data', icon: <Settings size={18} /> },
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

          <div className="brand-logo" onClick={() => onNavigate('overview')}>
            <span className="brand-icon">🌱</span>
            <div className="brand-text">
              <span className="brand-title">Food Waste Optimizer</span>
              <span className="brand-subtitle">Autonomous Mess System • Person C</span>
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
              <option value="breakfast">Breakfast (07:00–10:00)</option>
              <option value="lunch">Lunch (12:00–14:30)</option>
              <option value="snacks">Snacks (16:00–18:00)</option>
              <option value="dinner">Dinner (19:00–21:30)</option>
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

          <div className="synthetic-pill" title="Synthetic records only">
            <AlertTriangle size={13} />
            <span>Synthetic Mode</span>
          </div>
        </div>
      </header>

      {/* Main Body with Sidebar + Content */}
      <div className="app-container">
        {/* Sidebar Navigation */}
        <nav className={`sidebar ${mobileMenuOpen ? 'sidebar--open' : ''}`}>
          <div className="sidebar-section-title">DASHBOARD NAVIGATION</div>
          <ul className="nav-list">
            {navItems.map((item) => {
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
                <span>Model:</span>
                <code>context-rf-v4</code>
              </div>
              <div className="meta-row">
                <span>Scenario:</span>
                <code>synthetic_v1</code>
              </div>
              <div className="meta-row">
                <span>Seed:</span>
                <code>42</code>
              </div>
            </div>
          </div>
        </nav>

        {/* Content Area */}
        <main className="main-content">
          <div className="page-wrapper">
            <SyntheticBanner />
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};
