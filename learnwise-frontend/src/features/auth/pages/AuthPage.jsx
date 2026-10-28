import React, { useState, useEffect } from 'react';
import { ArrowRight, Check, LockKeyhole, Sparkles, Loader2, ScanFace } from 'lucide-react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { authApi } from '../../../api/auth.api';
import { isBackendApiEnabled } from '../../../api/client';
import { useAuth } from '../../../contexts/AuthContext';
import { Logo } from '../../../layouts/AppShell';
import './auth.css';
import './auth-brands.css';

export function AuthPage({ register = false }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { login, socialLogin } = useAuth();
  const [loading, setLoading] = useState('');
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  // Set once the backend answers a login attempt with `requires_2fa: true` (HTTP 428).
  // The password form then also collects a TOTP code or backup code and resubmits.
  const [needs2FA, setNeeds2FA] = useState(false);
  const [totpToken, setTotpToken] = useState('');
  const [backupCode, setBackupCode] = useState('');
  const roleParam = searchParams.get('role') === 'teacher' ? 'teacher' : 'student';
  const next = searchParams.get('next') || (register && roleParam === 'teacher' ? '/teacher/dashboard' : '/student/dashboard');

  const handleSocialLogin = (provider) => {
    setLoading(provider);
    setError('');

    if (!isBackendApiEnabled) {
      setTimeout(() => {
        login({ id: `preview-${provider}-user`, name: roleParam === 'teacher' ? 'Maya Chen' : 'Sarah Chen', email: `preview-${provider}@learnwise.ai`, role: roleParam });
        navigate(next, { replace: true });
      }, 350);
      return;
    }

    const clientId = provider === 'google'
      ? import.meta.env.VITE_GOOGLE_CLIENT_ID
      : import.meta.env.VITE_FACEBOOK_APP_ID;

    if (!clientId) {
      setError(`${provider} login is not configured.`);
      setLoading('');
      return;
    }

    const redirectUri = `${window.location.origin}/auth/social-callback`;
    const state = JSON.stringify({ provider, role: roleParam, next });

    let authUrl;
    if (provider === 'google') {
      const scope = 'openid email profile';
      authUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=code&scope=${encodeURIComponent(scope)}&access_type=offline&prompt=consent&state=${encodeURIComponent(state)}`;
    } else if (provider === 'facebook') {
      const scope = 'email,public_profile';
      authUrl = `https://www.facebook.com/v23.0/dialog/oauth?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=code&scope=${encodeURIComponent(scope)}&state=${encodeURIComponent(state)}`;
    }

    if (authUrl) {
      window.location.href = authUrl;
    } else {
      setError(`Failed to start ${provider} login.`);
      setLoading('');
    }
  };

  const handleSocialCallback = async () => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const stateStr = params.get('state');
    const error = params.get('error');

    if (error) {
      setError(`Social login failed: ${params.get('error_description') || error}`);
      setLoading('');
      return;
    }

    if (code && stateStr) {
      let state;
      try {
        state = JSON.parse(stateStr);
      } catch {
        setError('Invalid state parameter.');
        setLoading('');
        return;
      }

      const { provider, role, next: nextPath } = state;

      // Map frontend role to backend role
      const roleMap = { student: 'etudiant', teacher: 'professeur' };
      const backendRole = roleMap[role] || 'etudiant';

      try {
        const result = await socialLogin(provider, null, backendRole, code);
        if (result.success) {
          navigate(nextPath || next, { replace: true });
        } else {
          setError(result.error);
          setLoading('');
        }
      } catch (err) {
        setError('Social login failed. Please try again.');
        setLoading('');
      }
    }
  };

  useEffect(() => {
    if (window.location.search.includes('code=')) {
      handleSocialCallback();
    }
  }, []);

  const submit = async event => {
    event.preventDefault();
    setError('');
    setFieldErrors({});
    const data = new FormData(event.currentTarget);
    const password = String(data.get('password') || '');
    const confirmation = String(data.get('confirmPassword') || '');
    if (register && password !== confirmation) {
      setError('Passwords do not match.');
      return;
    }
    const email = String(data.get('email') || '');
    const rawRole = String(data.get('role') || '');
    const roleMap = { student: 'etudiant', teacher: 'professeur' };
    // Default to 'student' if no role provided (e.g., no ?role= query param)
    const role = rawRole || roleParam || 'student';
    const backendRole = roleMap[role] || role;
    if (needs2FA && !totpToken && !backupCode) {
      setError('Enter the 6-digit code from your authenticator app, or a backup code.');
      return;
    }
    if (!isBackendApiEnabled) {
      login({
        id: 'preview-user',
        name: `${data.get('firstName') || (roleParam === 'teacher' ? 'Maya' : 'Sarah')} ${data.get('lastName') || 'Chen'}`,
        email: email || 'learner@example.test',
        role,
      });
      navigate(next, { replace: true });
      return;
    }
    setLoading('email');
    try {
      const response = register
        ? await authApi.register({ email, password, confirm_password: confirmation, first_name: String(data.get('firstName') || ''), last_name: String(data.get('lastName') || ''), role: backendRole })
        : await authApi.login({
            email,
            password,
            ...(totpToken ? { totp_token: totpToken } : {}),
            ...(backupCode ? { backup_code: backupCode } : {}),
          });
      if (!response?.user) {
        throw new Error('The server returned an incomplete sign-in response.');
      }
      const user = {
        ...response.user,
        name: response.user.name || `${response.user.first_name || ''} ${response.user.last_name || ''}`.trim() || response.user.email,
      };
      
      if (register) {
        // For registration, redirect to the "check your inbox" page (no tokens yet).
        // The email address travels via navigation state, not the URL.
        navigate('/auth/verify-email', { replace: true, state: { email: user.email } });
      } else {
        // For login, proceed normally (email must be verified)
        if (!user.email_verified) {
          setError('Please verify your email before logging in. Check your inbox for the verification link.');
          setLoading('');
          return;
        }
        if (!response?.access || !response?.refresh) {
          throw new Error('The server returned an incomplete sign-in response.');
        }
        login(user, { access: response.access, refresh: response.refresh });
        navigate(next, { replace: true });
      }
    } catch (cause) {
      if (cause?.response?.data?.requires_2fa) {
        // Either this was the first, password-only attempt (account has 2FA enabled)
        // or the TOTP/backup code just submitted was wrong. Either way, (keep) showing
        // the 2FA fields lets the person try again without retyping their password.
        setNeeds2FA(true);
        setError(cause?.response?.data?.detail || 'Enter your two-factor authentication code.');
        setLoading('');
        return;
      }
      // Map Django REST framework field errors (e.g. {"email": ["..."]}) to the matching inputs.
      const backendErrors = cause?.response?.data?.errors || {};
      const fieldMap = { email: 'email', password: 'password', confirm_password: 'confirmPassword', first_name: 'firstName', last_name: 'lastName' };
      const nextFieldErrors = {};
      Object.entries(backendErrors).forEach(([field, messages]) => {
        const inputName = fieldMap[field] || field;
        if (messages && messages.length) nextFieldErrors[inputName] = messages[0];
      });
      setFieldErrors(nextFieldErrors);
      const generalError = cause?.response?.data?.detail || cause.message || 'Could not authenticate. Check your details and try again.';
      setError(Object.keys(nextFieldErrors).length ? '' : generalError);
    } finally {
      setLoading('');
    }
  };

  const googleConfigured = isBackendApiEnabled && import.meta.env.VITE_GOOGLE_CLIENT_ID;
  const facebookConfigured = isBackendApiEnabled && import.meta.env.VITE_FACEBOOK_APP_ID;

  return <main className="auth-screen">
    <section className="auth-visual">
      <div className="auth-visual-top"><Logo dark /></div>
      <div className="auth-visual-copy"><span className="auth-kicker"><Sparkles size={14} /> A calmer way to learn</span><h1>Your curiosity deserves a <em>place to grow.</em></h1><p>Bring your questions, sources, and progress into one intelligent learning space.</p><div className="auth-proof"><div className="auth-proof-stack"><span>SC</span><span>MW</span><span>LM</span></div><span>Built for thoughtful progress</span></div></div>
      <div className="auth-map" aria-hidden="true"><span className="auth-map-line line-a" /><span className="auth-map-line line-b" /><span className="auth-map-node node-a">AI</span><span className="auth-map-node node-b">?</span><span className="auth-map-node node-c">✦</span><span className="auth-map-caption">Your learning map / 04</span></div>
      <p className="auth-visual-foot">Learnwise · Learn in your own shape</p>
    </section>
    <section className="auth-panel">
      <div className="auth-panel-inner">
        <div className="auth-mobile-brand"><Logo /></div>
        <div className="auth-heading"><span className="auth-kicker">{register ? 'CREATE YOUR ACCOUNT' : 'WELCOME BACK'}</span><h2>{register ? 'Start with one good question.' : 'Good to see you again.'}</h2><p>{register ? 'Build a learning space that follows your curiosity.' : 'Pick up exactly where your learning left off.'}</p></div>
        {location.state?.notice && <p className="form-error" role="status">{location.state.notice}</p>}
        <div className="social-login">
          {googleConfigured && (
            <button type="button" className="social-button google" onClick={() => handleSocialLogin('google')} disabled={Boolean(loading)}>
              <svg viewBox="0 0 24 24" width="18" height="18" style={{marginRight: 8}}>
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              <span>{loading === 'google' ? <Loader2 size={16} /> : 'Continue with Google'}</span>
            </button>
          )}
          {facebookConfigured && (
            <button type="button" className="social-button facebook" onClick={() => handleSocialLogin('facebook')} disabled={Boolean(loading)}>
              <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" style={{marginRight: 8}}>
                <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
              </svg>
              <span>{loading === 'facebook' ? <Loader2 size={16} /> : 'Continue with Facebook'}</span>
            </button>
          )}
          {!googleConfigured && !facebookConfigured && !isBackendApiEnabled && (
            <>
              <button type="button" className="social-button google" onClick={() => handleSocialLogin('google')} disabled={Boolean(loading)}>
                <strong className="brand-letter google-letter">G</strong>
                <span>{loading === 'google' ? 'Connecting…' : 'Continue with Google'}</span>
              </button>
              <button type="button" className="social-button facebook" onClick={() => handleSocialLogin('facebook')} disabled={Boolean(loading)}>
                <strong className="brand-letter facebook-letter">f</strong>
                <span>{loading === 'facebook' ? 'Connecting…' : 'Continue with Facebook'}</span>
              </button>
            </>
          )}
          {/* Face Login Button */}
          {isBackendApiEnabled && !register && (
            <button
              type="button"
              className="social-button face"
              onClick={() => navigate('/auth/face-login', { replace: true })}
            >
              <ScanFace size={18} style={{marginRight: 8}} />
              <span>Sign in with Face</span>
            </button>
          )}
        </div>
        <div className="auth-divider"><span>{(googleConfigured || facebookConfigured) ? 'Continue with your Learnwise account' : 'or use your email'}</span></div>
        <form className="auth-form-modern" onSubmit={submit}>
          {register && <div className="auth-field-row"><label>First name<input name="firstName" placeholder={roleParam === 'teacher' ? 'Maya' : 'Sarah'} autoComplete="given-name" required />{fieldErrors.firstName && <span className="field-error">{fieldErrors.firstName}</span>}</label><label>Last name<input name="lastName" placeholder="Chen" autoComplete="family-name" required />{fieldErrors.lastName && <span className="field-error">{fieldErrors.lastName}</span>}</label></div>}
          <label>Email address<input name="email" type="email" placeholder="you@example.com" autoComplete="email" required />{fieldErrors.email && <span className="field-error">{fieldErrors.email}</span>}</label>
          <label>Password<div className="password-field"><input name="password" type="password" placeholder="At least 8 characters" autoComplete={register ? 'new-password' : 'current-password'} minLength="8" required /><LockKeyhole size={15} /></div>{fieldErrors.password && <span className="field-error">{fieldErrors.password}</span>}</label>
          {register && <label>Confirm password<div className="password-field"><input name="confirmPassword" type="password" placeholder="Repeat your password" autoComplete="new-password" minLength="8" required /><LockKeyhole size={15} /></div>{fieldErrors.confirmPassword && <span className="field-error">{fieldErrors.confirmPassword}</span>}</label>}
          {register && <label>How will you use Learnwise?<select name="role" defaultValue={roleParam}><option value="student">As a student</option><option value="teacher">As an educator</option></select>{fieldErrors.role && <span className="field-error">{fieldErrors.role}</span>}</label>}
          {!register && needs2FA && (
            <div className="auth-2fa-fields">
              <label>Authenticator code<input value={totpToken} onChange={event => setTotpToken(event.target.value)} inputMode="numeric" placeholder="6-digit code" maxLength={6} autoComplete="one-time-code" autoFocus /></label>
              <label>or a backup code<input value={backupCode} onChange={event => setBackupCode(event.target.value)} placeholder="XXXXX-XXXXX" maxLength={21} /></label>
            </div>
          )}
          {!register && <div className="auth-form-meta"><label className="remember-label"><input type="checkbox" /> Remember me</label><Link to="/auth/forgot-password">Forgot password?</Link></div>}
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="auth-submit" type="submit" disabled={Boolean(loading)}>{loading === 'email' ? 'Connecting…' : loading === 'google' || loading === 'facebook' ? <Loader2 size={16} /> : register ? 'Create my account' : 'Log in'} <ArrowRight size={16} /></button>
        </form>
        <p className="auth-legal">By continuing, you agree to Learnwise&apos;s <a href="/terms">Terms</a> and <a href="/privacy">Privacy Policy</a>.</p>
        <p className="auth-switch">{register ? 'Already have an account?' : 'New to Learnwise?'} <Link to={register ? '/auth/login' : '/auth/register'}>{register ? 'Log in' : 'Create an account'}</Link></p>
        <div className="auth-secure"><Check size={14} /> {isBackendApiEnabled ? 'Secure sign-in through the Learnwise service' : 'Preview sign-in · credentials are not sent to a server'}</div>
      </div>
    </section>
  </main>;
}