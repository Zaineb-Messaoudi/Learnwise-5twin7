import React from 'react';
import { AudioLines, BookOpen, CheckSquare, FileDown, Headphones, ListChecks, Network, Sparkles } from 'lucide-react';

const tools = [
  { label: 'Audio overview', detail: 'A two-host discussion script', icon: Headphones, kind: 'audio_overview' },
  { label: 'Study guide', detail: 'Key ideas and definitions', icon: BookOpen, kind: 'study_guide' },
  { label: 'Mind map', detail: 'Connect related concepts', icon: Network, kind: 'mind_map' },
  { label: 'Flashcards', detail: 'Review with active recall', icon: CheckSquare, kind: 'flashcards' },
  { label: 'Quiz', detail: 'Check your understanding', icon: ListChecks, kind: 'quiz' },
  { label: 'Briefing doc', detail: 'Summarize the essentials', icon: FileDown, kind: 'briefing_doc' },
];

export function StudioPanel({ onAudio, onCreate = () => {}, artifacts = [], creating = false, error = '' }) {
  return <section className="notebook-studio" aria-labelledby="studio-heading">
    <div className="notebook-section-head"><div><span className="eyebrow">STUDIO</span><h2 id="studio-heading">Create from sources</h2></div><Sparkles size={17}/></div>
    <p className="notebook-muted">Turn your source set into a new way to learn.</p>
    <div className="studio-grid">{tools.map(({ label, detail, icon: Icon, kind }) => <button type="button" key={label} disabled={creating} onClick={() => kind === 'audio_overview' && onAudio ? onAudio() : onCreate(kind)}>
      <span className="studio-tool-icon"><Icon size={17}/></span><span><b>{label}</b><small>{detail}</small></span>
    </button>)}</div>
    {error && <p className="upload-error" role="alert">{error}</p>}
    {creating && <p className="notebook-muted" role="status">Creating from selected sources…</p>}
    {artifacts.length > 0 && <div className="studio-artifacts"><div className="studio-artifacts-title"><AudioLines size={15}/><span>Created in this notebook</span></div>{artifacts.map((artifact, index) => <article className="studio-artifact" key={artifact.id || `${artifact.title}-${index}`}><span className="studio-artifact-icon"><FileDown size={15}/></span><span><b>{artifact.title}</b><small>{artifact.status || 'Generated from selected sources'}</small>{artifact.content && <p>{artifact.content}</p>}</span></article>)}</div>}
  </section>;
}
