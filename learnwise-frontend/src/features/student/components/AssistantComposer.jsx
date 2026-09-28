import React from 'react';
import { ArrowRight, BookOpen, Mic } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from '../../../components/shared/Primitives';

export function AssistantComposer({ value, onChange, onSend, disabled = false }) {
  const submit = event => { event.preventDefault(); onSend(); };
  return <form className="chat-composer" onSubmit={submit}><div className="composer-input"><textarea aria-label="Ask your learning assistant" name="question" value={value} onChange={event => onChange(event.target.value)} placeholder="Ask anything about your learning…" rows={1} disabled={disabled}/><div><Link to="/student/notebooks" className="icon-button" aria-label="Browse your course materials"><BookOpen size={16}/></Link><Link to="/student/voice-question" className="icon-button" aria-label="Ask with your voice"><Mic size={17}/></Link></div></div><Button type="submit" className="send-button" aria-label="Send message" disabled={disabled}><ArrowRight size={17}/></Button></form>;
}
