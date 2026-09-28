import React from 'react';
import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Logo } from '../../../layouts/AppShell';

export function NotFound() { return <main className="not-found"><Logo/><div><span className="eyebrow">404</span><h1>This page wandered off.</h1><p>Let’s get you back to somewhere useful.</p><Link to="/student/dashboard" className="button">Back to dashboard <ArrowRight size={15}/></Link></div></main>; }
