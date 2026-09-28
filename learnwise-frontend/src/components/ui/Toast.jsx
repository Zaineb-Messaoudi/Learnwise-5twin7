import React, { createContext, useContext, useMemo, useState } from 'react';
import { Check, X } from 'lucide-react';
const ToastContext = createContext(null);
export function ToastProvider({ children }) {
    const [items, setItems] = useState([]);
    const notify = (message, tone = 'info') => {
        const id = Date.now();
        setItems(current => [...current, { id, message, tone }]);
        window.setTimeout(() => setItems(current => current.filter(item => item.id !== id)), 3600);
    };
    const value = useMemo(() => ({ notify }), []);
    return <ToastContext.Provider value={value}>{children}<div className="toast-stack" aria-live="polite">{items.map(item => <div className={`toast toast-${item.tone}`} key={item.id}><span>{item.tone === 'success' ? <Check size={14}/> : item.tone === 'error' ? <X size={14}/> : 'i'}</span>{item.message}</div>)}</div></ToastContext.Provider>;
}
export function useToast() { const context = useContext(ToastContext); if (!context)
    throw new Error('useToast must be used within ToastProvider'); return context; }
