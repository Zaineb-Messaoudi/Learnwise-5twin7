import React, { Suspense } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { ProgressSyncProvider } from './contexts/ProgressSyncContext';
import { ToastProvider } from './components/ui/Toast';
import { AccessibilityToolbar } from './components/ui/AccessibilityToolbar';
import { AppErrorBoundary } from './components/system/AppErrorBoundary';
import { RouteBoundary, RouteOverrides } from './routes/AppRoutes';
import './styles/tokens.css';
import './styles.css';
import './styles/new-components.css';
import './accessibility.css';
import './system.css';

const queryClient = new QueryClient();
createRoot(document.getElementById('root')).render(<React.StrictMode><BrowserRouter><QueryClientProvider client={queryClient}><AuthProvider><ThemeProvider><ProgressSyncProvider><ToastProvider><AccessibilityToolbar><AppErrorBoundary><Suspense fallback={<div className="state-panel" role="status">Loading Learnwise…</div>}><RouteBoundary><RouteOverrides /></RouteBoundary></Suspense></AppErrorBoundary></AccessibilityToolbar></ToastProvider></ProgressSyncProvider></ThemeProvider></AuthProvider></QueryClientProvider></BrowserRouter></React.StrictMode>);
