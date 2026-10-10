import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { useProgressSync } from '../hooks/useProgressSync';
import { authApi } from '../api/auth.api';
import { isBackendApiEnabled } from '../api/client';

const ProgressSyncContext = createContext(null);

export function ProgressSyncProvider({ children }) {
  const [userId, setUserId] = useState(null);
  const progressSync = useProgressSync(userId, isBackendApiEnabled && Boolean(userId));

  useEffect(() => {
    const initUser = async () => {
      if (isBackendApiEnabled) {
        try {
          const me = await authApi.me();
          setUserId(me.id);
        } catch {
          console.warn('[ProgressSyncProvider] Could not fetch user');
        }
      }
    };
    initUser();
  }, []);

  return (
    <ProgressSyncContext.Provider value={progressSync}>
      {children}
    </ProgressSyncContext.Provider>
  );
}

export function useProgressSyncContext() {
  const context = useContext(ProgressSyncContext);
  if (!context) {
    throw new Error('useProgressSyncContext must be used within ProgressSyncProvider');
  }
  return context;
}

export default ProgressSyncContext;