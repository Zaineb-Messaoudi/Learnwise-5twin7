import React, { useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { useAuth } from '../../../contexts/AuthContext';
import './SocialCallbackPage.css';

export function SocialCallbackPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { socialLogin } = useAuth();
  const hasRunRef = useRef(false);

  useEffect(() => {
    if (hasRunRef.current) return;
    hasRunRef.current = true;

    const handleCallback = async () => {
      const params = new URLSearchParams(window.location.search);
      const code = params.get('code');
      const stateStr = params.get('state');
      const oauthError = params.get('error');

      if (oauthError) {
        navigate(`/auth/login?error=${encodeURIComponent(params.get('error_description') || oauthError)}`, { replace: true });
        return;
      }

      if (!code || !stateStr) {
        navigate('/auth/login?error=invalid_callback', { replace: true });
        return;
      }

      let state;
      try {
        state = JSON.parse(stateStr);
      } catch {
        navigate('/auth/login?error=invalid_state', { replace: true });
        return;
      }

      const { provider, role, next } = state;

      // For OAuth, send null role so user must choose in complete profile
      // (role selection is handled in CompleteProfilePage before face capture)
      try {
        const result = await socialLogin(provider, null, null, code);
        if (result.success) {
          if (result.isNewUser || result.needsProfileCompletion) {
            // New OAuth user or needs profile completion - redirect to complete profile page.
            // socialLogin() already logged the user in (tokens are stored), so only the
            // user object needs to travel onward, and it goes via navigation state — never
            // the URL, where it (and especially the tokens) would end up in browser
            // history and server/proxy logs.
            navigate('/auth/complete-profile', { replace: true, state: { user: result.user } });
          } else {
            // Existing user - login directly
            const routeRole = result.user?.role ? (result.user.role === 'etudiant' ? 'student' : result.user.role === 'professeur' ? 'teacher' : 'admin') : 'student';
            navigate(next || `/${routeRole}/dashboard`, { replace: true });
          }
        } else {
          navigate(`/auth/login?error=${encodeURIComponent(result.error)}`, { replace: true });
        }
      } catch (err) {
        navigate('/auth/login?error=social_login_failed', { replace: true });
      }
    };

    handleCallback();
  }, [searchParams, socialLogin, navigate]);

  return (
    <div className="callback-page">
      <div className="callback-card">
        <div className="callback-icon loading">
          <Loader2 className="spin" size={32} />
        </div>
        <h1>Completing sign in…</h1>
        <p>Please wait while we connect your account.</p>
      </div>
    </div>
  );
}

export default SocialCallbackPage;