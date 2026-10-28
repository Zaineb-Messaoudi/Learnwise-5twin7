import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Eye, EyeOff, AlertCircle, CheckCircle, Loader2, Zap, Brain } from 'lucide-react';

export function EngagementTracker({
  sessionId,
  onEngagementUpdate,
  interval = 30000,
  enabled = false,
  className = ''
}) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const intervalRef = useRef(null);
  const modelLoadedRef = useRef(false);
  const [isEnabled, setIsEnabled] = useState(enabled);
  const [status, setStatus] = useState('idle');
  const [engagement, setEngagement] = useState({ score: 0, present: false, attentive: false, emotions: {} });
  const [error, setError] = useState(null);
  const [permission, setPermission] = useState('prompt');

  const loadModels = useCallback(async () => {
    try {
      setStatus('loading');
      const faceapi = await import('face-api.js');
      const MODEL_URL = '/models';
      await faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL);
      await faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL);
      await faceapi.nets.faceExpressionNet.loadFromUri(MODEL_URL);
      modelLoadedRef.current = true;
      setStatus('ready');
    } catch (err) {
      setError('Face detection models unavailable. Serve model files at /models to enable engagement tracking.');
      setStatus('error');
    }
  }, []);

  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 320, height: 240, facingMode: 'user' },
        audio: false,
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setPermission('granted');
      return true;
    } catch (err) {
      setPermission('denied');
      setError('Camera access denied');
      return false;
    }
  }, []);

  const detectEngagement = useCallback(async () => {
    if (!modelLoadedRef.current || !videoRef.current || videoRef.current.paused || videoRef.current.ended) return;

    try {
      const faceapi = await import('face-api.js');
      const detection = await faceapi.detectSingleFace(videoRef.current, new faceapi.TinyFaceDetectorOptions())
        .withFaceLandmarks()
        .withFaceExpressions();

      if (detection) {
        const expressions = detection.expressions;
        const attentive = expressions.neutral > 0.3 || expressions.happy > 0.2 || expressions.surprised > 0.1;
        const present = detection.detection.score > 0.5;
        const emotions = {
          neutral: expressions.neutral,
          happy: expressions.happy,
          sad: expressions.sad,
          angry: expressions.angry,
          fearful: expressions.fearful,
          disgusted: expressions.disgusted,
          surprised: expressions.surprised,
        };
        const topEmotion = Object.entries(emotions).reduce((a, b) => emotions[a[0]] > emotions[b[0]] ? a : b)[0];
        const score = Math.round(((present ? 0.6 : 0) + (attentive ? 0.4 : 0)) * 100);

        const newEngagement = { score, present, attentive, emotions, topEmotion };
        setEngagement(newEngagement);
        onEngagementUpdate?.(sessionId, newEngagement);
      } else {
        const newEngagement = { ...engagement, present: false, attentive: false, score: 0 };
        setEngagement(newEngagement);
        onEngagementUpdate?.(sessionId, newEngagement);
      }
    } catch (err) {
      console.warn('Engagement detection failed:', err);
    }
  }, [sessionId, onEngagementUpdate, engagement]);

  const start = useCallback(async () => {
    if (!isEnabled) return;
    if (!modelLoadedRef.current) await loadModels();
    if (modelLoadedRef.current) {
      const cameraStarted = await startCamera();
      if (cameraStarted) {
        setStatus('tracking');
        intervalRef.current = setInterval(detectEngagement, interval);
      }
    }
  }, [isEnabled, loadModels, startCamera, detectEngagement, interval]);

  const stop = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (videoRef.current?.srcObject) {
      videoRef.current.srcObject.getTracks().forEach(track => track.stop());
      videoRef.current.srcObject = null;
    }
    setStatus('idle');
  }, []);

  const toggle = useCallback(() => {
    if (status === 'tracking') stop();
    else start();
  }, [status, start, stop]);

  useEffect(() => {
    setIsEnabled(enabled);
  }, [enabled]);

  useEffect(() => {
    if (isEnabled) start();
    return () => stop();
  }, [isEnabled, start, stop]);

  const getEngagementLabel = (score) => {
    if (score >= 80) return { label: 'Highly engaged', color: 'text-lime' };
    if (score >= 50) return { label: 'Engaged', color: 'text-cyan' };
    if (score >= 30) return { label: 'Low engagement', color: 'text-coral' };
    return { label: 'Not engaged', color: 'text-coral' };
  };

  const { label, color } = getEngagementLabel(engagement.score);

  if (!isEnabled) {
    return (
      <div className="engagement-consent" role="region" aria-label="Engagement tracking consent">
        <div className="engagement-consent-card">
          <Brain size={24} />
          <h3>Engagement tracking</h3>
          <p>
            Enable camera-based engagement tracking to measure your presence and
            attentiveness during this session. Your video is processed locally and
            never stored or shared.
          </p>
          <button className="button button-primary" onClick={() => setIsEnabled(true)} aria-label="Enable engagement tracking">
            Enable tracking
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`engagement-tracker ${className}`} role="region" aria-label="Engagement tracking">
      <div className="tracker-header">
        <div className="tracker-status">
          <span className={`status-dot ${status}`} />
          <span className="status-text">
            {status === 'idle' && 'Inactive'}
            {status === 'loading' && 'Loading models…'}
            {status === 'ready' && 'Ready'}
            {status === 'tracking' && 'Tracking'}
            {status === 'error' && 'Error'}
          </span>
        </div>
        <button className="icon-button" onClick={toggle} aria-label={status === 'tracking' ? 'Pause tracking' : 'Start tracking'} aria-pressed={status === 'tracking'}>
          {status === 'tracking' ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>

      {status === 'error' && (
        <div className="tracker-error" role="alert">
          <AlertCircle size={16} /> {error}
        </div>
      )}

      {permission === 'denied' && (
        <div className="tracker-permission" role="alert">
          <AlertCircle size={16} /> Camera access denied. Enable in browser settings to use engagement tracking.
        </div>
      )}

      <div className="tracker-video-wrapper">
        <video ref={videoRef} autoPlay playsInline muted style={{ display: 'none' }} />
        <canvas ref={canvasRef} className="tracker-canvas" width={320} height={240} aria-hidden="true" />
      </div>

      <div className="engagement-metrics">
        <div className="engagement-score">
          <span className={`score-value ${color}`}>{engagement.score}%</span>
          <span className={`score-label ${color}`}>{label}</span>
        </div>
        <div className="engagement-indicators">
          <div className={`indicator ${engagement.present ? 'active' : ''}`}>
            <CheckCircle size={14} /> Present
          </div>
          <div className={`indicator ${engagement.attentive ? 'active' : ''}`}>
            <Brain size={14} /> Attentive
          </div>
        </div>
        <div className="engagement-emotions">
          {engagement.topEmotion && (
            <div className="top-emotion">
              <Zap size={12} />
              <span>Primary: {engagement.topEmotion} ({Math.round(engagement.emotions[engagement.topEmotion] * 100)}%)</span>
            </div>
          )}
        </div>
      </div>

      {status === 'loading' && (
        <div className="tracker-loading" role="status">
          <Loader2 size={20} className="spin" /> Loading face detection models…
        </div>
      )}
    </div>
  );
}

export default EngagementTracker;
