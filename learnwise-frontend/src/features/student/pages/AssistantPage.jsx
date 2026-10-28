import React, { useEffect, useRef, useState } from 'react';
import { ArrowRight, MessageCircle, MoreHorizontal, Sparkles, Zap, Image, Loader2 } from 'lucide-react';
import { useParams, useNavigate } from 'react-router-dom';
import { AppShell } from '../../../layouts/AppShell';
import { PageHeader } from '../../../components/shared/Primitives';
import { AssistantComposer } from '../components/AssistantComposer';
import { assistantApi } from '../../../api/assistant.api';
import { isBackendApiEnabled } from '../../../api/client';
import { useWebSocket } from '../../../hooks/useWebSocket';
import { useQuery } from '@tanstack/react-query';
import './AssistantPage.css';

const answers = [
  { match: ['gradient', 'descent'], text: 'Gradient descent adjusts model weights in small steps that reduce the loss. In this notebook, the process connects to the feedback loop in Chapter 4.', source: 'Chapter 4, section 2' },
  { match: ['analogy', 'simple', 'explain'], text: 'Think of a neural network as a stack of adjustable filters. Each layer notices a more useful pattern, and feedback helps every filter improve its next guess.', source: 'Chapter 4, section 1' },
  { match: ['quiz', 'practice'], text: 'Try the four-question Neural Networks Check-in. It covers activation functions, weights, loss, and validation.', source: 'Neural Networks Check-in' },
];
function answerFor(question) { const normalized = question.toLowerCase(); return answers.find(answer => answer.match.some(word => normalized.includes(word))) || { text: 'From your neural networks material: a model improves by comparing its prediction with the expected answer, then updating the weights that contributed to the error.', source: 'Chapter 4, section 2' }; }
function presentMessage(message) {
  return {
    id: message.id,
    from: message.role === 'user' ? 'user' : 'ai',
    text: message.content || '',
    status: message.status || 'completed',
    source: message.citations?.[0]?.title || '',
    citations: message.citations || [],
    explanation: message.explanation?.content || message.explanation?.text || '',
    illustrations: message.illustrations || [],
  };
}

export function AssistantPage() {
  const { sessionId: requestedSessionId } = useParams();
  const [messages, setMessages] = useState([{ from: 'ai', text: 'Hi Sarah! I’m here to help you make sense of your learning. What are you exploring today?' }]);
  const [sessions, setSessions] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(isBackendApiEnabled);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const seenAssistantIds = useRef(new Set());
  const [generatingIllustration, setGeneratingIllustration] = useState(null);
  const [pendingAssistantId, setPendingAssistantId] = useState(null);
  const navigate = useNavigate();

  // Reset des IDs vus quand on change de session
  useEffect(() => {
    seenAssistantIds.current.clear();
  }, [sessionId]);

  const sessionQuery = useQuery({
    queryKey: ['assistant', 'active-session', requestedSessionId],
    queryFn: async () => {
      const response = await assistantApi.sessions();
      const items = Array.isArray(response) ? response : response.results || [];
      let selected = items.find(item => item.id === requestedSessionId) || items[0];
      if (!selected && requestedSessionId) selected = await assistantApi.session(requestedSessionId);
      if (!selected) selected = await assistantApi.createSession({ title: 'New learning session' });
      const messageResponse = await assistantApi.messages(selected.id);
      return { selected, sessions: items.length ? items : [selected], messages: Array.isArray(messageResponse) ? messageResponse : messageResponse.results || [] };
    },
    enabled: isBackendApiEnabled,
    staleTime: Infinity,
  });
  const socket = useWebSocket(sessionId ? assistantApi.socketPath(sessionId) : '', isBackendApiEnabled && Boolean(sessionId));
  useEffect(() => {
    if (!sessionQuery.data) return;
    const { selected, sessions: loadedSessions, messages: records } = sessionQuery.data;
    setSessions(loadedSessions);
    setSessionId(selected.id);
    // Peupler seenAssistantIds avec les messages deja charges pour eviter les doublons
    records.forEach(m => { if (m.role === 'assistant') seenAssistantIds.current.add(m.id); });
    setMessages(records.map(presentMessage));
    const last = records[records.length - 1];
    if (last && last.role === 'assistant' && (!last.content || last.status === 'processing')) {
      setPendingAssistantId(last.id);
    }
    setLoading(false);
  }, [sessionQuery.data]);
  useEffect(() => {
    if (sessionQuery.isError) {
      setError('Could not load your conversations. Please try again.');
      setMessages([]);
      setLoading(false);
    }
  }, [sessionQuery.isError]);

  // WebSocket : message commencé / delta / complété / erreur
  useEffect(() => {
    const event = socket.lastMessage;
    if (!event) return;
    if (event?.type === 'message.started' && event.id) {
      setSending(true);
      setMessages(current => current.some(message => message.id === event.id) ? current : [...current, { id: event.id, from: 'ai', text: '', status: 'processing', pending: true }]);
      setPendingAssistantId(event.id);
    } else if (event?.type === 'message.delta' && event.payload?.text) {
      setMessages(current => {
        const id = event.id;
        const index = current.findIndex(message => message.id === id);
        if (index < 0) return [...current, { id, from: 'ai', text: event.payload.text, status: 'processing', pending: true }];
        return current.map((message, itemIndex) => itemIndex === index ? { ...message, text: message.text + event.payload.text, status: 'processing' } : message);
      });
    } else if (event?.type === 'message.completed' && event.payload?.message) {
      const message = event.payload.message;
      if (!seenAssistantIds.current.has(message.id)) {
        seenAssistantIds.current.add(message.id);
        setMessages(current => current.some(item => item.id === message.id)
          ? current.map(item => item.id === message.id ? { id: message.id, from: 'ai', text: message.content, status: 'completed', source: message.citations?.[0]?.title || '', citations: message.citations || [], explanation: message.explanation?.content || message.explanation?.text || '', illustrations: message.illustrations || [], pending: false } : item)
          : [...current, { id: message.id, from: 'ai', text: message.content, status: 'completed', source: message.citations?.[0]?.title || '', citations: message.citations || [], explanation: message.explanation?.content || message.explanation?.text || '', illustrations: message.illustrations || [], pending: false }]);
        setPendingAssistantId(null);
      }
      setSending(false);
    } else if (socket.lastMessage?.type === 'error') {
      setError(socket.lastMessage.payload?.message || 'Assistant response failed. Retry your question.');
      setSending(false);
      setPendingAssistantId(null);
    }
  }, [socket.lastMessage]);

  // Fallback : si un message assistant est en attente depuis trop longtemps sans WebSocket,
  // on rafraîchit les messages depuis l'API REST
  useEffect(() => {
    if (!pendingAssistantId || !sessionId) return;
    const timer = window.setTimeout(async () => {
      try {
        const response = await assistantApi.messages(sessionId);
        const records = Array.isArray(response) ? response : response.results || [];
        const updated = records.find(m => m.id === pendingAssistantId);
        if (updated && updated.content && updated.status === 'completed') {
          setMessages(current => current.map(m => m.id === pendingAssistantId ? { id: updated.id, from: 'ai', text: updated.content, status: 'completed', source: updated.citations?.[0]?.title || '', citations: updated.citations || [], explanation: updated.explanation?.content || updated.explanation?.text || '', illustrations: updated.illustrations || [], pending: false } : m));
          setPendingAssistantId(null);
        }
      } catch { /* ignore fallback errors */ }
    }, 5000);
    return () => window.clearTimeout(timer);
  }, [pendingAssistantId, sessionId]);

  useEffect(() => {
    const handleOnboardingRequired = () => {
      navigate('/auth/complete-profile', { replace: true });
    };
    window.addEventListener('learnwise:onboarding-required', handleOnboardingRequired);
    return () => { window.removeEventListener('learnwise:onboarding-required', handleOnboardingRequired); };
  }, [navigate]);

  const selectSession = async id => {
    setError('');
    try {
      const response = await assistantApi.messages(id);
      const records = Array.isArray(response) ? response : response.results || [];
      setSessionId(id);
      setMessages(records.map(presentMessage));
      const last = records[records.length - 1];
      if (last && last.role === 'assistant' && (!last.content || last.status === 'processing')) {
        setPendingAssistantId(last.id);
      } else {
        setPendingAssistantId(null);
      }
    } catch { setError('Could not load this conversation. Try selecting it again.'); }
  };
  const newSession = async () => {
    setError('');
    if (!isBackendApiEnabled) {
      setMessages([{ from: 'ai', text: 'New conversation ready. What are you exploring?' }]);
      return;
    }
    try {
      const session = await assistantApi.createSession({ title: 'New learning session' });
      setSessions(current => [session, ...current]);
      setSessionId(session.id);
      setMessages([]);
      setPendingAssistantId(null);
    } catch { setError('Could not create a new conversation. Please try again.'); }
  };

  const generateIllustration = async (messageId, prompt) => {
    if (!sessionId) return;
    setGeneratingIllustration(messageId);
    setError('');
    try {
      const response = await assistantApi.generateIllustration(messageId, prompt, 'educational');
      // La réponse est le message complet avec son tableau illustrations
      const illustrations = response.illustrations || [];
      const newIllustration = illustrations[illustrations.length - 1];
      if (!newIllustration || !newIllustration.image) {
        throw new Error(newIllustration?.error_message || 'Aucune image generee.');
      }
      setError('');
      setMessages(current => current.map(msg => {
        if (msg.id !== messageId) return msg;
        return { ...msg, illustrations: [...(msg.illustrations || []), {
          id: newIllustration.id,
          image: newIllustration.image,
          alt_text: newIllustration.alt_text || prompt,
          prompt: newIllustration.prompt || prompt,
          caption: newIllustration.caption || prompt
        }] };
      }));
    } catch (cause) {
      setError(cause.message || 'Could not generate illustration. Try again.');
    } finally {
      setGeneratingIllustration(null);
    }
  };
  const send = async value => {
    const question = (value || input).trim();
    if (!question || sending) return;
    setError('');
    setInput('');
    if (!isBackendApiEnabled) {
      const answer = answerFor(question);
      setMessages(current => [...current, { from: 'user', text: question }, { from: 'ai', ...answer }]);
      return;
    }
    if (!sessionId) {
      setError('A conversation is not ready yet. Wait for the session to load and retry.');
      setInput(question);
      return;
    }
    setMessages(current => [...current, { from: 'user', text: question }]);
    setSending(true);
    try {
      const response = await assistantApi.ask(sessionId, { content: question });
      const message = response.assistant_message || (response.role === 'assistant' || response.role === 'ai' ? response : null);
      if (message?.content) {
        if (!seenAssistantIds.current.has(message.id)) {
          seenAssistantIds.current.add(message.id);
          setMessages(current => [...current, { id: message.id, from: 'ai', text: message.content, source: message.citations?.[0]?.title || '', citations: message.citations || [], explanation: message.explanation?.content || message.explanation?.text || '', illustrations: message.illustrations || [] }]);
        }
        setSending(false);
      } else {
        setPendingAssistantId(message?.id || null);
      }
    } catch {
      setError('Your question could not be sent. It remains in this conversation; please try again.');
      setSending(false);
    }
  };
  const conversationItems = isBackendApiEnabled
    ? sessions.map((item, index) => ({ id: item.id, title: item.title || 'Learning conversation', time: index ? 'Earlier' : 'Now' }))
    : [{ id: 'sample-1', title: 'Neural networks basics', time: 'Now' }, { id: 'sample-2', title: 'Understanding attention', time: '1d' }, { id: 'sample-3', title: 'Study plan for this week', time: '2d' }];
  return (
    <AppShell>
      <div className="assistant-page-wrapper">
        <PageHeader eyebrow="AI assistant" title="Ask, explore, understand." description="Your learning companion can answer with explanations grounded in your course materials." />
        <div className="assistant-layout">
          <aside className="conversation-list">
            <div className="assistant-sidebar-head"><span className="eyebrow">CONVERSATIONS</span><button type="button" className="icon-button" aria-label="New conversation" onClick={() => void newSession()}><MessageCircle size={16} /></button></div>
            {conversationItems.map((item, index) => <button type="button" className={`conversation-item ${(isBackendApiEnabled ? item.id === sessionId : index === 0) ? 'active' : ''}`} key={item.id} onClick={() => isBackendApiEnabled ? void selectSession(item.id) : setMessages([{ from: 'ai', text: `Let’s continue with ${item.title}. What would you like to understand next?` }])}><MessageCircle size={15} /><span>{item.title}</span><small>{item.time}</small></button>)}
          </aside>
          <section className="chat-panel">
            <div className="chat-top"><div className="chat-course"><div className="tiny-course-icon">✦</div><div><b>AI &amp; Machine Learning</b><span>Course-grounded conversation</span></div></div>{isBackendApiEnabled && <span className={`assistant-connection ${socket.status}`}>{socket.status}</span>}<button type="button" className="icon-button" aria-label="Conversation options"><MoreHorizontal size={18} /></button></div>
            {error && <p className="assistant-inline-error" role="alert">{error}{sessionQuery.isError && <button type="button" onClick={() => void sessionQuery.refetch()}> Retry</button>}</p>}
            <div className="chat-messages" aria-live="polite">
              {loading ? <p role="status">Loading your conversations…</p> : messages.map((message, index) => <div key={`${message.from}-${message.id || index}`} className={`chat-message ${message.from} ${message.pending ? 'pending' : ''}`}><div className="chat-avatar" aria-hidden="true">{message.from === 'ai' ? <Sparkles size={15} /> : 'SC'}</div><div><span className="message-author">{message.from === 'ai' ? 'Learnwise AI' : 'You'}</span><p>{message.text || (message.from === 'ai' && message.pending ? 'Learnwise is preparing a response…' : '')}</p>{message.explanation && <p className="assistant-explanation">{message.explanation}</p>}{message.illustrations?.map((illustration, illustrationIndex) => <figure className="assistant-illustration" key={illustration.id || illustrationIndex}><img src={illustration.image} alt={illustration.alt_text || illustration.prompt || 'AI-generated course illustration'} loading="lazy"/>{(illustration.caption || illustration.prompt) && <figcaption>{illustration.caption || illustration.prompt}</figcaption>}</figure>)}{message.from === 'ai' && index > 0 && <div className="ai-answer"><b>{isBackendApiEnabled ? 'Assistant response' : 'Sample course answer'}</b>{(message.citations?.length ? message.citations : message.source ? [{ title: message.source }] : []).map((citation, citationIndex) => <div className="answer-source" key={citation.id || citationIndex}><span>Source: {citation.title}{citation.page ? ` · page ${citation.page}` : ''}{citation.timestamp ? ` · ${citation.timestamp}` : ''}</span><ArrowRight size={13} /></div>)}</div>}{message.from === 'ai' && isBackendApiEnabled && !message.pending && <div className="message-actions"><button type="button" className="icon-button" onClick={() => void generateIllustration(message.id, message.text)} disabled={generatingIllustration === message.id || sending} aria-label="Generate illustration for this answer"><Image size={16} /><span className="button-label">{generatingIllustration === message.id ? <Loader2 size={14} className="spin" /> : 'Illustrate'}</span></button></div>}</div></div>)}
              {sending && <p className="assistant-pending" role="status"><Sparkles size={15}/> Learnwise is preparing a response…</p>}
            </div>
            <AssistantComposer value={input} onChange={setInput} onSend={() => void send()} disabled={loading || sending} />
            {isBackendApiEnabled && <span className="composer-hint">Responses may include course citations and generated illustrations.</span>}
          </section>
          <aside className="assistant-context"><span className="eyebrow">SUGGESTED QUESTIONS</span>{['What is gradient descent?', 'Can you give me an analogy?', 'Quiz me on this chapter'].map(item => <button type="button" className="suggested-question" key={item} onClick={() => void send(item)}>{item}<ArrowRight size={14} /></button>)}<div className="context-tip"><Zap size={15} /><div><b>Study tip</b><p>Explain the concept in your own words to remember it longer.</p></div></div></aside>
        </div>
      </div>
    </AppShell>
  );
}

export default AssistantPage;
