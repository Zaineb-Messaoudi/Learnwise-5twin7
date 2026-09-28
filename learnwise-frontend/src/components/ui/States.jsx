import React from 'react';
import { AlertCircle, Inbox, LoaderCircle } from 'lucide-react';
export function LoadingState({ label = 'Loading' }) { return <div role="status" className="state-panel"><LoaderCircle className="spin" size={22}/><span>{label}...</span></div>; }
export function EmptyState({ title, action }) { return <div className="state-panel"><Inbox size={24}/><strong>{title}</strong>{action}</div>; }
export function ErrorState({ message = 'Something went wrong.', action }) { return <div role="alert" className="state-panel error-state"><AlertCircle size={22}/><strong>{message}</strong>{action}</div>; }
