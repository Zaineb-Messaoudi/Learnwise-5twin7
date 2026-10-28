import React, { useState, useRef, useEffect } from 'react';
import { Bell, Check, X, AlertCircle, Award, BookOpen, Zap, Loader2, ExternalLink } from 'lucide-react';
import { useProgressSyncContext } from '../../contexts/ProgressSyncContext';

export function NotificationBell() {
  const { notifications, unreadCount, markNotificationRead, clearNotifications, status } = useProgressSyncContext();
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getNotificationIcon = (type) => {
    switch (type) {
      case 'achievement': return <Award size={16} className="text-lime" />;
      case 'quiz': return <Zap size={16} className="text-cyan" />;
      case 'material': return <BookOpen size={16} className="text-cobalt" />;
      default: return <AlertCircle size={16} className="text-coral" />;
    }
  };

  const getNotificationTitle = (notification) => {
    switch (notification.type) {
      case 'achievement_unlocked': return `Achievement: ${notification.achievement?.title || 'New badge'}`;
      case 'quiz_available': return `New quiz: ${notification.quiz?.title || 'Practice quiz'}`;
      case 'material_ready': return `Material ready: ${notification.material?.title || 'Course content'}`;
      case 'progress_update': return `Progress update: ${Math.round(notification.progress * 100)}%`;
      default: return notification.title || 'Notification';
    }
  };

  const getNotificationDescription = (notification) => {
    if (notification.message) return notification.message;
    switch (notification.type) {
      case 'achievement_unlocked': return 'You\'ve earned a new achievement!';
      case 'quiz_available': return 'A new practice quiz is available for you.';
      case 'material_ready': return 'Your course material has finished processing.';
      case 'progress_update': return 'Your learning progress has been updated.';
      default: return 'You have a new notification.';
    }
  };

  const handleNotificationClick = (notification, index) => {
    markNotificationRead(notification.id);
    if (notification.action_url) {
      window.location.href = notification.action_url;
    }
  };

  return (
    <div className="notification-bell-wrapper" ref={dropdownRef}>
      <button
        className={`notification-bell ${unreadCount > 0 ? 'has-unread' : ''}`}
        onClick={() => setOpen(!open)}
        aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ''}`}
        aria-expanded={open}
        aria-haspopup="true"
      >
        <Bell size={20} />
        {unreadCount > 0 && <span className="notification-badge">{unreadCount > 9 ? '9+' : unreadCount}</span>}
      </button>

      {open && (
        <div className="notification-dropdown" role="menu">
          <div className="notification-header">
            <h3>Notifications</h3>
            {notifications.length > 0 && (
              <button className="clear-all" onClick={clearNotifications}>Clear all</button>
            )}
          </div>
          <div className="notification-list" role="list">
            {notifications.length === 0 ? (
              <div className="notification-empty">
                <Bell size={24} />
                <p>No notifications yet</p>
                <span>You&apos;ll see updates here when they arrive</span>
              </div>
            ) : (
              notifications.map((notification, index) => (
                <button
                  key={notification.id || index}
                  className={`notification-item ${!notification.read ? 'unread' : ''}`}
                  onClick={() => handleNotificationClick(notification, index)}
                  role="menuitem"
                >
                  <div className="notification-icon">{getNotificationIcon(notification.type)}</div>
                  <div className="notification-content">
                    <div className="notification-title">{getNotificationTitle(notification)}</div>
                    <div className="notification-desc">{getNotificationDescription(notification)}</div>
                    <div className="notification-time">{new Date(notification.timestamp || Date.now()).toLocaleTimeString()}</div>
                  </div>
                  {!notification.read && <Check size={14} className="unread-dot" />}
                </button>
              ))
            )}
          </div>
          {status === 'connecting' || status === 'reconnecting' && (
            <div className="notification-status">
              <Loader2 size={14} className="spin" /> Connecting…
            </div>
          )}
          {status === 'error' && (
            <div className="notification-status error">
              <AlertCircle size={14} /> Connection lost. Retrying…
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default NotificationBell;