import React, { useState } from 'react';
import { ArrowRight, Check, LockKeyhole, Sparkles } from 'lucide-react';
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
  const { login } = useAuth();
  const [loading, setLoading] = useState('');
  const [error, setError] = useState('');
  const roleParam = searchParams.get('role') === 'teacher' ? 'teacher' : 'student';
  const next = searchParams.get('next') || (register && roleParam === 'teacher' ? '/teacher/dashboard' : '/student/dashboard');

  const finishPreviewLogin = provider => {
    setLoading(provider);
    window.setTimeout(() => {
      login({ id: `preview-${provider}-user`, name: roleParam === 'teacher' ? 'Maya Chen' : 'Sarah Chen', email: `preview-${provider}@learnwise.ai`, role: roleParam });
      navigate(next, { replace: true });
    }, 350);
  };

  const submit = async event => {
    event.preventDefault();
    setError('');
    const data = new FormData(event.currentTarget);
    const password = String(data.get('password') || '');
    const confirmation = String(data.get('confirmPassword') || '');
    if (register && password !== confirmation) {
      setError('Passwords do not match.');
      return;
    }
    const email = String(data.get('email') || '');
    const role = String(data.get('role') || roleParam);
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
        ? await authApi.register({ email, password, first_name: String(data.get('firstName') || ''), last_name: String(data.get('lastName') || ''), role })
        : await authApi.login({ email, password });
      if (!response?.user || !response.access || !response.refresh) {
        throw new Error('The server returned an incomplete sign-in response.');
      }
      const user = {
        ...response.user,
        name: response.user.name || `${response.user.first_name || ''} ${response.user.last_name || ''}`.trim() || response.user.email,
      };
      login(user, { access: response.access, refresh: response.refresh });
      navigate(next, { replace: true });
    } catch (cause) {
      const validationError = Object.values(cause?.response?.data?.errors || {}).flat()[0];
      setError(cause?.response?.data?.detail || validationError || cause.message || 'Could not authenticate. Check your details and try again.');
    } finally {
      setLoading('');
    }
  };

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
        {!isBackendApiEnabled && <div className="social-login"><button type="button" className="social-button google" onClick={() => finishPreviewLogin('google')} disabled={Boolean(loading)}><strong className="brand-letter google-letter">G</strong><span>{loading === 'google' ? 'Connecting…' : 'Continue with Google'}</span></button><button type="button" className="social-button facebook" onClick={() => finishPreviewLogin('facebook')} disabled={Boolean(loading)}><strong className="brand-letter facebook-letter">f</strong><span>{loading === 'facebook' ? 'Connecting…' : 'Continue with Facebook'}</span></button></div>}
        <div className="auth-divider"><span>{isBackendApiEnabled ? 'Continue with your Learnwise account' : 'or use your email'}</span></div>
        <form className="auth-form-modern" onSubmit={submit}>
          {register && <div className="auth-field-row"><label>First name<input name="firstName" placeholder={roleParam === 'teacher' ? 'Maya' : 'Sarah'} autoComplete="given-name" required /></label><label>Last name<input name="lastName" placeholder="Chen" autoComplete="family-name" required /></label></div>}
          <label>Email address<input name="email" type="email" placeholder="you@example.com" autoComplete="email" required /></label>
          <label>Password<div className="password-field"><input name="password" type="password" placeholder="At least 8 characters" autoComplete={register ? 'new-password' : 'current-password'} minLength="8" required /><LockKeyhole size={15} /></div></label>
          {register && <label>Confirm password<div className="password-field"><input name="confirmPassword" type="password" placeholder="Repeat your password" autoComplete="new-password" minLength="8" required /><LockKeyhole size={15} /></div></label>}
          {register && <label>How will you use Learnwise?<select name="role" defaultValue={roleParam}><option value="student">As a student</option><option value="teacher">As an educator</option></select></label>}
          {!register && <div className="auth-form-meta"><label className="remember-label"><input type="checkbox" /> Remember me</label><Link to="/auth/forgot-password">Forgot password?</Link></div>}
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="auth-submit" type="submit" disabled={Boolean(loading)}>{loading === 'email' ? 'Connecting…' : register ? 'Create my account' : 'Log in'} <ArrowRight size={16} /></button>
        </form>
        <p className="auth-legal">By continuing, you agree to Learnwise’s <a href="/terms">Terms</a> and <a href="/privacy">Privacy Policy</a>.</p>
        <p className="auth-switch">{register ? 'Already have an account?' : 'New to Learnwise?'} <Link to={register ? '/auth/login' : '/auth/register'}>{register ? 'Log in' : 'Create an account'}</Link></p>
        <div className="auth-secure"><Check size={14} /> {isBackendApiEnabled ? 'Secure sign-in through the Learnwise service' : 'Preview sign-in · credentials are not sent to a server'}</div>
      </div>
    </section>
  </main>;
}
