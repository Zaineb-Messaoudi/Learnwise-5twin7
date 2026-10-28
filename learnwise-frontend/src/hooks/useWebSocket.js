import { useEffect, useRef, useState } from 'react';
import { createWebSocket } from '../api/client';
export function useWebSocket(path, enabled = true) {
    const socketRef = useRef(null);
    const [status, setStatus] = useState('disconnected');
    const [lastMessage, setLastMessage] = useState(null);
    useEffect(() => {
        if (!enabled)
            return;
        let retryTimer;
        let retryDelay = 1000;
        let disposed = false;
        const connect = (retrying = false) => {
            setStatus(retrying ? 'reconnecting' : 'connecting');
            const socket = createWebSocket(path);
            socketRef.current = socket;
            socket.onopen = () => { retryDelay = 1000; setStatus('connected'); };
            socket.onmessage = event => {
                try {
                    setLastMessage(JSON.parse(event.data));
                }
                catch {
                    setLastMessage(event.data);
                }
            };
            socket.onerror = () => setStatus('error');
            socket.onclose = event => {
                const terminal = [4001, 4003, 4004, 4401, 4403, 4404].includes(event.code);
                if (!disposed && !terminal) {
                    retryTimer = window.setTimeout(() => connect(true), retryDelay);
                    retryDelay = Math.min(retryDelay * 2, 30000);
                } else {
                    setStatus('disconnected');
                }
            };
        };
        connect();
        return () => { disposed = true; if (retryTimer)
            window.clearTimeout(retryTimer); socketRef.current?.close(); };
    }, [enabled, path]);
    const send = (payload) => { if (socketRef.current?.readyState === WebSocket.OPEN)
        socketRef.current.send(JSON.stringify(payload)); };
    return { status, lastMessage, send };
}
