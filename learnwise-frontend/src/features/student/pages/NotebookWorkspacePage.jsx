import React, { useEffect, useState } from 'react';
import { ArrowLeft, Check, MoreHorizontal, Share2, Sparkles } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader } from '../../../components/shared/Primitives';
import { ErrorState, LoadingState } from '../../../components/ui/States';
import { assistantApi } from '../../../api/assistant.api';
import { coursesApi } from '../../../api/courses.api';
import { materialsApi } from '../../../api/materials.api';
import { quizzesApi } from '../../../api/quizzes.api';
import { isBackendApiEnabled } from '../../../api/client';
import { getNotebooks } from '../data/notebookStore';
import { NotebookChat } from '../components/notebook/NotebookChat';
import { SourceList } from '../components/notebook/SourceList';
import { StudioPanel } from '../components/notebook/StudioPanel';
import '../notebook.css';

const recordsFrom = response => Array.isArray(response) ? response : response?.results || [];
const roleOf = message => message.role === 'user' ? 'user' : 'assistant';
const toolPrompts = {
  audio_overview: ['Audio overview script', 'Write a conversational two-host audio overview script that explains the key ideas in the selected sources. Include a short introduction, discussion, and conclusion.'],
  study_guide: ['Study guide', 'Create a structured study guide with the main concepts, clear explanations, key terms, and review questions.'],
  mind_map: ['Mind map', 'Create a text-based mind map showing the central topic, branches, and relationships between concepts.'],
  flashcards: ['Flashcards', 'Create concise question-and-answer flashcards for active recall. Number each card and separate its front and back clearly.'],
  briefing_doc: ['Briefing document', 'Write a concise briefing document with the central thesis, essential evidence, and key takeaways.'],
};

export function NotebookWorkspacePage() {
  const { notebookId } = useParams();
  const localNotebook = getNotebooks().find(item => item.id === notebookId);
  const [notebook, setNotebook] = useState(localNotebook || null);
  const [sources, setSources] = useState(() => localNotebook?.sourceItems || []);
  const [selectedSources, setSelectedSources] = useState(() => localNotebook?.sourceItems || []);
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [artifacts, setArtifacts] = useState([]);
  const [loading, setLoading] = useState(isBackendApiEnabled);
  const [sending, setSending] = useState(false);
  const [creatingArtifact, setCreatingArtifact] = useState(false);
  const [error, setError] = useState('');
  const [artifactError, setArtifactError] = useState('');
  const [shared, setShared] = useState(false);

  useEffect(() => {
    if (!isBackendApiEnabled || !notebookId) return undefined;
    let active = true;
    setLoading(true);
    setError('');
    setNotebook(null);
    Promise.all([
      coursesApi.detail(notebookId),
      materialsApi.list(notebookId),
      assistantApi.sessions(),
    ]).then(async ([course, materialsResponse, sessionsResponse]) => {
      const sessions = recordsFrom(sessionsResponse);
      const session = sessions.find(item => String(item.course_id || item.course?.id || item.course) === String(notebookId))
        || await assistantApi.createSession({ title: course.title, course_id: notebookId });
      const conversation = recordsFrom(await assistantApi.messages(session.id));
      if (!active) return;
      const materialRecords = recordsFrom(materialsResponse);
      setNotebook({
        id: course.id,
        title: course.title,
        subject: course.level || 'Course notebook',
        description: course.description || 'Explore this course through its sources.',
      });
      setSources(materialRecords);
      setSelectedSources(materialRecords.filter(item => !item.status || item.status === 'completed').map(item => item.id));
      setSessionId(session.id);
      setMessages(conversation);
      setLoading(false);
    }).catch(() => {
      if (!active) return;
      setError('Could not load this course notebook. Check the course, source, and assistant services, then retry.');
      setLoading(false);
    });
    return () => { active = false; };
  }, [notebookId]);

  useEffect(() => {
    const pendingMaterials = sources.filter(source => typeof source !== 'string' && ['queued', 'processing'].includes(source.status));
    if (!isBackendApiEnabled || !pendingMaterials.length) return undefined;
    let active = true;
    let timer;
    const refresh = async () => {
      try {
        const updates = await Promise.all(pendingMaterials.map(material => materialsApi.processingStatus(material.id)));
        if (!active) return;
        const statusById = new Map(pendingMaterials.map((material, index) => [material.id, updates[index]]));
        setSources(current => current.map(source => {
          const update = statusById.get(source.id);
          return update ? { ...source, ...update, status: update.status || source.status } : source;
        }));
        const completedIds = pendingMaterials.filter((material, index) => updates[index].status === 'completed').map(material => material.id);
        if (completedIds.length) setSelectedSources(current => [...new Set([...current, ...completedIds])]);
        const failed = updates.find(update => update.status === 'failed');
        if (failed) setError(failed.error_message || 'A source could not be processed. Remove it or retry the upload.');
        else if (updates.some(update => ['queued', 'processing'].includes(update.status))) timer = window.setTimeout(refresh, 2000);
      } catch {
        if (active) {
          setError('Could not refresh source processing status. The source list will retry shortly.');
          timer = window.setTimeout(refresh, 5000);
        }
      }
    };
    timer = window.setTimeout(refresh, 1200);
    return () => { active = false; window.clearTimeout(timer); };
  }, [sources]);

  if (loading) return <AppShell><PageHeader eyebrow="Student workspace" title="Loading notebook"/><LoadingState label="Loading course sources and conversation"/></AppShell>;
  if (error && !notebook) return <AppShell><PageHeader eyebrow="Student workspace" title="Notebook unavailable"/><ErrorState message={error} action={<Button onClick={() => window.location.reload()}>Retry</Button>}/></AppShell>;
  if (!notebook) return <AppShell><section className="notebook-empty"><h1>Notebook not found</h1><p>This notebook may have been removed or belongs to another workspace.</p><Link className="button" to="/student/notebooks">Back to notebooks</Link></section></AppShell>;

  const backendSourceIds = isBackendApiEnabled ? selectedSources : [];
  const toggleSource = sourceId => setSelectedSources(current => current.includes(sourceId) ? current.filter(item => item !== sourceId) : [...current, sourceId]);
  const selectAll = selected => setSelectedSources(selected
    ? sources.filter(source => typeof source === 'string' || !source.status || source.status === 'completed').map(source => typeof source === 'string' ? source : source.id)
    : []);
  const openSources = citation => {
    const materialId = citation?.material_id || citation?.material || citation?.id;
    const sourceRow = materialId ? document.getElementById(`source-${materialId}`) : null;
    (sourceRow || document.getElementById('sources-heading'))?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  const askAssistant = async prompt => {
    if (!isBackendApiEnabled || !sessionId) {
      setError('A course-scoped assistant session is not available yet.');
      return null;
    }
    if (!backendSourceIds.length) {
      setError('Select at least one processed source before asking a question.');
      return null;
    }
    setError('');
    setSending(true);
    const knownAssistantIds = new Set(messages.filter(message => roleOf(message) === 'assistant').map(message => message.id));
    try {
      const response = await assistantApi.ask(sessionId, {
        content: prompt,
        course_id: notebook.id,
        material_ids: backendSourceIds,
      });
      let responseMessage = response?.assistant_message || response?.message
        || (response?.role === 'assistant' ? response : null);
      let conversation = recordsFrom(await assistantApi.messages(sessionId));
      for (let attempt = 0; !responseMessage?.content && attempt < 15; attempt += 1) {
        responseMessage = conversation.find(message => roleOf(message) === 'assistant' && !knownAssistantIds.has(message.id));
        if (responseMessage?.content) break;
        await new Promise(resolve => window.setTimeout(resolve, 1000));
        conversation = recordsFrom(await assistantApi.messages(sessionId));
      }
      if (!responseMessage?.content) throw new Error('Assistant response was not completed.');
      const hasQuestion = conversation.some(message => roleOf(message) === 'user' && message.content === prompt);
      const currentConversation = hasQuestion
        ? conversation.some(message => message.id === responseMessage.id) ? conversation : [...conversation, responseMessage]
        : [...conversation, { id: `question-${Date.now()}`, role: 'user', content: prompt }, responseMessage];
      setMessages(currentConversation);
      return responseMessage;
    } catch {
      setError('The assistant could not complete this response. Please retry your question.');
      return null;
    } finally {
      setSending(false);
    }
  };

  const createFromSources = async kind => {
    if (!backendSourceIds.length) {
      setArtifactError('Select at least one processed source first.');
      return;
    }
    setArtifactError('');
    setCreatingArtifact(true);
    try {
      if (kind === 'quiz') {
        let generation = await quizzesApi.generate({
          course_id: notebook.id,
          material_ids: backendSourceIds,
          kind: 'quiz',
          question_count: 5,
          difficulty: 'medium',
        });
        for (let attempt = 0; generation.id && !['completed', 'failed'].includes(generation.status) && attempt < 30; attempt += 1) {
          await new Promise(resolve => window.setTimeout(resolve, 1000));
          generation = await quizzesApi.generation(generation.id);
        }
        if (generation.status !== 'completed') throw new Error('Quiz generation did not complete.');
        const result = generation.result || generation.quiz || generation;
        const questions = result.questions || [];
        setArtifacts(current => [{
          id: generation.id,
          title: result.title || 'Generated quiz',
          status: `${questions.length} questions · review before use`,
          content: questions.map((question, index) => `${index + 1}. ${question.prompt || question.text || ''}`).filter(Boolean).join('\n'),
        }, ...current]);
        return;
      }
      const [title, instruction] = toolPrompts[kind] || [];
      if (!title || !instruction) throw new Error('This study tool is unavailable.');
      const response = await askAssistant(`${instruction}\n\nUse only my selected course sources.`);
      if (!response) throw new Error('The requested study material was not generated.');
      setArtifacts(current => [{
        id: response.id || `${kind}-${Date.now()}`,
        title,
        status: 'Generated from selected sources',
        content: response.content,
      }, ...current]);
    } catch {
      setArtifactError('Could not create this study material from the selected sources. Please retry.');
    } finally {
      setCreatingArtifact(false);
    }
  };

  const createSession = async () => {
    if (!isBackendApiEnabled) {
      setMessages([]);
      return;
    }
    try {
      const session = await assistantApi.createSession({ title: notebook.title, course_id: notebook.id });
      setSessionId(session.id);
      setMessages([]);
      setError('');
    } catch {
      setError('Could not start a new conversation for this course.');
    }
  };

  const addSource = async file => {
    if (!file || !isBackendApiEnabled) return;
    setError('');
    try {
      const material = await materialsApi.upload(notebook.id, file);
      setSources(current => [...current, material]);
      if (material.status === 'completed') setSelectedSources(current => [...current, material.id]);
    } catch {
      setError('The source could not be uploaded. Check its file type and size, then retry.');
    }
  };

  const shareNotebook = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setShared(true);
      window.setTimeout(() => setShared(false), 1800);
    } catch {
      setShared(false);
    }
  };

  return <AppShell><div className="notebook-workspace notebooklm-workspace">
    <header className="notebook-header">
      <div className="notebook-heading-copy"><Link className="text-link" to="/student/notebooks"><ArrowLeft size={15}/> Notebooks</Link><span className="eyebrow">{notebook.subject}</span><h1>{notebook.title}<button type="button" className="notebook-title-menu" aria-label="Notebook options"><MoreHorizontal size={17}/></button></h1><p>{notebook.description}</p></div>
      <div className="notebook-header-actions"><span className="notebook-source-count"><Sparkles size={14}/>{selectedSources.length} sources selected</span><button type="button" className="button button-secondary" onClick={() => void shareNotebook()}><Share2 size={15}/>{shared ? 'Copied' : 'Share'}</button></div>
    </header>
    <div className="notebook-workspace-grid">
      <SourceList sources={sources} selectedSources={selectedSources} onToggle={toggleSource} onSelectAll={selectAll} onAdd={addSource} canUpload={isBackendApiEnabled}/>
      <NotebookChat notebook={notebook} selectedSources={selectedSources} onSourcesClick={openSources} messages={messages} onAsk={askAssistant} onClear={createSession} sending={sending} error={error}/>
      <StudioPanel onCreate={createFromSources} artifacts={artifacts} creating={creatingArtifact} error={artifactError}/>
    </div>
    <div className="notebook-workspace-footer"><Check size={14}/> {isBackendApiEnabled ? 'Answers are grounded in the selected course materials.' : 'Choose a course to work with its published sources.'}</div>
  </div></AppShell>;
}
