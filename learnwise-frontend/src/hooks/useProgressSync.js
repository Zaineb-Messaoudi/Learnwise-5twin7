import { useEffect, useRef, useState, useCallback } from 'react';
import { createWebSocket } from '../api/client';
import { isBackendApiEnabled } from '../api/client';

// Property names that must never be used as a dynamic object key, since
// writing to them can pollute the object's prototype chain.
const UNSAFE_KEYS = new Set(['__proto__', 'constructor', 'prototype']);

// Returns a safe string key derived from untrusted input, or null if the
// value would be dangerous to use as a computed property name.
const safeKey = (value) => {
  const key = String(value ?? '');
  return UNSAFE_KEYS.has(key) ? null : key;
};

export function useProgressSync(userId, enabled = true) {
  const socketRef = useRef(null);
  const [status, setStatus] = useState('disconnected');
  const [progressUpdates, setProgressUpdates] = useState([]);
  const [latestProgress, setLatestProgress] = useState({});
  const [notifications, setNotifications] = useState([]);
  const reconnectTimeoutRef = useRef(null);
  const handlersRef = useRef(new Map());
  const shouldReconnectRef = useRef(false);
  const sanitizeForLog = (value) => String(value ?? '').replace(/[\r\n]/g, '');

  const connect = useCallback(() => {
    if (!enabled || !isBackendApiEnabled || !userId) return;
    shouldReconnectRef.current = true;
    setStatus('connecting');
    // The authenticated analytics socket is scoped to the current user on the
    // server. Do not put the user id in the URL: it is both redundant and was
    // pointing to a route that does not exist in Channels.
    const wsUrl = '/ws/analytics/';
    const socket = createWebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      setStatus('connected');
      console.log('[ProgressSync] Connected');
    };

    socket.onmessage = (event) => {
      try {
        const rawMessage = JSON.parse(event.data);
        const eventTypes = {
          'progress.updated': 'progress_update',
          'achievement.earned': 'achievement_unlocked',
          'session.updated': 'session_update',
          'quiz.available': 'quiz_available',
          'material.ready': 'material_ready',
        };
        const message = rawMessage.event
          ? { ...rawMessage.data, type: eventTypes[rawMessage.event] || rawMessage.event }
          : rawMessage;
        console.log('[ProgressSync] Received:', message);

        switch (message.type) {
          case 'progress_update': {
            // message.course_id comes from the server payload and is
            // untrusted; guard it before using it as a computed property
            // name to avoid a prototype-pollution write (e.g. "__proto__").
            const courseKey = safeKey(message.course_id);
            if (courseKey !== null) {
              setLatestProgress(prev => ({
                ...prev,
                [courseKey]: Number(message.completion_percentage ?? message.progress ?? 0) / (
                  message.completion_percentage !== undefined ? 100 : 1
                ),
              }));
            } else {
              console.warn('[ProgressSync] Rejected unsafe course_id key:', sanitizeForLog(message.course_id));
            }
            setProgressUpdates(prev => [message, ...prev.slice(0, 49)]);
            handlersRef.current.get('progress')?.(message);
            break;
          }
          case 'session_update':
            handlersRef.current.get('session')?.(message);
            break;
          case 'achievement_unlocked':
            setNotifications(prev => [{ ...message, id: Date.now(), read: false }, ...prev.slice(0, 19)]);
            handlersRef.current.get('achievement')?.(message);
            break;
          case 'quiz_available':
            setNotifications(prev => [{ ...message, id: Date.now(), read: false, type: 'quiz' }, ...prev.slice(0, 19)]);
            handlersRef.current.get('quiz')?.(message);
            break;
          case 'material_ready':
            setNotifications(prev => [{ ...message, id: Date.now(), read: false, type: 'material' }, ...prev.slice(0, 19)]);
            handlersRef.current.get('material')?.(message);
            break;
          default:
            if (message.type !== 'connected') {
              console.log('[ProgressSync] Unknown message type:', sanitizeForLog(message.type));
            }
        }
      } catch (err) {
        console.warn('[ProgressSync] Failed to parse message:', err);
      }
    };

    socket.onerror = (err) => {
      console.error('[ProgressSync] Error:', err);
      setStatus('error');
    };

    socket.onclose = () => {
      console.log('[ProgressSync] Disconnected');
      setStatus('disconnected');
      if (shouldReconnectRef.current && enabled && isBackendApiEnabled && userId) {
        reconnectTimeoutRef.current = setTimeout(connect, 3000);
      }
    };
  }, [enabled, userId]);

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;
    if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
    setStatus('disconnected');
  }, []);

  const on = useCallback((event, handler) => {
    handlersRef.current.set(event, handler);
    return () => handlersRef.current.delete(event);
  }, []);

  const send = useCallback((payload) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(payload));
    }
  }, []);

  const markNotificationRead = useCallback((id) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
  }, []);

  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return {
    status,
    progressUpdates,
    latestProgress,
    notifications,
    unreadCount: notifications.filter(n => !n.read).length,
    on,
    send,
    markNotificationRead,
    clearNotifications,
    connect,
    disconnect,
  };
}

export default useProgressSync;
