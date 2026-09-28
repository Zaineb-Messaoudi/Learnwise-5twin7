import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, BookOpen, Compass, MessageCircle, Sparkles, Target } from 'lucide-react';
import { SignatureLanding } from '../features/public/pages/SignatureLandingPage';

export function Landing() {
  return <SignatureLanding />;
}

export function Feature({ icon, title, text, tone }) {
  return <article className={`feature-item ${tone}`}><div className={`feature-icon ${tone}`}>{icon}</div><h3>{title}</h3><p>{text}</p><ArrowRight size={16} className="feature-arrow" aria-hidden="true" /></article>;
}

export function Step({ n, title, text, icon, active }) {
  return <article className={`workflow-step ${active ? 'active' : ''}`}><div className="step-top"><span>{n}</span><div className="step-icon">{icon}</div></div><h3>{title}</h3><p>{text}</p></article>;
}

export function PublicNav() {
  return <header className="public-nav"><Link to="/" className="logo" aria-label="Learnwise home"><span className="logo-mark"><Sparkles size={17} /></span><span>learnwise</span></Link><nav className="public-links" aria-label="Public navigation"><Link to="/features">Features</Link><Link to="/how-it-works">How it works</Link><Link to="/faq">FAQ</Link></nav><div className="nav-actions"><Link to="/auth/login" className="text-link">Log in</Link><Link to="/auth/register" className="button button-primary button-small">Start learning <ArrowRight size={15} /></Link></div></header>;
}

export function PublicSectionPage({ title, description, kind = 'overview', children }) {
  const content = {
    about: [
      [<Sparkles />, 'A calmer relationship with AI', 'The companion explains its thinking, invites questions, and keeps the learner in control.'],
      [<BookOpen />, 'Built around your material', 'Your notes, lectures, and sources become the context for useful study instead of another content dump.'],
      [<Target />, 'Progress with a point', 'Learnwise turns activity into a clear next step, so progress feels like direction rather than a score.'],
    ],
    features: [
      [<BookOpen />, 'Notebook workspace', 'Gather PDFs, notes, audio, and lecture fragments into source-grounded learning spaces.', '/student/notebooks'],
      [<Sparkles />, 'Learning companion', 'Ask for explanations, analogies, connections, and follow-up questions without losing the thread.', '/student/assistant'],
      [<Target />, 'Active practice', 'Create quizzes and exercises from your own context, then learn from the feedback.', '/student/exercises'],
      [<MessageCircle />, 'Voice learning', 'Ask questions and listen to explanations when typing or looking at a screen is not the right mode.', '/student/voice-question'],
      [<Compass />, 'Progress signals', 'See concepts, momentum, and useful next actions in one connected view.', '/student/progress'],
    ],
    workflow: [
      ['01', 'Bring in the messy material', 'Upload a source, open a notebook, or start with the question you cannot quite phrase yet.'],
      ['02', 'Make meaning together', 'Ask, simplify, compare, and connect until the idea feels like something you can use.'],
      ['03', 'Practice at the edge', 'Test your understanding, review the feedback, and let the next useful move emerge.'],
    ],
  };
  const items = content[kind] || content.about;
  return <div className="public-page"><PublicNav /><main className="public-info"><span className="kicker">Learnwise platform</span><h1>{title}</h1><p>{description}</p>{kind === 'workflow' ? <div className="public-workflow-list">{items.map(([number, itemTitle, text]) => <article key={number}><span>{number}</span><div><h2>{itemTitle}</h2><p>{text}</p></div><ArrowRight size={18} aria-hidden="true" /></article>)}</div> : <div className="feature-grid">{items.map(([icon, itemTitle, text, to]) => to ? <Link className="feature-item" to={to} key={itemTitle}><div className="feature-icon purple">{icon}</div><h3>{itemTitle}</h3><p>{text}</p><ArrowRight size={16} className="feature-arrow" aria-hidden="true" /></Link> : <Feature icon={icon} title={itemTitle} text={text} tone="purple" key={itemTitle} />)}</div>}{children}</main></div>;
}
