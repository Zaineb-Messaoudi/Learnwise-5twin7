import React from 'react';
import { createWebSocket } from './client';

/**
 * Presence API - WebSocket-based real-time presence tracking
 * 
 * Connects to ws://localhost:8000/ws/content/courses/{course_id}/presence/
 * to track which students are currently viewing a course page.
 */

// Presence state types
const STATE_CONNECTING = 'connecting';
const STATE_OPEN = 'open';
const STATE_CLOSED = 'closed';
const STATE_ERROR = 'error';

// Message types
const MESSAGE_JOIN = 'join';
const MESSAGE_LEAVE = 'leave';
const MESSAGE_HEARTBEAT = 'heartbeat';
const MESSAGE_PRESENCE_UPDATE = 'presence_update';

/**
 * PresenceHook - React hook for course presence tracking
 * 
 * @param {string} courseId - The course ID to track presence for
 * @param {Object} options - Configuration options
 * @param {number} options.heartbeatInterval - Heartbeat interval in ms (default: 30000)
 * @returns {Object} Presence state and control functions
 */
export function usePresence(courseId, options = {}) {
    const {
        heartbeatInterval = 30000,
        onJoin,
        onLeave,
        onPresenceUpdate,
        onError,
        onStateChange
    } = options;

    const [state, setState] = React.useState(STATE_CONNECTING);
    const [activeUsers, setActiveUsers] = React.useState([]);
    const [error, setError] = React.useState(null);
    const wsRef = React.useRef(null);
    const heartbeatRef = React.useRef(null);

    // Connect to WebSocket
    React.useEffect(() => {
        const token = window.localStorage.getItem('learnwise:access-token');
        const url = token
            ? `ws://localhost:8000/ws/content/courses/${courseId}/presence/?token=${token}`
            : `ws://localhost:8000/ws/content/courses/${courseId}/presence/`;
        wsRef.current = createWebSocket(url);

        wsRef.current.onopen = () => {
            setState(STATE_OPEN);
            setError(null);
            if (onStateChange) onStateChange(STATE_OPEN);

            // Send join message
            if (wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({
                    type: MESSAGE_JOIN,
                    courseId: courseId
                }));
                if (onJoin) onJoin();
            }

            // Start heartbeat
            heartbeatRef.current = setInterval(() => {
                if (wsRef.current.readyState === WebSocket.OPEN) {
                    wsRef.current.send(JSON.stringify({
                        type: MESSAGE_HEARTBEAT,
                        courseId: courseId
                    }));
                }
            }, heartbeatInterval);
        };

        wsRef.current.onmessage = (event) => {
            const message = JSON.parse(event.data);
            
            if (message.type === MESSAGE_PRESENCE_UPDATE) {
                setActiveUsers(message.users || []);
                if (onPresenceUpdate) onPresenceUpdate(message.users || []);
            }
        };

        wsRef.current.onerror = (event) => {
            setState(STATE_ERROR);
            setError('WebSocket error');
            if (onError) onError(event);
            if (onStateChange) onStateChange(STATE_ERROR);
        };

        wsRef.current.onclose = () => {
            setState(STATE_CLOSED);
            clearInterval(heartbeatRef.current);
            if (onStateChange) onStateChange(STATE_CLOSED);

            // Attempt reconnection after 3 seconds
            setTimeout(() => {
                if (state === STATE_CLOSED) {
                    // Reconnect - will be handled by useEffect re-run
                }
            }, 3000);
        };

        // Cleanup on unmount
        return () => {
            if (wsRef.current) {
                wsRef.current.send(JSON.stringify({
                    type: MESSAGE_LEAVE,
                    courseId: courseId
                }));
                wsRef.current.close();
            }
            if (heartbeatRef.current) {
                clearInterval(heartbeatRef.current);
            }
        };
    }, [courseId, heartbeatInterval, onJoin, onLeave, onPresenceUpdate, onError, onStateChange]);

    // Expose control functions
    const join = () => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
                type: MESSAGE_JOIN,
                courseId: courseId
            }));
        }
    };

    const leave = () => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
                type: MESSAGE_LEAVE,
                courseId: courseId
            }));
        }
    };

    return {
        state,
        activeUsers,
        error,
        join,
        leave,
        totalActive: activeUsers.length
    };
}

/**
 * PresenceContext - Context provider for course presence
 * 
 * Provides presence state to all descendants via React context.
 * 
 * Usage:
 * <PresenceProvider courseId="course_123">
 *   <CourseDetailPage />
 * </PresenceProvider>
 */

const PresenceContext = React.createContext({
    state: STATE_CONNECTING,
    activeUsers: [],
    error: null,
    join: () => {},
    leave: () => {},
    totalActive: 0
});

/**
 * PresenceProvider - React context provider for presence tracking
 */
export function PresenceProvider({ courseId, children, ...props }) {
    const presence = usePresence(courseId, props);
    return (
        <PresenceContext.Provider value={presence}>
            {children}
        </PresenceContext.Provider>
    );
}

/**
 * usePresenceValue - Helper to get presence value from context
 * 
 * @param {Object} context - React context value
 * @returns {Object} Presence state
 */
export function usePresenceValue(context) {
    return context || {
        state: STATE_CONNECTING,
        activeUsers: [],
        error: null,
        join: () => {},
        leave: () => {},
        totalActive: 0
    };
}