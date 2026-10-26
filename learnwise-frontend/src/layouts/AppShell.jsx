import React, { useState } from 'react';
import { Activity, ArrowRight, BarChart3, Bell, BookOpen, ChevronDown, FolderOpen, Grid2X2, ListChecks, LogOut, Menu, MoreHorizontal, Search, Settings, Sparkles, Sun, Moon, Target, Users, X, Zap, User, Lock } from 'lucide-react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { navAdmin, navStudent, navTeacher } from '../data/mockData';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { authApi } from '../api/auth.api';
import { isBackendApiEnabled } from '../api/client';

const icons = { grid: Grid2X2, book: BookOpen, spark: Sparkles, quiz: ListChecks, target: Target, chart: BarChart3, folder: FolderOpen, users: Users, activity: Activity, user: User, lock: Lock };

function Logo({ dark = false }) {
  return <Link to="/" className={`logo ${dark ? 'logo-dark' : ''}`} aria-label="Learnwise home"><img className="brand-logo-image" src="/assets/learnwise-wordmark.webp" width="150" height="34" alt="Learnwise" /><img className="brand-symbol-image" src="/assets/learnwise-symbol.png" width="44" height="38" alt="" aria-hidden="true" /></Link>;
}

function WorkspaceNav({ role, nav, close }) {
  return <nav id="workspace-navigation" className="side-nav" aria-label="Workspace navigation"><span className="side-label">Workspace</span>{nav.map(item => { const Icon = icons[item.icon]; return <NavLink key={item.path} to={item.path} onClick={close} className={({ isActive }) => `side-link ${isActive ? 'active' : ''}`}><Icon size={17} /><span>{item.label}</span>{item.label === 'AI assistant' && <i className="new-dot" />}</NavLink>; })}<span className="side-label side-label-spaced">Account</span><NavLink to={`/${role}/notifications`} onClick={close} className="side-link"><Bell size={17} /><span>Notifications</span><span className="notification-count">3</span></NavLink><NavLink to={`/${role}/settings`} onClick={close} className="side-link"><Settings size={17} /><span>Settings</span></NavLink></nav>;
}

function AppShell({ role = 'student', children }) {
  const nav = role === 'teacher' ? navTeacher : role === 'admin' ? navAdmin : navStudent;
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { theme, setTheme, dark } = useTheme();
  const { user, logout } = useAuth();
  const displayName = user?.name || (role === 'student' ? 'Sarah Chen' : role === 'teacher' ? 'Maya Chen' : 'Learnwise Admin');
  const initials = displayName.split(/\s+/).filter(Boolean).slice(0, 2).map(part => part[0]).join('').toUpperCase();
  const workspaceName = role === 'student' ? 'Student workspace' : role === 'teacher' ? 'Instructor workspace' : 'Admin workspace';
  const signOut = async () => {
    let remoteSignOutFailed = false;
    if (isBackendApiEnabled) {
      const refresh = window.localStorage.getItem('learnwise:refresh-token');
      try { await authApi.logout(refresh); }
      catch { remoteSignOutFailed = true; }
    }
    logout();
    navigate('/auth/login', { replace: true, state: remoteSignOutFailed ? { notice: 'The server could not revoke the session. Your browser session was cleared.' } : null });
  };
  return <div className="app-shell"><a className="skip-link" href="#workspace-main">Skip to main content</a><aside className={`app-sidebar ${open ? 'open' : ''}`}><div className="sidebar-head"><Logo /><button className="icon-button sidebar-close" onClick={() => setOpen(false)} aria-label="Close navigation"><X size={18} /></button></div><div className="workspace-switch"><div className="workspace-avatar">{initials}</div><div><b>{displayName}</b><span>{workspaceName}</span></div><ChevronDown size={15} /></div><WorkspaceNav role={role} nav={nav} close={() => setOpen(false)} /><div className="sidebar-bottom"><button className="upgrade-card" onClick={() => navigate('/student/assistant')}><span className="upgrade-icon"><Zap size={15} /></span><div><b>Unlock your potential</b><span>Explore AI learning tools</span></div><ArrowRight size={14} /></button><div className="sidebar-user"><div className="avatar">{initials}</div><div><b>{displayName}</b><span>{user?.email || workspaceName}</span></div><button type="button" className="icon-button" aria-label="Sign out" title="Sign out" onClick={() => void signOut()}><LogOut size={16}/></button></div></div></aside><div className="app-main"><header className="app-topbar"><button className="icon-button menu-button" onClick={() => setOpen(true)} aria-label="Open navigation" aria-expanded={open} aria-controls="workspace-navigation"><Menu size={20} /></button><div className="breadcrumb"><span>Workspace</span><span>/</span><b>{location.pathname.split('/').filter(Boolean).slice(-1)[0]?.replaceAll('-', ' ') || 'Overview'}</b></div><div className="top-actions"><button className="icon-button" onClick={() => navigate(`/${role}/search`)} aria-label="Search"><Search size={18} /></button><button className="icon-button" onClick={() => setTheme(dark ? 'light' : 'dark')} aria-label={dark ? 'Use light theme' : 'Use dark theme'} aria-pressed={dark}>{dark ? <Sun size={18} /> : <Moon size={18} />}</button><Link className="icon-button notification-button" to={`/${role}/notifications`} aria-label="Open notifications"><Bell size={18} /><i /></Link><div className="top-avatar">{initials}</div></div></header><main className="app-content" id="workspace-main" tabIndex="-1">{children}</main></div></div>;
}

export { AppShell, Logo };
