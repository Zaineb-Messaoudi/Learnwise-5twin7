import { useEffect, useRef, useState, useCallback } from 'react';
import { createWebSocket } from '../api/client';
import { isBackendApiEnabled } from '../api/client';

export function useProgressSync(userId, enabled = true) {
  const socketRef = useRef(null);
  const [status, setStatus] = useState('disconnected');
  const [progressUpdates, setProgressUpdates] = useState([]);
  // Keyed by course_id, a value that comes straight off the WebSocket
  // payload and is therefore untrusted. A Map stores the key as plain
  // data rather than as an object property, so there is no way for a
  // value like "__proto__" to be interpreted as a property name and
  // pollute an object's prototype chain.
  const [latestProgress, setLatestProgress] = useState(new Map());
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
        // message originates from the server and may contain attacker-
        // controlled strings (e.g. embedded newlines) that could be used
        // to forge fake log entries, so strip line breaks before logging.
        console.log('[ProgressSync] Received:', sanitizeForLog(JSON.stringify(message)));

        switch (message.type) {
          case 'progress_update': {
            const courseKey = String(message.course_id ?? '');
            const ratio = Number(message.completion_percentage ?? message.progress ?? 0) / (
              message.completion_percentage !== undefined ? 100 : 1
            );
            setLatestProgress(prev => {
              const next = new Map(prev);
              next.set(courseKey, ratio);
              return next;
            });
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
