import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeft, BookOpen, FileText, HelpCircle, ListChecks, Music, Link as LinkIcon, Send, Sparkles, Loader2, AlertCircle, Quote, Check } from 'lucide-react';
import { useParams, useNavigate } from 'react-router-dom';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader } from '../../../components/shared/Primitives';
import { ErrorState, LoadingState } from '../../../components/ui/States';
import { coursesApi } from '../../../api/courses.api';
import { materialsApi } from '../../../api/materials.api';
import { assistantApi } from '../../../api/assistant.api';
import { quizzesApi } from '../../../api/quizzes.api';
import { isBackendApiEnabled } from '../../../api/client';

const demoCourse = { id: 'course-7', title: 'Neural Networks', description: 'Course overview' };
const demoMaterials = [{ id: 'material-4', title: 'Backpropagation.pdf', status: 'completed', kind: 'document' }];

function recordsFrom(response) {
  return Array.isArray(response) ? response : response?.results || [];
}

export function NotebookWorkspacePage() {
  const { id = 'course-7' } = useParams();
  const navigate = useNavigate();
  const [course, setCourse] = useState(null);
  const [materials, setMaterials] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(isBackendApiEnabled);
  const [quizDraft, setQuizDraft] = useState(null);
  const [generatingQuiz, setGeneratingQuiz] = useState(false);
  const [selectedMaterialIds, setSelectedMaterialIds] = useState([]);
  const sessionPromiseRef = useRef(null);

  useEffect(() => {
    if (!isBackendApiEnabled) {
      setCourse(demoCourse);
      setMaterials(demoMaterials);
      setSelectedMaterialIds(demoMaterials.map(m => m.id));
      setLoading(false);
      return;
    }
    let active = true;
    setLoading(true);
    Promise.all([coursesApi.detail(id), materialsApi.list(id)])
      .then(([courseResponse, materialsResponse]) => {
        if (!active) return null;
        const loadedCourse = courseResponse;
        const loadedMaterials = recordsFrom(materialsResponse);
        setCourse(loadedCourse);
        setMaterials(loadedMaterials);
        setSelectedMaterialIds(loadedMaterials.map(m => m.id));
        const sessionPromise = assistantApi.createSession({ title: loadedCourse?.title || 'Notebook', course_id: id });
        sessionPromiseRef.current = sessionPromise;
        return sessionPromise;
      })
      .then(session => {
        if (!active || !session) return;
        setSessionId(session.id);
      })
      .catch(() => { if (active) setError('Could not load this notebook. Retry.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id]);

  const materialIds = useMemo(() => selectedMaterialIds.length ? selectedMaterialIds : materials.map(m => m.id), [selectedMaterialIds, materials]);

  const ask = async (question) => {
    const text = (question || input).trim();
    if (!text || sending) return;
    setError('');
    setInput('');
    if (!isBackendApiEnabled) {
      setMessages(current => [...current, { from: 'user', text }, { from: 'ai', text: 'Gradient descent updates model weights.', citations: [{ id: 'material-4', title: 'Backpropagation.pdf', page: 4 }] }]);
      return;
    }
    setSending(true);
    setMessages(current => [...current, { from: 'user', text }]);
    try {
      let activeSessionId = sessionId;
      if (!activeSessionId && sessionPromiseRef.current) {
        const session = await sessionPromiseRef.current;
        activeSessionId = session?.id;
        setSessionId(activeSessionId);
      }
      if (!activeSessionId) {
        throw new Error('The assistant session is not ready yet. Wait for the notebook to load.');
      }
      const response = await assistantApi.ask(activeSessionId, { content: text, course_id: id, material_ids: materialIds });
      const message = response.assistant_message || response;
      setMessages(current => [...current, { from: 'ai', text: message.content || '', citations: message.citations || [] }]);
    } catch (cause) {
      setError(cause.message || 'Could not get an answer. Try again.');
      setMessages(current => current.slice(0, -1));
    } finally {
      setSending(false);
    }
  };

  const generateQuiz = async () => {
    if (!isBackendApiEnabled) {
      setQuizDraft({ title: 'Generated quiz', questions: [{ prompt: 'What is gradient descent?' }] });
      return;
    }
    setGeneratingQuiz(true);
    setError('');
    try {
      const result = await quizzesApi.generate({
        course_id: id,
        material_ids: materialIds,
        kind: 'quiz',
        question_count: 5,
        difficulty: 'medium',
      });
      const draft = result.result || result;
      setQuizDraft(draft);
    } catch (cause) {
      setError(cause.message || 'Could not generate a quiz draft.');
    } finally {
      setGeneratingQuiz(false);
    }
  };

  const toggleMaterial = (materialId) => {
    setSelectedMaterialIds(current => current.includes(materialId) ? current.filter(m => m !== materialId) : [...current, materialId]);
  };

  if (loading) return <AppShell><PageHeader eyebrow="Notebook" title="Loading notebook"/><LoadingState label="Loading course materials"/></AppShell>;
  if (error && !course) return <AppShell><PageHeader eyebrow="Notebook" title="This notebook could not be opened."/><ErrorState message={error} action={<Button onClick={() => window.location.reload()}>Retry</Button>}/></AppShell>;

  return (
    <AppShell>
      <PageHeader
        eyebrow="Notebook"
        title={course?.title || 'Notebook'}
        description={course?.description || 'Ask questions grounded in your course materials.'}
        action={<Button variant="secondary" onClick={() => navigate('/student/courses')}><ArrowLeft size={15} /> Back to courses</Button>}
      />

      <div className="notebook-workspace">
        <aside className="sources-panel">
          <div className="panel-header">
            <h3>Course materials</h3>
            <span className="source-count">{materials.length}</span>
          </div>
          <div className="sources-list">
            {materials.map(material => (
              <div key={material.id} className={`source-item ${selectedMaterialIds.includes(material.id) ? 'selected' : ''}`}>
                <button type="button" className="source-select" onClick={() => toggleMaterial(material.id)} aria-pressed={selectedMaterialIds.includes(material.id)}>
                  <span className="source-icon">
                    {material.kind === 'audio' ? <Music size={16} /> : material.kind === 'link' ? <LinkIcon size={16} /> : <FileText size={16} />}
                  </span>
                  <span className="source-info">
                    <strong>{material.title || material.file_name}</strong>
                    <small>{material.kind || 'document'} · {material.status}</small>
                  </span>
                </button>
                {selectedMaterialIds.includes(material.id) && <Check size={14} className="text-lime" />}
              </div>
            ))}
          </div>
          <div className="sources-filter-note">
            <Check size={14} /> {materialIds.length} source{materialIds.length !== 1 ? 's' : ''} selected
          </div>
        </aside>

        <main className="notebook-main">
          <nav className="notebook-tabs">
            <button type="button" className="notebook-tab active"><Send size={16} /> Chat</button>
            <button type="button" className="notebook-tab" onClick={() => void generateQuiz()}><ListChecks size={16} /> Quiz</button>
          </nav>

          {error && <p className="notebook-error" role="alert"><AlertCircle size={15} /> {error}</p>}

          <div className="chat-panel">
            <div className="chat-messages" aria-live="polite">
              {messages.length === 0 ? (
                <div className="chat-empty">
                  <Sparkles size={32} />
                  <h3>Ask anything about {course?.title || 'this course'}</h3>
                  <p>Your answers are grounded in the selected course materials.</p>
                  <div className="chat-suggestions">
                    <button className="suggestion-chip" onClick={() => void ask('What are the key ideas?')}>What are the key ideas?</button>
                    <button className="suggestion-chip" onClick={() => void ask('Explain the main concepts simply')}>Explain simply</button>
                    <button className="suggestion-chip" onClick={() => void ask('Test yourself on this material')}>Test yourself</button>
                  </div>
                </div>
              ) : (
                messages.map((msg, i) => (
                  <div key={i} className={`chat-message ${msg.from}`}>
                    <div className="message-avatar">{msg.from === 'ai' ? <Sparkles size={14} /> : 'You'}</div>
                    <div className="message-body">
                      <p>{msg.text}</p>
                      {msg.citations?.length > 0 && (
                        <div className="citations">
                          <span className="citations-label"><Quote size={12} /> Sources</span>
                          {msg.citations.map((citation, ci) => (
                            <button key={ci} className="citation" type="button">
                              <FileText size={12} />
                              <span>{citation.title || citation.source}{citation.page ? ` · p. ${citation.page}` : ''}</span>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
              {sending && <p className="chat-pending" role="status"><Loader2 size={14} className="spin" /> Thinking…</p>}
            </div>
            <div className="chat-composer">
              <input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void ask(); } }}
                placeholder="Ask about your course materials…"
                disabled={sending}
              />
              <Button onClick={() => void ask()} disabled={sending || !input.trim()}><Send size={15} /></Button>
            </div>
          </div>

          {quizDraft && (
            <div className="quiz-draft">
              <h3><BookOpen size={16} /> {quizDraft.title || 'Generated quiz'}</h3>
              <ol className="quiz-draft-questions">
                {(quizDraft.questions || []).map((question, qi) => (
                  <li key={qi}>{question.prompt || question.text || question.question}</li>
                ))}
              </ol>
            </div>
          )}
          {generatingQuiz && <p className="chat-pending" role="status"><Loader2 size={14} className="spin" /> Generating quiz draft…</p>}
        </main>
      </div>
    </AppShell>
  );
}

export default NotebookWorkspacePage;
