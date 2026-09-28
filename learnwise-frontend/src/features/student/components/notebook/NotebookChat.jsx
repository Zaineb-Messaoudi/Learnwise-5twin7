import React, { useEffect, useRef, useState } from 'react';
import { ArrowDown, ArrowRight, Bot, ChevronDown, Copy, Paperclip, RotateCcw, Send, Sparkles, ThumbsDown, ThumbsUp } from 'lucide-react';

const suggestions = [
  'Create a study guide from these sources',
  'What are the key ideas?',
  'Compare the main arguments',
];

const messageRole = message => message.role === 'user' || message.from === 'user' ? 'user' : 'assistant';
const citationTitle = citation => typeof citation === 'string' ? citation : citation.title || citation.material_title || 'Source';
const citationLocation = citation => typeof citation === 'string' ? '' : citation.page ? ` · p. ${citation.page}` : citation.timestamp || citation.timecode || '';

export function NotebookChat({ notebook, selectedSources = [], onSourcesClick, messages = [], onAsk, onClear, sending = false, error = '' }) {
  const [question, setQuestion] = useState('');
  const messagesRef = useRef(null);
  useEffect(() => {
    if (messagesRef.current) messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
  }, [messages, sending]);

  const ask = async value => {
    const prompt = value.trim();
    if (!prompt || sending || !onAsk) return;
    setQuestion('');
    await onAsk(prompt);
  };

  const submit = event => {
    event.preventDefault();
    void ask(question);
  };
  return <section className="notebook-chat" aria-labelledby="chat-heading">
    <header className="notebook-chat-toolbar">
      <div className="notebook-chat-title">
        <span className="notebook-chat-mark"><Sparkles size={16}/></span>
        <div><h2 id="chat-heading">Notebook guide</h2><span>{notebook.title}</span></div>
      </div>
      <div className="notebook-chat-actions">
        <button type="button" className="notebook-source-filter" onClick={onSourcesClick}><Paperclip size={14}/>{selectedSources.length} sources<ChevronDown size={13}/></button>
        <button type="button" className="notebook-icon-action" aria-label="New conversation" onClick={() => { if (window.confirm('Start a new conversation?')) onClear?.(); }}><RotateCcw size={16}/></button>
      </div>
    </header>

    <div className="notebook-conversation" ref={messagesRef} aria-live="polite">
      {!messages.length ? <div className="notebook-welcome">
        <span className="notebook-welcome-icon"><Sparkles size={23}/></span>
        <h3>What would you like to explore?</h3>
        <p>Ask questions across your selected sources. Answers are organized around evidence you can open and review.</p>
        <div className="notebook-prompt-grid">{suggestions.map(item => <button type="button" key={item} onClick={() => void ask(item)}>{item}<ArrowRight size={14}/></button>)}</div>
      </div> : <div className="notebook-thread">
        {messages.map((message, index) => messageRole(message) === 'user'
          ? <div className="notebook-question" key={message.id || `user-${index}`}><span className="notebook-user-avatar">S</span><p>{message.content || message.text || ''}</p></div>
          : <article className="notebook-answer" key={message.id || `assistant-${index}`}>
            <span className="notebook-answer-avatar"><Bot size={16}/></span>
            <div className="notebook-answer-content"><b>Notebook guide</b><p>{message.content || message.text || ''}</p>
              {Boolean(message.citations?.length) && <div className="notebook-citations" aria-label="Sources">
                {message.citations.map((source, citationIndex) => <button type="button" className="notebook-citation" key={`${source.id || source.material || citationTitle(source)}-${citationIndex}`} onClick={() => onSourcesClick?.(source)}><span>[{citationIndex + 1}]</span>{citationTitle(source)}{citationLocation(source)}<ArrowDown size={12}/></button>)}
              </div>}
              <div className="notebook-answer-tools"><button type="button" aria-label="Copy answer" onClick={() => void navigator.clipboard?.writeText(message.content || message.text || '')}><Copy size={14}/></button><button type="button" aria-label="Helpful answer"><ThumbsUp size={14}/></button><button type="button" aria-label="Unhelpful answer"><ThumbsDown size={14}/></button></div>
            </div>
          </article>)}
      </div>}
      {sending && <p className="notebook-muted" role="status">Working from your selected sources…</p>}
      {error && <p className="upload-error" role="alert">{error}</p>}
    </div>

    <div className="notebook-composer-wrap">
      {messages.length > 0 && <div className="notebook-followups">{suggestions.slice(1).map(item => <button type="button" key={item} onClick={() => void ask(item)}>{item}</button>)}</div>}
      <form className="notebook-composer" onSubmit={submit}>
        <label className="sr-only" htmlFor="notebook-question">Ask your sources</label>
        <textarea id="notebook-question" value={question} onChange={event => setQuestion(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void ask(question); } }} placeholder="Ask a question about your sources..." rows={2}/>
        <div className="notebook-composer-bottom"><span><Paperclip size={13}/> {selectedSources.length ? `${selectedSources.length} sources selected` : 'Select sources to focus your answer'}</span><button type="submit" className="notebook-send" disabled={!question.trim() || sending} aria-label="Send question"><Send size={15}/></button></div>
      </form>
      <p className="notebook-composer-note">Responses include source references so you can check the context.</p>
    </div>
  </section>;
}
