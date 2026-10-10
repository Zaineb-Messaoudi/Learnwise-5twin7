import React, { useEffect, useState } from 'react';
import { TrendingUp, Target, Clock, Loader2 } from 'lucide-react';
import { useProgressSyncContext } from '../../contexts/ProgressSyncContext';

export function LiveProgressIndicator({ courseId, compact = false }) {
  const { latestProgress, status } = useProgressSyncContext();
  const [progress, setProgress] = useState(0);
  const [animating, setAnimating] = useState(false);

  useEffect(() => {
    if (latestProgress[courseId] !== undefined) {
      const newProgress = latestProgress[courseId];
      if (newProgress !== progress) {
        setAnimating(true);
        setProgress(newProgress);
        setTimeout(() => setAnimating(false), 500);
      }
    }
  }, [latestProgress, courseId, progress]);

  if (compact) {
    return (
      <div className={`live-progress-compact ${animating ? 'animating' : ''}`} title={`Progress: ${Math.round(progress * 100)}%`}>
        <div className="progress-ring" style={{ '--progress': progress }}>
          <span className="progress-value">{Math.round(progress * 100)}%</span>
        </div>
        <div className="progress-status">
          <span className={`status-dot ${status === 'connected' ? 'connected' : status === 'connecting' ? 'connecting' : 'disconnected'}`} />
        </div>
      </div>
    );
  }

  return (
    <div className={`live-progress-indicator ${animating ? 'animating' : ''}`} role="status" aria-live="polite">
      <div className="progress-header">
        <div className="progress-title">
          <Target size={16} />
          <span>Live Progress</span>
        </div>
        <div className={`connection-status ${status}`}>
          <span className="status-dot" />
          <span>{status === 'connected' ? 'Live' : status === 'connecting' ? 'Connecting…' : 'Offline'}</span>
        </div>
      </div>
      <div className="progress-main">
        <div className="progress-bar-wrapper">
          <div className="progress-bar-track">
            <div
              className="progress-bar-fill"
              style={{ width: `${progress * 100}%` }}
              role="progressbar"
              aria-valuenow={Math.round(progress * 100)}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>
        </div>
        <div className="progress-stats">
          <div className="stat">
            <TrendingUp size={14} />
            <span>{Math.round(progress * 100)}% complete</span>
          </div>
          <div className="stat">
            <Clock size={14} />
            <span>Updated just now</span>
          </div>
        </div>
      </div>
      {status === 'connecting' && (
        <div className="progress-connecting">
          <Loader2 size={14} className="spin" /> Establishing live connection…
        </div>
      )}
    </div>
  );
}

export default LiveProgressIndicator;