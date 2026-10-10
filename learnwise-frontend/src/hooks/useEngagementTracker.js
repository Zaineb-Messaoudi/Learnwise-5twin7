import { useState, useCallback, useEffect } from 'react';
import { analyticsApi } from '../api/analytics.api';
import { isBackendApiEnabled } from '../api/client';

export function useEngagementTracker(sessionId, enabled = true) {
  const [engagementData, setEngagementData] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  const handleEngagementUpdate = useCallback(async (sid, engagement) => {
    if (!isBackendApiEnabled || !sid) return;
    try {
      await analyticsApi.recordActivity({
        session_id: sid,
        activity_type: 'engagement_check',
        engagement_score: engagement.score,
        engagement_present: engagement.present,
        engagement_attentive: engagement.attentive,
        engagement_emotions: engagement.emotions,
        engagement_top_emotion: engagement.topEmotion,
      });
      setEngagementData(engagement);
      setLastUpdate(Date.now());
    } catch (err) {
      console.warn('Failed to record engagement:', err);
    }
  }, []);

  const sendHeartbeat = useCallback(async () => {
    if (!isBackendApiEnabled || !sessionId || !engagementData) return;
    try {
      await analyticsApi.recordActivity({
        session_id: sessionId,
        activity_type: 'heartbeat',
        engagement_score: engagementData.score,
      });
    } catch (err) {
      console.warn('Heartbeat failed:', err);
    }
  }, [sessionId, engagementData]);

  useEffect(() => {
    if (!enabled || !sessionId) return;
    const interval = setInterval(sendHeartbeat, 60000);
    return () => clearInterval(interval);
  }, [enabled, sessionId, sendHeartbeat]);

  return { engagementData, lastUpdate, handleEngagementUpdate };
}

export default useEngagementTracker;