import React from 'react';
import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import '../../../pages/mock-pages.css';
import { BrandMark } from './BrandMark';

export function PublicFrame({ children }) { return <div className="public-page"><a className="skip-link" href="#public-main">Skip to content</a><header className="public-nav"><BrandMark className="logo"/><nav className="public-links" aria-label="Public navigation"><Link to="/features">Features</Link><Link to="/how-it-works">How it works</Link><Link to="/educators">For educators</Link><Link to="/faq">FAQ</Link></nav><div className="nav-actions"><Link to="/auth/login" className="text-link">Log in</Link><Link to="/auth/register" className="button button-primary button-small">Start learning <ArrowRight size={15}/></Link></div></header>{React.cloneElement(children, { id: 'public-main' })}<footer className="public-footer"><BrandMark className="logo"/><nav aria-label="Footer navigation"><Link to="/features">Features</Link><Link to="/educators">For educators</Link><Link to="/privacy">Privacy</Link><Link to="/terms">Terms</Link></nav></footer></div>; }
