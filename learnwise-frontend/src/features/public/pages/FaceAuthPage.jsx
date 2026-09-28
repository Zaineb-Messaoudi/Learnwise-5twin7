import React from 'react';
import { ArrowLeft, ScanFace } from 'lucide-react';
import { Link } from 'react-router-dom';
import { PublicFrame } from '../components/PublicFrame';

export function FaceAuthPage() {
  return <PublicFrame><main className="auth-special"><span className="kicker">Identity verification</span><h1>Face sign-in is not available yet.</h1><p>Learnwise does not access your camera or perform face or emotion recognition. Use email sign-in while the team defines a consent-based verification flow.</p><div className="face-frame ready"><div className="face-placeholder"><ScanFace size={42}/></div><span className="face-status">Camera access is off</span></div><div className="face-actions"><Link to="/auth/login" className="button"><ArrowLeft size={15}/> Use email sign-in</Link></div></main></PublicFrame>;
}
