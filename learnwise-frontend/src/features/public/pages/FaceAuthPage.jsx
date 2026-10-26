import React from 'react';
import { ArrowLeft, ScanFace, Shield } from 'lucide-react';
import { Link } from 'react-router-dom';
import { PublicFrame } from '../components/PublicFrame';

export function FaceAuthPage() {
  return (
    <PublicFrame>
      <main className="auth-special">
        <span className="kicker">Identity verification</span>
        <h1>Face sign-in</h1>
        <p>Sign in quickly and securely with facial recognition. Your face descriptor is computed locally in your browser—no images leave your device.</p>
        <div className="face-frame ready">
          <div className="face-placeholder"><ScanFace size={42} /></div>
          <span className="face-status">Camera access required</span>
        </div>
        <div className="face-benefits">
          <div className="benefit">
            <Shield size={18} />
            <span>Privacy-first: descriptor computed locally</span>
          </div>
          <div className="benefit">
            <Shield size={18} />
            <span>No images stored or transmitted</span>
          </div>
          <div className="benefit">
            <Shield size={18} />
            <span>Optional — use email sign-in if preferred</span>
          </div>
        </div>
        <div className="face-actions">
          <Link to="/auth/login" className="button"><ArrowLeft size={15} /> Use email sign-in instead</Link>
        </div>
      </main>
    </PublicFrame>
  );
}

export default FaceAuthPage;