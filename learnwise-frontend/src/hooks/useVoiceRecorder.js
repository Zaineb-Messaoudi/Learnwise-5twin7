import { useCallback, useEffect, useRef, useState } from 'react';

export function useVoiceRecorder() {
    const recorder = useRef(null);
    const stream = useRef(null);
    const chunks = useRef([]);
    const cancelled = useRef(false);
    const requestId = useRef(0);
    const [state, setState] = useState('idle');
    const [duration, setDuration] = useState(0);
    const [audio, setAudio] = useState(null);
    const timer = useRef(null);
    const start = useCallback(async () => {
        if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
            setState('unsupported');
            return;
        }
        cancelled.current = false;
        const thisRequest = ++requestId.current;
        setState('requesting');
        const grantedStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        if (requestId.current !== thisRequest) {
            grantedStream.getTracks().forEach(track => track.stop());
            return;
        }
        stream.current = grantedStream;
        const recordingChunks = [];
        chunks.current = recordingChunks;
        setAudio(null);
        const next = new MediaRecorder(grantedStream);
        recorder.current = next;
        next.ondataavailable = event => { if (event.data.size) recordingChunks.push(event.data); };
        next.onstart = () => {
            if (requestId.current !== thisRequest) return;
            setState('recording');
            setDuration(0);
            timer.current = window.setInterval(() => setDuration(value => value + 1), 1000);
        };
        next.onstop = () => {
            grantedStream.getTracks().forEach(track => track.stop());
            if (stream.current === grantedStream) stream.current = null;
            if (timer.current) window.clearInterval(timer.current);
            timer.current = null;
            if (!cancelled.current && requestId.current === thisRequest) {
                if (recordingChunks.length) setAudio(new Blob(recordingChunks, { type: next.mimeType || 'audio/webm' }));
                setState('stopped');
            }
        };
        next.start();
    }, []);
    const stop = useCallback(() => recorder.current?.state === 'recording' && recorder.current.stop(), []);
    const reset = useCallback(() => {
        cancelled.current = true;
        requestId.current += 1;
        if (timer.current) window.clearInterval(timer.current);
        timer.current = null;
        const activeRecorder = recorder.current;
        if (activeRecorder && activeRecorder.state !== 'inactive') activeRecorder.stop();
        stream.current?.getTracks().forEach(track => track.stop());
        stream.current = null;
        recorder.current = null;
        chunks.current = [];
        setAudio(null);
        setState('idle');
        setDuration(0);
    }, []);
    useEffect(() => () => {
        cancelled.current = true;
        requestId.current += 1;
        if (timer.current) window.clearInterval(timer.current);
        if (recorder.current && recorder.current.state !== 'inactive') recorder.current.stop();
        stream.current?.getTracks().forEach(track => track.stop());
    }, []);
    return { state, duration, audio, start, stop, reset };
}
