import React, { useEffect, useState } from 'react';
import { Bell, Check, LockKeyhole, Save, UserRound } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader } from '../../../components/shared/Primitives';
import { ErrorState, LoadingState } from '../../../components/ui/States';
import { authApi } from '../../../api/auth.api';
import { isBackendApiEnabled } from '../../../api/client';
import { useAuth } from '../../../contexts/AuthContext';

function profileFrom(user = {}) {
  const [first = '', ...last] = (user.name || '').split(' ');
  return {
    first_name: user.first_name || first,
    last_name: user.last_name || last.join(' '),
    email: user.email || '',
  };
}

export function SettingsPage({ role }) {
  const { user, updateUser } = useAuth();
  const [profile, setProfile] = useState(() => profileFrom(user));
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const profileQuery = useQuery({ queryKey: ['account', 'me'], queryFn: authApi.me, enabled: isBackendApiEnabled });
  useEffect(() => {
    if (profileQuery.data) setProfile(profileFrom(profileQuery.data.user || profileQuery.data));
  }, [profileQuery.data]);
  const saveProfile = async event => {
    event.preventDefault();
    setSaving(true);
    setSaved(false);
    setError('');
    try {
      const updated = isBackendApiEnabled
        ? await authApi.updateProfile(profile)
        : { ...user, ...profile, name: `${profile.first_name} ${profile.last_name}`.trim() };
      const currentUser = updated.user || updated;
      updateUser({ ...currentUser, name: currentUser.name || `${currentUser.first_name || ''} ${currentUser.last_name || ''}`.trim() || currentUser.email });
      setProfile(profileFrom(currentUser));
      setSaved(true);
    } catch (cause) {
      setError(cause?.response?.data?.detail || 'Your profile could not be saved. Your edits are still here; retry.');
    } finally {
      setSaving(false);
    }
  };
  if (isBackendApiEnabled && profileQuery.isLoading) return <AppShell role={role}><PageHeader eyebrow={`${role} workspace`} title="Workspace settings"/><LoadingState label="Loading your account profile"/></AppShell>;
  if (isBackendApiEnabled && profileQuery.isError) return <AppShell role={role}><PageHeader eyebrow={`${role} workspace`} title="Workspace settings"/><ErrorState message="Your profile could not be loaded." action={<Button onClick={() => void profileQuery.refetch()}>Retry</Button>}/></AppShell>;
  return <AppShell role={role}><PageHeader eyebrow={`${role} workspace`} title="Workspace settings" description="Manage account details and notification preferences."/><form onSubmit={saveProfile}><div className="settings-layout"><section className="settings-card"><div className="settings-card-head"><UserRound size={18}/><div><h2>Profile</h2><p>Keep your workspace identity current.</p></div></div><label>First name<input value={profile.first_name} onChange={event => setProfile(current => ({ ...current, first_name: event.target.value }))} autoComplete="given-name"/></label><label>Last name<input value={profile.last_name} onChange={event => setProfile(current => ({ ...current, last_name: event.target.value }))} autoComplete="family-name"/></label><label>Email address<input type="email" value={profile.email} onChange={event => setProfile(current => ({ ...current, email: event.target.value }))} autoComplete="email"/></label></section><section className="settings-card"><div className="settings-card-head"><Bell size={18}/><div><h2>Notifications</h2><p>Choose which updates you would like to receive.</p></div></div><label className="setting-toggle"><input type="checkbox" defaultChecked/> Learning reminders</label><label className="setting-toggle"><input type="checkbox" defaultChecked/> Weekly progress digest</label><label className="setting-toggle"><input type="checkbox"/> Product updates</label></section><section className="settings-card"><div className="settings-card-head"><LockKeyhole size={18}/><div><h2>Security</h2><p>Protect your account and manage active sessions.</p></div></div>{isBackendApiEnabled && <p className="settings-note">Your account uses authenticated sessions.</p>}</section></div>{error && <p className="form-error" role="alert">{error}</p>}<button type="submit" className="button" disabled={saving}><Save size={15}/> {saving ? 'Saving…' : 'Save profile'}</button>{saved && <span className="settings-saved" role="status"><Check size={14}/> Profile saved.</span>}</form></AppShell>;
}
