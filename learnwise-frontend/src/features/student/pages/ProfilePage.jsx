import React, { useState, useEffect } from 'react';
import { useAuth } from '../../../contexts/AuthContext';
import { User, Mail, Lock, Shield, Camera, Save, AlertCircle, CheckCircle } from 'lucide-react';
import './ProfilePage.css';

export function ProfilePage() {
  const { user, updateProfile, changePassword, loading, error, clearError } = useAuth();
  const [activeTab, setActiveTab] = useState('profile');
  const [profileData, setProfileData] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    username: user?.username || '',
    phone: user?.phone || '',
    bio: user?.bio || '',
  });
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });
  const [profileError, setProfileError] = useState('');
  const [profileSuccess, setProfileSuccess] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState('');

  useEffect(() => {
    if (user) {
      setProfileData({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        username: user.username || '',
        phone: user.phone || '',
        bio: user.bio || '',
      });
    }
  }, [user]);

  const handleProfileChange = (e) => {
    const { name, value } = e.target;
    setProfileData(prev => ({ ...prev, [name]: value }));
    setProfileError('');
    setProfileSuccess('');
  };

  const handlePasswordChange = (e) => {
    const { name, value } = e.target;
    setPasswordData(prev => ({ ...prev, [name]: value }));
    setPasswordError('');
    setPasswordSuccess('');
  };

  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    setProfileError('');
    setProfileSuccess('');
    const result = await updateProfile(profileData);
    if (result.success) {
      setProfileSuccess('Profile updated successfully!');
    } else {
      setProfileError(result.error);
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setPasswordError('');
    setPasswordSuccess('');
    if (passwordData.new_password !== passwordData.confirm_password) {
      setPasswordError('New passwords do not match.');
      return;
    }
    if (passwordData.new_password.length < 8) {
      setPasswordError('Password must be at least 8 characters.');
      return;
    }
    const result = await changePassword({
      current_password: passwordData.current_password,
      new_password: passwordData.new_password,
      confirm_password: passwordData.confirm_password,
    });
    if (result.success) {
      setPasswordSuccess('Password changed successfully!');
      setPasswordData({ current_password: '', new_password: '', confirm_password: '' });
    } else {
      setPasswordError(result.error);
    }
  };

  const getRoleLabel = (role) => {
    const labels = {
      etudiant: 'Student',
      professeur: 'Educator',
      admin: 'Administrator',
    };
    return labels[role] || role;
  };

  const getInitials = () => {
    if (user?.first_name || user?.last_name) {
      return `${user.first_name?.[0] || ''}${user.last_name?.[0] || ''}`.toUpperCase();
    }
    return user?.email?.[0]?.toUpperCase() || 'U';
  };

  return (
    <div className="profile-page">
      <div className="profile-header">
        <div className="profile-avatar-section">
          <div className="avatar-large">{getInitials()}</div>
          <div className="profile-info">
            <h1>{user?.name || user?.email}</h1>
            <div className="role-badge">{getRoleLabel(user?.role)}</div>
            <p className="email">{user?.email}</p>
          </div>
        </div>
        {user?.email_verified ? (
          <div className="verified-badge">
            <Shield size={16} />
            <span>Email verified</span>
          </div>
        ) : (
          <div className="unverified-banner">
            <AlertCircle size={16} />
            <span>Email not verified</span>
          </div>
        )}
      </div>

      <div className="profile-tabs">
        <button
          className={`tab-button ${activeTab === 'profile' ? 'active' : ''}`}
          onClick={() => setActiveTab('profile')}
        >
          <User size={18} /> Profile
        </button>
        <button
          className={`tab-button ${activeTab === 'security' ? 'active' : ''}`}
          onClick={() => setActiveTab('security')}
        >
          <Lock size={18} /> Security
        </button>
      </div>

      {activeTab === 'profile' && (
        <form onSubmit={handleProfileSubmit} className="profile-form">
          <div className="form-section">
            <h2>Personal Information</h2>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="first_name">First Name</label>
                <input
                  id="first_name"
                  name="first_name"
                  type="text"
                  value={profileData.first_name}
                  onChange={handleProfileChange}
                  placeholder="First name"
                />
              </div>
              <div className="form-group">
                <label htmlFor="last_name">Last Name</label>
                <input
                  id="last_name"
                  name="last_name"
                  type="text"
                  value={profileData.last_name}
                  onChange={handleProfileChange}
                  placeholder="Last name"
                />
              </div>
            </div>
            <div className="form-group">
              <label htmlFor="username">Username</label>
              <input
                id="username"
                name="username"
                type="text"
                value={profileData.username}
                onChange={handleProfileChange}
                placeholder="Username"
              />
            </div>
            <div className="form-group">
              <label htmlFor="phone">Phone Number</label>
              <input
                id="phone"
                name="phone"
                type="tel"
                value={profileData.phone}
                onChange={handleProfileChange}
                placeholder="+1 (555) 000-0000"
              />
            </div>
            <div className="form-group">
              <label htmlFor="bio">Bio</label>
              <textarea
                id="bio"
                name="bio"
                value={profileData.bio}
                onChange={handleProfileChange}
                placeholder="Tell us about yourself..."
                rows={4}
              />
            </div>
          </div>

          {profileError && <div className="form-message error">{profileError}</div>}
          {profileSuccess && <div className="form-message success">{profileSuccess}</div>}

          <button type="submit" className="btn-save" disabled={loading}>
            <Save size={18} /> Save Changes
          </button>
        </form>
      )}

      {activeTab === 'security' && (
        <form onSubmit={handlePasswordSubmit} className="profile-form">
          <div className="form-section">
            <h2>Change Password</h2>
            <div className="form-group">
              <label htmlFor="current_password">Current Password</label>
              <input
                id="current_password"
                name="current_password"
                type="password"
                value={passwordData.current_password}
                onChange={handlePasswordChange}
                placeholder="Enter current password"
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="new_password">New Password</label>
              <input
                id="new_password"
                name="new_password"
                type="password"
                value={passwordData.new_password}
                onChange={handlePasswordChange}
                placeholder="Enter new password (min 8 chars)"
                minLength={8}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="confirm_password">Confirm New Password</label>
              <input
                id="confirm_password"
                name="confirm_password"
                type="password"
                value={passwordData.confirm_password}
                onChange={handlePasswordChange}
                placeholder="Confirm new password"
                minLength={8}
                required
              />
            </div>
          </div>

          {passwordError && <div className="form-message error">{passwordError}</div>}
          {passwordSuccess && <div className="form-message success">{passwordSuccess}</div>}

          <button type="submit" className="btn-save" disabled={loading}>
            <Lock size={18} /> Update Password
          </button>
        </form>
      )}
    </div>
  );
}