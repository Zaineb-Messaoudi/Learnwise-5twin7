import React, { useEffect, useMemo, useState } from 'react';
import { AlertCircle, ArrowRight, BookOpen, FileText, Headphones, LoaderCircle, RotateCcw, Save, Sparkles, Upload } from 'lucide-react';
import { Link } from 'react-router-dom';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader } from '../../../components/shared/Primitives';
import { coursesApi } from '../../../api/courses.api';
import { isBackendApiEnabled } from '../../../api/client';
import { materialsApi } from '../../../api/materials.api';
import './content-management.css';

const demoCourses = [{ id: 'neural-networks', title: 'AI & Machine Learning' }, { id: 'design-thinking', title: 'Design Thinking Foundations' }];
const demoMaterials = [
  { id: 'demo-pdf', title: 'Neural networks basics.pdf', kind: 'document', status: 'completed', progress: 100, updated_at: 'Today' },
  { id: 'demo-audio', title: 'Lecture 04 · Backpropagation.mp3', kind: 'audio', status: 'processing', progress: 68, updated_at: 'Today' },
  { id: 'demo-failed', title: 'Office hours recording.wav', kind: 'audio', status: 'failed', progress: 100, error_message: 'Audio could not be decoded. Try uploading an MP3 or WAV file again.', updated_at: 'Yesterday' },
];
const statusLabels = { queued: 'Queued', processing: 'Processing', completed: 'Ready to review', failed: 'Needs attention' };

export function ContentManagementPage({ mode = 'materials' }) {
  const [courses, setCourses] = useState(isBackendApiEnabled ? [] : demoCourses);
  const [courseId, setCourseId] = useState(isBackendApiEnabled ? '' : demoCourses[0].id);
  const [materials, setMaterials] = useState(isBackendApiEnabled ? [] : demoMaterials);
  const [selectedId, setSelectedId] = useState(null);
  const [content, setContent] = useState(null);
  const [loading, setLoading] = useState(isBackendApiEnabled);
  const [contentLoading, setContentLoading] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [saving, setSaving] = useState(false);
  const selected = materials.find(material => material.id === selectedId);

  useEffect(() => {
    if (!isBackendApiEnabled) return undefined;
    let active = true;
    coursesApi.list().then(response => {
      if (!active) return;
      const items = Array.isArray(response) ? response : response.results || [];
      setCourses(items);
      setCourseId(items[0]?.id || '');
    }).catch(() => { if (active) setError('Could not load courses. Check your connection and retry.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!isBackendApiEnabled || !courseId) return undefined;
    let active = true;
    setLoading(true);
    setError('');
    materialsApi.list(courseId).then(response => {
      if (!active) return;
      setMaterials(Array.isArray(response) ? response : response.results || []);
    }).catch(() => { if (active) setError('Could not load materials for this course. Retry the request.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [courseId]);

  useEffect(() => {
    if (!selected || !isBackendApiEnabled || selected.status !== 'completed') {
      if (!isBackendApiEnabled && selected) {
        setContent(mode === 'transcriptions'
          ? `This is a sample transcript for ${selected.title}. Review technical terms, speaker turns, and timestamps before students use this material.`
          : `Key ideas from ${selected.title}\n\n• Neural networks learn by updating weights from prediction error.\n• Backpropagation carries that error through each layer.\n• Practice retrieval to check whether the explanation is clear.`);
      }
      return undefined;
    }
    let active = true;
    setContentLoading(true);
    setError('');
    const loader = mode === 'transcriptions' ? materialsApi.transcription(selected.id) : materialsApi.summary(selected.id);
    loader.then(result => { if (active) setContent(mode === 'transcriptions' ? result.text || '' : result.text || ''); })
      .catch(() => { if (active) setError(`Could not load this ${mode === 'transcriptions' ? 'transcript' : 'summary'}. Retry opening the material.`); })
      .finally(() => { if (active) setContentLoading(false); });
    return () => { active = false; };
  }, [selectedId, mode]);

  const visibleMaterials = useMemo(() => materials.filter(item => mode === 'materials' || (mode === 'transcriptions' ? item.kind === 'audio' : item.status === 'completed')), [materials, mode]);
  const selectMaterial = item => { setSelectedId(item.id); setContent(null); setNotice(''); };
  const save = async () => {
    if (!selected || content == null) return;
    setSaving(true);
    setError('');
    try {
      if (isBackendApiEnabled) {
        if (mode === 'transcriptions') await materialsApi.updateTranscription(selected.id, content);
        else await materialsApi.updateSummary(selected.id, content);
      }
      setNotice('Review updated.');
    } catch {
      setError('Could not save your changes. Your text remains here; please try again.');
    } finally { setSaving(false); }
  };
  const retryProcessing = async item => {
    setError('');
    try {
      if (isBackendApiEnabled) {
        await materialsApi.retryProcessing(item.id);
        const updated = await materialsApi.processingStatus(item.id);
        setMaterials(current => current.map(row => row.id === item.id ? { ...row, ...updated } : row));
      } else {
        setMaterials(current => current.map(row => row.id === item.id ? { ...row, status: 'processing', progress: 20 } : row));
      }
    } catch {
      setError('Could not restart processing. Check the material and retry.');
    }
  };
  const regenerate = async () => {
    if (!selected) return;
    setSaving(true);
    setError('');
    try {
      const result = isBackendApiEnabled ? await materialsApi.regenerateSummary(selected.id) : { text: `Regenerated example summary for ${selected.title}.\n\nReview these key ideas and confirm they match the course source before publishing.` };
      if (result.text) setContent(result.text);
      setNotice(isBackendApiEnabled ? 'Summary generation started.' : 'A sample summary is ready to review.');
    } catch {
      setError('Could not regenerate the summary. Your current draft has not been changed.');
    } finally { setSaving(false); }
  };
  const title = mode === 'transcriptions' ? 'Transcription review' : mode === 'summaries' ? 'Course summaries' : 'Course materials';
  return <AppShell role="teacher"><PageHeader eyebrow="Content management · Teacher workspace" title={title} description="Prepare course sources, review AI-generated text, and resolve processing issues before learners see them." action={<Link className="button" to="/teacher/materials/upload"><Upload size={15}/> Upload material</Link>} />
    <section className="content-management">
      <div className="content-toolbar">
        <label>Course<select value={courseId} onChange={event => { setCourseId(event.target.value); setSelectedId(null); setContent(null); }} disabled={loading || !courses.length}><option value="">Choose a course</option>{courses.map(course => <option key={course.id} value={course.id}>{course.title}</option>)}</select></label>
        <nav aria-label="Content review"><Link className={mode === 'materials' ? 'active' : ''} to="/teacher/materials">Materials</Link><Link className={mode === 'transcriptions' ? 'active' : ''} to="/teacher/transcriptions">Transcripts</Link><Link className={mode === 'summaries' ? 'active' : ''} to="/teacher/summaries">Summaries</Link></nav>
      </div>
      {isBackendApiEnabled && <p className="content-mode-note"><span/> Live backend mode · status and review content come from content_management.</p>}
      {!isBackendApiEnabled && <p className="content-mode-note"><span/> Sample content · uploads and generated text are not stored on a server.</p>}
      {error && <p className="content-error" role="alert"><AlertCircle size={16}/>{error}</p>}
      <div className="content-review-layout">
        <section className="content-material-list" aria-label="Course materials">
          {loading ? <p className="content-state"><LoaderCircle size={18}/> Loading course materials…</p> : visibleMaterials.length ? visibleMaterials.map(item => <article className={`content-material ${selectedId === item.id ? 'selected' : ''}`} key={item.id}>
            <button type="button" className="content-material-open" onClick={() => selectMaterial(item)}><span className="content-file-icon">{item.kind === 'audio' ? <Headphones size={18}/> : <FileText size={18}/>}</span><span className="content-material-copy"><b>{item.title || item.file_name}</b><small>{item.kind === 'audio' ? 'Audio material' : 'Course document'} · {item.updated_at || statusLabels[item.status] || item.status}</small></span><ArrowRight size={16}/></button>
            <div className="content-status-row"><span className={`content-status ${item.status}`}>{statusLabels[item.status] || item.status}</span>{item.status !== 'completed' && <span>{item.progress || 0}%</span>}</div>
            {item.status !== 'completed' && <div className="content-progress"><span style={{ width: `${item.progress || 0}%` }}/></div>}
            {item.status === 'failed' && <div className="content-failure"><p>{item.error_message || 'Processing did not complete.'}</p><button type="button" onClick={() => void retryProcessing(item)}><RotateCcw size={13}/> Retry processing</button></div>}
          </article>) : <p className="content-state"><BookOpen size={18}/> No materials yet. Upload a course PDF or audio file to begin.</p>}
        </section>
        <section className="content-review" aria-label="Review generated content">
          {!selected ? <div className="content-review-empty"><Sparkles size={24}/><h2>Review before sharing</h2><p>Select a processed course item to check its transcript or summary. Failed and in-progress items show their next action.</p></div>
            : selected.status !== 'completed' ? <div className="content-review-empty"><LoaderCircle size={24}/><h2>{statusLabels[selected.status] || selected.status}</h2><p>{selected.status === 'failed' ? 'Resolve the processing error, then retry. Review text becomes available after processing completes.' : 'Transcription and summary will appear here when processing is complete.'}</p></div>
            : <><div className="content-review-header"><div><span className="eyebrow">{mode === 'transcriptions' ? 'WHISPER TRANSCRIPTION' : 'AI-GENERATED SUMMARY'}</span><h2>{selected.title || selected.file_name}</h2></div>{mode === 'summaries' && <Button variant="secondary" onClick={() => void regenerate()} disabled={saving}><Sparkles size={14}/> Regenerate</Button>}</div>
              {contentLoading ? <p className="content-state"><LoaderCircle size={18}/> Loading review content…</p> : <><label className="content-editor-label" htmlFor="content-review-text">{mode === 'transcriptions' ? 'Transcript text' : 'Summary text'}</label><textarea id="content-review-text" value={content || ''} onChange={event => setContent(event.target.value)} rows={12} placeholder="Processed content will appear here…" /><div className="content-review-actions"><span role="status">{notice || (mode === 'transcriptions' ? 'Correct recognition errors before students use this transcript.' : 'Check accuracy and clarity against the original source.')}</span><Button onClick={() => void save()} disabled={saving || content == null}><Save size={14}/>{saving ? 'Saving…' : 'Save review'}</Button></div></>}
            </>}
        </section>
      </div>
    </section>
  </AppShell>;
}
