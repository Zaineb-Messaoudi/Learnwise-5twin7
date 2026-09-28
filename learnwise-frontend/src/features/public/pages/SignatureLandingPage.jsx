import React, { useEffect, useRef, useState } from 'react';
import { ArrowDownRight, ArrowRight, ChevronRight, Compass, Menu, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import '../../../pages/signature-pages.css';
import { BrandMark } from '../components/BrandMark';
import { EducatorSection } from '../components/EducatorSection';
import { FeatureExplorer, AtlasField } from '../components/SignatureSections';
import { LearningDemo } from '../components/LearningDemo';

function Hero() {
  return <section className="atlas-hero"><div className="hero-copy-atlas"><p className="atlas-kicker"><span className="signal" aria-hidden="true" /> The anti-boring learning platform</p><h1>Make your<br /><strong>aha moment</strong><br /><i>impossible to miss.</i></h1><p className="atlas-lede">Learnwise turns your courses, questions, and messy notes into a colorful map of what you know, what you are ready for, and where curiosity can take you next.</p><div className="atlas-hero-actions"><Link to="/auth/register" className="atlas-button atlas-button-bright">Build my learning world <ArrowRight size={16} /></Link><a href="#atlas" className="atlas-text-action">Take the tour <ArrowDownRight size={16} /></a></div><div className="atlas-trust"><span>AI that explains</span><span className="trust-rule" /><span>Practice that adapts</span><span className="trust-rule" /><span>Progress you can feel</span></div></div><AtlasField /></section>;
}

function Method() {
  const steps = [['01', 'Drop in a question', 'Bring a PDF, a note, a voice memo, or the thing you cannot quite explain yet.'], ['02', 'Follow the thread', 'Your AI learning partner turns fragments into clear explanations and useful connections.'], ['03', 'Make it yours', 'Practice at the edge of your ability, then see the pattern in your progress.']];
  return <section id="method" className="atlas-method" aria-labelledby="method-heading"><div className="method-label"><span>01</span><p id="method-heading">The loop</p><Compass size={22} aria-hidden="true" /></div><div className="method-grid">{steps.map(([number, title, text]) => <article className="method-step" key={number}><span className="step-number">{number}</span><div><h3>{title}</h3><p>{text}</p></div><ChevronRight size={18} aria-hidden="true" /></article>)}</div></section>;
}

export function SignatureLanding() {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef(null);
  const firstMenuLinkRef = useRef(null);
  useEffect(() => { if (menuOpen) firstMenuLinkRef.current?.focus(); }, [menuOpen]);
  useEffect(() => { const closeOnEscape = event => { if (event.key === 'Escape' && menuOpen) { setMenuOpen(false); menuButtonRef.current?.focus(); } }; document.addEventListener('keydown', closeOnEscape); return () => document.removeEventListener('keydown', closeOnEscape); }, [menuOpen]);
  const closeMenu = () => setMenuOpen(false);
  return <div className="atlas-page"><a className="skip-link" href="#main-content">Skip to content</a><header className="atlas-nav"><BrandMark className="signature-mark" /><nav aria-label="Primary navigation"><a href="#atlas">How it works</a><a href="#features">Features</a><a href="#method">Learning loop</a><a href="#educators">For educators</a></nav><div className="atlas-actions"><Link to="/auth/login" className="quiet-link">Log in</Link><Link to="/auth/register" className="atlas-button atlas-button-bright">Start free <ArrowRight size={15} /></Link><button ref={menuButtonRef} type="button" className="atlas-menu" aria-expanded={menuOpen} aria-controls="mobile-navigation" aria-label={menuOpen ? 'Close menu' : 'Open menu'} onClick={() => setMenuOpen(value => !value)}>{menuOpen ? <X size={20} /> : <Menu size={20} />}</button></div></header>{menuOpen && <nav id="mobile-navigation" className="mobile-atlas-nav" aria-label="Mobile navigation"><a ref={firstMenuLinkRef} href="#atlas" onClick={closeMenu}>How it works</a><a href="#features" onClick={closeMenu}>Features</a><a href="#method" onClick={closeMenu}>Learning loop</a><a href="#educators" onClick={closeMenu}>For educators</a></nav>}<main id="main-content"><Hero /><section id="atlas" className="atlas-intro" aria-labelledby="atlas-heading"><div><p className="atlas-kicker">Your brain is not a sidebar</p><h2 id="atlas-heading">Stop collecting tabs.<br /><i>Start connecting ideas.</i></h2></div><p>Learnwise is a living studio for learning. Ask an unruly question, drop in a lecture, remix a concept, or test yourself. The platform turns every move into a more useful next move.</p></section><FeatureExplorer /><LearningDemo /><Method /><EducatorSection /></main><footer className="atlas-footer"><div><BrandMark className="signature-mark" /><p>One intelligent space for courses, questions, practice, and progress.</p></div><nav aria-label="Footer navigation"><Link to="/features">Features</Link><Link to="/how-it-works">How it works</Link><Link to="/educators">For educators</Link><Link to="/faq">FAQ</Link></nav><div className="footer-action"><span>Ready when you are?</span><Link to="/auth/register" className="atlas-button atlas-button-bright">Build your map <ArrowRight size={14} /></Link></div></footer></div>;
}
