import React from 'react';
import { ArrowRight, BarChart3, Users } from 'lucide-react';
import { Link } from 'react-router-dom';

export function EducatorSection() { return <section id="educators" className="atlas-educators"><div><p className="atlas-kicker">For people who teach</p><h2>Give every learner<br/><i>a better next step.</i></h2></div><p>Build a learning environment that feels human at scale. Curate materials, see the signal in student activity, and spend more time on the moments that need you.</p><div className="educator-signals" aria-label="Illustrative dashboard metrics"><span className="educator-demo-note">Illustrative dashboard</span><span><Users size={16} aria-hidden="true"/> 1,248 learners in view</span><span><BarChart3 size={16} aria-hidden="true"/> 84% average progress</span></div><Link to="/auth/register?role=teacher" className="atlas-button atlas-button-light">Explore educator tools <ArrowRight size={15} aria-hidden="true"/></Link></section>; }
