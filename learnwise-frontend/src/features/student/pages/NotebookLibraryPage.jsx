import React, { useState, useCallback, useEffect } from 'react';
import { Plus, Search, Filter, Grid, List, Loader2, MoreVertical, Edit2, Trash2, FileText, Music, Video, Image as ImageIcon, Link as LinkIcon, Sparkles, ChevronDown, ChevronUp, Clock, Check, X } from 'lucide-react';
import { Button, PageHeader } from '../../../components/shared/Primitives';
import { AppShell } from '../../../layouts/AppShell';
import { notebooksApi } from '../../../api/notebooks.api';
import { isBackendApiEnabled } from '../../../api/client';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const demoNotebooks = [
  { id: 'nb-1', title: 'Neural Networks Research', updated_at: '2 hours ago', source_count: 5, description: 'Papers and notes on backpropagation and transformers' },
  { id: 'nb-2', title: 'MLOps Learning Path', updated_at: 'Yesterday', source_count: 3, description: 'Course materials for production ML systems' },
  { id: 'nb-3', title: 'AI Safety Reading Group', updated_at: '3 days ago', source_count: 8, description: 'Alignment papers and discussion notes' },
];

export function NotebookLibraryPage() {
  const queryClient = useQueryClient();
  const [view, setView] = useState('grid');
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState('updated');
  const [creating, setCreating] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');

  const query = useQuery({
    queryKey: ['notebooks'],
    queryFn: notebooksApi.list,
    enabled: isBackendApiEnabled,
  });

  const createMutation = useMutation({
    mutationFn: notebooksApi.create,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['notebooks'] }); setCreating(false); setNewTitle(''); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }) => notebooksApi.update(id, payload),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['notebooks'] }); setEditingId(null); },
  });

  const deleteMutation = useMutation({
    mutationFn: notebooksApi.delete,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notebooks'] }),
  });

  const notebooks = isBackendApiEnabled ? (query.data?.results || query.data || []) : demoNotebooks;
  const filtered = notebooks.filter(n => n.title.toLowerCase().includes(search.toLowerCase()));

  const handleCreate = (e) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    createMutation.mutate({ title: newTitle.trim() });
  };

  const handleUpdate = (id) => {
    if (!editTitle.trim()) return;
    updateMutation.mutate({ id, payload: { title: editTitle.trim() } });
  };

  const handleDelete = (id) => {
    if (window.confirm('Delete this notebook?')) deleteMutation.mutate(id);
  };

  return (
    <AppShell>
      <PageHeader eyebrow="Notebooks" title="Your research workspaces" description="Organize sources, chat with your documents, and generate insights." action={<Button onClick={() => setCreating(true)}><Plus size={15} /> New Notebook</Button>} />
      
      {creating && (
        <form onSubmit={handleCreate} className="create-notebook-form">
          <input type="text" value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="Notebook title…" autoFocus required />
          <div className="form-actions">
            <Button type="submit" disabled={createMutation.isPending}><Plus size={14} />{createMutation.isPending ? ' Creating…' : ' Create'}</Button>
            <Button type="button" variant="secondary" onClick={() => setCreating(false)}>Cancel</Button>
          </div>
        </form>
      )}

      <div className="notebook-toolbar">
        <div className="search-box">
          <Search size={16} />
          <input type="text" placeholder="Search notebooks…" value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <div className="toolbar-right">
          <select value={sort} onChange={e => setSort(e.target.value)} className="sort-select">
            <option value="updated">Recently updated</option>
            <option value="created">Oldest first</option>
            <option value="title">Alphabetical</option>
            <option value="sources">Most sources</option>
          </select>
          <div className="view-toggle">
            <button className={view === 'grid' ? 'active' : ''} onClick={() => setView('grid')} aria-label="Grid view"><Grid size={16} /></button>
            <button className={view === 'list' ? 'active' : ''} onClick={() => setView('list')} aria-label="List view"><List size={16} /></button>
          </div>
        </div>
      </div>

      {isBackendApiEnabled && query.isLoading ? (
        <div className="notebooks-loading"><Loader2 size={24} className="spin" /> Loading notebooks…</div>
      ) : filtered.length === 0 ? (
        <div className="notebooks-empty">
          <FileText size={48} />
          <h3>{search ? 'No matching notebooks' : 'No notebooks yet'}</h3>
          <p>{search ? 'Try a different search term' : 'Create your first notebook to start organizing research'}</p>
          {!search && <Button onClick={() => setCreating(true)}><Plus size={15} /> Create Notebook</Button>}
        </div>
      ) : view === 'grid' ? (
        <div className="notebooks-grid">
          {filtered.map(notebook => (
            <NotebookCard key={notebook.id} notebook={notebook} editingId={editingId} editTitle={editTitle} setEditTitle={setEditTitle} setEditingId={setEditingId} onUpdate={handleUpdate} onDelete={handleDelete} />
          ))}
        </div>
      ) : (
        <div className="notebooks-list">
          {filtered.map(notebook => (
            <NotebookRow key={notebook.id} notebook={notebook} editingId={editingId} editTitle={editTitle} setEditTitle={setEditTitle} setEditingId={setEditingId} onUpdate={handleUpdate} onDelete={handleDelete} />
          ))}
        </div>
      )}
    </AppShell>
  );
}

function NotebookCard({ notebook, editingId, editTitle, setEditTitle, setEditingId, onUpdate, onDelete }) {
  const isEditing = editingId === notebook.id;
  return (
    <article className={`notebook-card ${isEditing ? 'editing' : ''}`}>
      {isEditing ? (
        <form onSubmit={e => { e.preventDefault(); onUpdate(notebook.id); }} className="card-edit-form">
          <input value={editTitle} onChange={e => setEditTitle(e.target.value)} autoFocus />
          <div className="edit-actions">
            <Button type="submit" size="sm"><Check size={12} /></Button>
            <Button type="button" variant="ghost" size="sm" onClick={() => setEditingId(null)}><X size={12} /></Button>
          </div>
        </form>
      ) : (
        <>
          <div className="card-header">
            <FileText size={24} className="notebook-icon" />
            <div className="card-menu">
              <button className="icon-button" onClick={() => setEditTitle(notebook.title) || setEditingId(notebook.id)} aria-label="Rename"><Edit2 size={14} /></button>
              <button className="icon-button" onClick={() => onDelete(notebook.id)} aria-label="Delete"><Trash2 size={14} /></button>
            </div>
          </div>
          <h3 className="notebook-title">{notebook.title}</h3>
          {notebook.description && <p className="notebook-description">{notebook.description}</p>}
          <div className="card-meta">
            <span><Sparkles size={12} /> {notebook.source_count || 0} sources</span>
            <span><Clock size={12} /> {notebook.updated_at}</span>
          </div>
          <div className="card-action">
            <Button onClick={() => window.location.href = `/student/notebooks/${notebook.id}`}>Open</Button>
          </div>
        </>
      )}
    </article>
  );
}

function NotebookRow({ notebook, editingId, editTitle, setEditTitle, setEditingId, onUpdate, onDelete }) {
  const isEditing = editingId === notebook.id;
  return (
    <div className={`notebook-row ${isEditing ? 'editing' : ''}`}>
      {isEditing ? (
        <form onSubmit={e => { e.preventDefault(); onUpdate(notebook.id); }} className="row-edit-form">
          <input value={editTitle} onChange={e => setEditTitle(e.target.value)} autoFocus />
          <div className="edit-actions">
            <Button type="submit" size="sm"><Check size={12} /></Button>
            <Button type="button" variant="ghost" size="sm" onClick={() => setEditingId(null)}><X size={12} /></Button>
          </div>
        </form>
      ) : (
        <>
          <div className="row-main">
            <FileText size={20} className="notebook-icon" />
            <div className="row-info">
              <h4>{notebook.title}</h4>
              <p>{notebook.description || 'No description'}</p>
            </div>
          </div>
          <div className="row-meta">
            <span>{notebook.source_count || 0} sources</span>
            <span>{notebook.updated_at}</span>
          </div>
          <div className="row-actions">
            <Button variant="secondary" size="sm" onClick={() => window.location.href = `/student/notebooks/${notebook.id}`}>Open</Button>
            <button className="icon-button" onClick={() => setEditTitle(notebook.title) || setEditingId(notebook.id)} aria-label="Rename"><Edit2 size={14} /></button>
            <button className="icon-button" onClick={() => onDelete(notebook.id)} aria-label="Delete"><Trash2 size={14} /></button>
          </div>
        </>
      )}
    </div>
  );
}

export default NotebookLibraryPage;