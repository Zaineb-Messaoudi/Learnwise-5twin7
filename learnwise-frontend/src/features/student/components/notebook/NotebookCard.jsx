import React from 'react';
import { ArrowUpRight, FileText } from 'lucide-react';
import { Link } from 'react-router-dom';

export function NotebookCard({ notebook }) { return <Link to={`/student/notebooks/${notebook.id}`} className="notebook-card"><div className={`notebook-card-art art-${notebook.color}`}><span>✦</span><small>{notebook.sources} sources</small></div><div className="notebook-card-body"><span className="eyebrow">{notebook.subject}</span><h2>{notebook.title}</h2><p>{notebook.description}</p><div className="notebook-card-meta"><span><FileText size={14}/> {notebook.sources} sources</span><span>{notebook.updated}</span><ArrowUpRight size={16}/></div></div></Link>; }
