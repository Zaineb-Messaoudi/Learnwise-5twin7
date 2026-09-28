import React, { useRef, useState } from 'react';
import { ArrowRight, BookOpen, ChevronRight, Compass, MessageCircle, Sparkles, Target } from 'lucide-react';
import { Link } from 'react-router-dom';

const features = [
  { id: 'materials', label: 'Bring materials', icon: <BookOpen size={19} />, title: 'Turn any material into a starting point.', text: 'Upload PDFs, notes, audio, or a lecture outline. Learnwise organizes the useful parts into summaries, transcripts, and connected concepts.', color: 'pink', to: '/student/notebooks' },
  { id: 'companion', label: 'Ask your companion', icon: <Sparkles size={19} />, title: 'Get unstuck without losing your voice.', text: 'Ask follow-up questions, request a simpler explanation, or ask for an analogy that matches how you think.', color: 'blue', to: '/student/assistant' },
  { id: 'practice', label: 'Practice actively', icon: <Target size={19} />, title: 'Replace passive scrolling with useful friction.', text: 'Generate quizzes and exercises from your own material, then get feedback that tells you what to try next.', color: 'lime', to: '/student/exercises' },
  { id: 'voice', label: 'Learn out loud', icon: <MessageCircle size={19} />, title: 'Keep learning when your screen is busy.', text: 'Use voice prompts, listen to explanations, and talk through a difficult concept as naturally as you would with a study partner.', color: 'coral', to: '/student/voice-question' },
  { id: 'signal', label: 'See your signal', icon: <Compass size={19} />, title: 'Track understanding, not just activity.', text: 'Watch your concepts connect, spot gaps, celebrate streaks, and always know the most useful next step.', color: 'violet', to: '/student/progress' },
];

export function FeatureExplorer() {
  const [activeId, setActiveId] = useState(features[0].id);
  const tabRefs = useRef([]);
  const active = features.find(feature => feature.id === activeId) || features[0];
  const onKeyDown = event => {
    const current = tabRefs.current.indexOf(event.target);
    let next = current;
    if (event.key === 'ArrowRight' || event.key === 'ArrowDown') next = (current + 1) % features.length;
    if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') next = (current - 1 + features.length) % features.length;
    if (event.key === 'Home') next = 0;
    if (event.key === 'End') next = features.length - 1;
    if (next !== current) {
      event.preventDefault();
      tabRefs.current[next]?.focus();
    }
  };
  return <section id="features" className="feature-explorer" aria-labelledby="features-heading"><div className="explorer-head"><div><p className="atlas-kicker">Everything in one learning world</p><h2 id="features-heading">Less platform.<br /><i>More possibility.</i></h2></div><p>Choose a doorway. They all lead back to the same thing: making progress feel visible.</p></div><div className="explorer-layout"><div className="feature-tabs" role="tablist" aria-label="Learnwise features" onKeyDown={onKeyDown}>{features.map((feature, index) => <button ref={node => { tabRefs.current[index] = node; }} type="button" key={feature.id} id={`feature-tab-${feature.id}`} role="tab" aria-selected={active.id === feature.id} aria-controls={`feature-panel-${feature.id}`} tabIndex={active.id === feature.id ? 0 : -1} className={`feature-tab ${active.id === feature.id ? 'active' : ''} ${feature.color}`} onClick={() => setActiveId(feature.id)} onFocus={() => setActiveId(feature.id)}>{feature.icon}<span>{feature.label}</span><ChevronRight size={15} aria-hidden="true" /></button>)}</div><article id={`feature-panel-${active.id}`} role="tabpanel" tabIndex="0" aria-labelledby={`feature-tab-${active.id}`} className={`feature-stage ${active.color}`}><div className="stage-decoration" aria-hidden="true"><span /><span /><span /></div><div className="stage-icon" aria-hidden="true">{active.icon}</div><p className="atlas-kicker">{active.label}</p><h3>{active.title}</h3><p>{active.text}</p><Link to={active.to} className="atlas-text-action">Try this in Learnwise <ArrowRight size={15} aria-hidden="true" /></Link></article></div></section>;
}

export function AtlasField() { const nodes = [['neural nets', 'lime', '14%', '63%'], ['loss functions', 'coral', '39%', '29%'], ['ethics', 'blue', '68%', '54%'], ['language', 'lime', '82%', '22%'], ['your next idea', 'bright', '22%', '80%']]; return <figure className="atlas-field"><figcaption className="sr-only">A learning atlas illustration showing connected concepts: neural nets, loss functions, ethics, language, and your next idea.</figcaption><div className="field-grid" aria-hidden="true" /><div className="field-orbit orbit-a" aria-hidden="true" /><div className="field-orbit orbit-b" aria-hidden="true" /><span className="field-cross cross-a" aria-hidden="true">+</span><span className="field-cross cross-b" aria-hidden="true">+</span>{nodes.map(([label, tone, left, top], index) => <div key={label} className={`atlas-node ${tone} ${index === 0 ? 'node-active' : ''}`} style={{ left, top }}><span className="node-dot" /><span>{label}</span></div>)}<div className="field-caption"><span className="live-pulse" /> Learning map <b>04</b></div></figure>; }
