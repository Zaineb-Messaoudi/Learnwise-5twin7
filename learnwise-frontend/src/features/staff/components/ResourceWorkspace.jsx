import React, { useEffect, useMemo, useState } from 'react';
import { ArrowRight, Check, Plus, Search, X } from 'lucide-react';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader } from '../../../components/shared/Primitives';
import { isBackendApiEnabled } from '../../../api/client';

export function ResourceWorkspace({ role, title, description, resource, items, canCreate = true }) {
  const storageKey = `learnwise:staff-records:${role}:${resource}`;
  const [records, setRecords] = useState(() => {
    try {
      const saved = JSON.parse(window.localStorage.getItem(storageKey) || 'null');
      if (Array.isArray(saved)) return saved.map(item => ({ ...item, icon: items.find(seed => seed.name === item.name)?.icon || <Plus size={18} /> }));
    } catch { /* Use the supplied sample data if stored data is malformed. */ }
    return items;
  });
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('All');
  const [selected, setSelected] = useState(null);
  const [storageWarning, setStorageWarning] = useState(false);
  useEffect(() => {
    if (isBackendApiEnabled) return;
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(records.map(({ icon, ...record }) => record)));
      setStorageWarning(false);
    } catch {
      setStorageWarning(true);
    }
  }, [records, storageKey]);
  const shown = useMemo(() => records.filter(item => item.name.toLowerCase().includes(query.toLowerCase()) && (filter === 'All' || item.status === filter)), [records, query, filter]);
  if (isBackendApiEnabled) return <AppShell role={role}><PageHeader eyebrow={`${role} workspace`} title={title} description={description}/><p className="state-panel">No {resource} records to show yet.</p></AppShell>;
  const create = () => {
    const draft = { name: `Untitled ${resource} ${records.filter(item => item.name.startsWith(`Untitled ${resource}`)).length + 1}`, meta: 'New draft · Stored in this browser', status: 'Draft', icon: <Plus size={18} /> };
    setRecords(current => [draft, ...current]);
    setSelected(draft);
  };
  const markReviewed = () => {
    if (!selected) return;
    const reviewed = { ...selected, status: 'Reviewed', meta: `${selected.meta} · Reviewed` };
    setRecords(current => current.map(item => item.name === selected.name ? reviewed : item));
    setSelected(null);
  };
  return <AppShell role={role}><PageHeader eyebrow={`${role} workspace`} title={title} description={description} action={canCreate ? <Button onClick={create}><Plus size={16} /> Create {resource}</Button> : null} />{selected && <section className="resource-detail" role="region" aria-label={`${selected.name} details`} aria-live="polite"><div><span className="eyebrow">WORKSPACE ITEM</span><h2>{selected.name}</h2><p>{selected.meta}</p></div><button type="button" className="icon-button" aria-label="Close details" onClick={() => setSelected(null)}><X size={17} /></button><Button variant="secondary" onClick={markReviewed} disabled={selected.status === 'Reviewed'}><Check size={15} /> {selected.status === 'Reviewed' ? 'Reviewed' : 'Mark reviewed'}</Button></section>}{storageWarning && <p className="state-panel" role="status">Browser storage is unavailable. Changes will last only until you leave this page.</p>}<div className="toolbar"><div className="segmented" role="group" aria-label={`${resource} status`}>{['All', 'Active', 'Draft', 'Reviewed'].map(option => <button type="button" className={filter === option ? 'selected' : ''} aria-pressed={filter === option} onClick={() => setFilter(option)} key={option}>{option}</button>)}</div><label className="search-field"><Search size={16} /><span className="sr-only">Search {resource}</span><input value={query} onChange={event => setQuery(event.target.value)} placeholder={`Search ${resource.toLowerCase()}`} /></label></div><section className="resource-table" aria-label={`${title} list`}>{shown.map((item, index) => <article className="resource-row" key={`${item.name}-${index}`}><div className="resource-main"><span className="resource-icon">{item.icon}</span><span><b>{item.name}</b><small>{item.meta}</small></span></div><span className={`resource-status ${item.status.toLowerCase()}`}>{item.status}</span><button type="button" className="icon-button" aria-label={`Open ${item.name}`} onClick={() => setSelected(item)}><ArrowRight size={16} /></button></article>)}{!shown.length && <p className="empty-search" role="status">No {resource.toLowerCase()} match this filter.</p>}</section></AppShell>;
}
