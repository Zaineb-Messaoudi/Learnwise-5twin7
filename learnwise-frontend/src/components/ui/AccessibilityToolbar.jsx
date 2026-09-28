import React, { useEffect, useRef, useState } from 'react';
import { Accessibility, Check, Eye, Focus, Minus, Type, X } from 'lucide-react';
import './accessibility-toolbar.css';

const defaults = { highContrast: false, calm: false, largeText: false, readableFont: false, focusGuide: false };

export function AccessibilityToolbar({ children }) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef(null);
  const closeRef = useRef(null);
  const [settings, setSettings] = useState(() => {
    try { return { ...defaults, ...JSON.parse(window.localStorage.getItem('learnwise-accessibility') || '{}') }; } catch { return defaults; }
  });

  useEffect(() => {
    const root = document.documentElement;
    [['a11y-high-contrast', settings.highContrast], ['a11y-calm', settings.calm], ['a11y-large-text', settings.largeText], ['a11y-readable-font', settings.readableFont], ['a11y-focus-guide', settings.focusGuide]].forEach(([name, enabled]) => root.classList.toggle(name, enabled));
    window.localStorage.setItem('learnwise-accessibility', JSON.stringify(settings));
  }, [settings]);

  useEffect(() => {
    if (!open) return undefined;
    closeRef.current?.focus();
    const onKeyDown = event => {
      if (event.key === 'Escape') { setOpen(false); triggerRef.current?.focus(); return; }
      if (event.key !== 'Tab') return;
      const panel = document.getElementById('a11y-panel');
      const focusable = panel ? [...panel.querySelectorAll('button, input, select, textarea, a[href]')].filter(element => !element.disabled) : [];
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [open]);

  const toggle = key => setSettings(current => ({ ...current, [key]: !current[key] }));
  const close = () => { setOpen(false); triggerRef.current?.focus(); };
  return <>{children}<div className="a11y-tools"><button ref={triggerRef} type="button" className="a11y-trigger" aria-expanded={open} aria-controls="a11y-panel" aria-label="Open accessibility preferences" onClick={() => setOpen(current => !current)}><Accessibility size={18}/><span>Accessibility</span></button>{open && <section id="a11y-panel" className="a11y-panel" role="dialog" aria-modal="true" aria-labelledby="a11y-title" aria-describedby="a11y-intro"><div className="a11y-panel-head"><div><span className="a11y-overline">Personalise your experience</span><h2 id="a11y-title">Accessibility preferences</h2></div><button ref={closeRef} type="button" className="a11y-close" onClick={close} aria-label="Close accessibility preferences"><X size={17}/></button></div><p id="a11y-intro" className="a11y-intro">These settings stay on this device and work across the platform. They supplement, not replace, your browser and operating-system preferences.</p><div className="a11y-options"><Preference icon={<Eye size={17}/>} label="High contrast" hint="Increase contrast and reduce color dependence" checked={settings.highContrast} onClick={() => toggle('highContrast')} /><Preference icon={<Focus size={17}/>} label="Calm mode" hint="Reduce decorative motion and visual density" checked={settings.calm} onClick={() => toggle('calm')} /><Preference icon={<Type size={17}/>} label="Larger text" hint="Increase readable type without breaking layout" checked={settings.largeText} onClick={() => toggle('largeText')} /><Preference icon={<Type size={17}/>} label="Readable font" hint="Use a more open, dyslexia-friendly letterform" checked={settings.readableFont} onClick={() => toggle('readableFont')} /><Preference icon={<Focus size={17}/>} label="Focus guide" hint="Highlight the item currently receiving keyboard focus" checked={settings.focusGuide} onClick={() => toggle('focusGuide')} /></div><button type="button" className="a11y-reset" onClick={() => setSettings(defaults)}><Minus size={14}/> Reset preferences</button></section>}</div></>;
}

function Preference({ icon, label, hint, checked, onClick }) {
  return <button type="button" className={`a11y-preference ${checked ? 'selected' : ''}`} aria-pressed={checked} onClick={onClick}><span className="a11y-preference-icon">{icon}</span><span><b>{label}</b><small>{hint}</small></span><span className="a11y-check" aria-hidden="true">{checked && <Check size={13}/>}</span></button>;
}
