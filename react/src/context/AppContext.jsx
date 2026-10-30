import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';

const AppStoreContext = createContext(null);

export function AppStoreProvider({ children }) {
  // 1. Base URL
  const [apiBaseUrl, setApiBaseUrlState] = useState(() => {
    return localStorage.getItem('ragops_api_base_url') || '';
  });

  const setApiBaseUrl = useCallback((url) => {
    setApiBaseUrlState(url);
    if (url) {
      localStorage.setItem('ragops_api_base_url', url);
    } else {
      localStorage.removeItem('ragops_api_base_url');
    }
  }, []);

  // 2. Active Theme ('dark' | 'light')
  const [theme, setThemeState] = useState(() => {
    return localStorage.getItem('ragops_theme') || 'dark';
  });

  const toggleTheme = useCallback(() => {
    setThemeState((prev) => {
      const next = prev === 'dark' ? 'light' : 'dark';
      localStorage.setItem('ragops_theme', next);
      if (next === 'light') {
        document.documentElement.classList.add('light-theme');
      } else {
        document.documentElement.classList.remove('light-theme');
      }
      return next;
    });
  }, []);

  useEffect(() => {
    if (theme === 'light') {
      document.documentElement.classList.add('light-theme');
    } else {
      document.documentElement.classList.remove('light-theme');
    }
  }, [theme]);

  // 3. User Authentication State (RESTORE IMMEDIATELY from localStorage)
  const [currentUser, setCurrentUserState] = useState(() => {
    try {
      const stored = localStorage.getItem('ragops_user');
      if (stored) return JSON.parse(stored);
    } catch (e) {}
    return {
      id: 2,
      username: 'test1',
      email: 'test1@ragops.io',
      role: 'user',
    };
  });

  const [authToken, setAuthToken] = useState(() => {
    return localStorage.getItem('ragops_token') || '';
  });

  const setCurrentUser = useCallback((user, token = null) => {
    setCurrentUserState(user);
    if (user) {
      localStorage.setItem('ragops_user', JSON.stringify(user));
    } else {
      localStorage.removeItem('ragops_user');
    }
    if (token !== null) {
      setAuthToken(token);
      if (token) {
        localStorage.setItem('ragops_token', token);
      } else {
        localStorage.removeItem('ragops_token');
      }
    }
  }, []);

  // 4. Central Data Store States
  const [healthData, setHealthData] = useState(null);
  const [isOnline, setIsOnline] = useState(true);
  const [modelName, setModelName] = useState('Ollama llama3.2:3b');
  const [activeProvider, setActiveProvider] = useState('auto');
  const [warmupState, setWarmupState] = useState(() => {
    try {
      const saved = sessionStorage.getItem('ragops_warmup_state');
      if (saved) return JSON.parse(saved);
    } catch (e) {}
    return { status: 'ready', took_ms: 0, stages: {} };
  });

  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [catalogData, setCatalogData] = useState(null);
  const [cacheStats, setCacheStats] = useState(null);
  const [companyProfile, setCompanyProfile] = useState(null);

  // Admin-only states
  const [analytics, setAnalytics] = useState(null);
  const [userList, setUserList] = useState([]);
  const [recentLogs, setRecentLogs] = useState([]);
  const [feedbackData, setFeedbackData] = useState(null);

  // Loading & Error states
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [bootstrapError, setBootstrapError] = useState(null);

  // AbortController ref to cancel stale requests on rapid account switch
  const abortControllerRef = useRef(null);

  // 5. Unified Parallel Bootstrap & Refetch Loader
  const loadAppData = useCallback(async (userToLoad = currentUser) => {
    if (!userToLoad?.username) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const abortCtrl = new AbortController();
    abortControllerRef.current = abortCtrl;
    const { signal } = abortCtrl;

    setBootstrapError(null);

    const base = apiBaseUrl || '';
    const username = userToLoad.username;
    const role = userToLoad.role || 'user';

    try {
      // 1. Health check & provider info (resolved immediately so warmup/provider state updates in ms)
      const healthPromise = fetch(`${base}/health/ready`, { signal })
        .then((r) => (r.ok ? r.json() : null))
        .then((hData) => {
          if (hData && !signal.aborted) {
            setIsOnline(true);
            setHealthData(hData);
            if (hData.warmup) {
              setWarmupState(hData.warmup);
              try {
                sessionStorage.setItem('ragops_warmup_state', JSON.stringify(hData.warmup));
              } catch (e) {}
            }
            if (hData.active_provider) setActiveProvider(hData.active_provider);
            if (hData.model) setModelName(hData.model);
          }
          return hData;
        })
        .catch(() => null);

      // 2. Chat Sessions for the active user
      const sessionsPromise = fetch(
        `${base}/api/v1/sessions?username=${encodeURIComponent(username)}&role=${encodeURIComponent(role)}`,
        { signal }
      )
        .then((r) => (r.ok ? r.json() : { sessions: [] }))
        .catch(() => ({ sessions: [] }));

      // 3. Document Catalog
      const catalogPromise = fetch(`${base}/api/v1/catalog`, { signal })
        .then((r) => (r.ok ? r.json() : null))
        .catch(() => null);

      // 4. Cache Statistics
      const cachePromise = fetch(`${base}/api/v1/cache/stats`, { signal })
        .then((r) => (r.ok ? r.json() : null))
        .catch(() => null);

      // 5. Company Profile
      const companyPromise = fetch(`${base}/api/v1/company/profile`, { signal })
        .then((r) => (r.ok ? r.json() : null))
        .catch(() => null);

      // 6. Admin queries (if admin)
      let adminPromises = [Promise.resolve(null), Promise.resolve(null), Promise.resolve(null), Promise.resolve(null)];
      if (role === 'admin') {
        adminPromises = [
          fetch(`${base}/api/v1/admin/analytics`, { signal }).then((r) => (r.ok ? r.json() : null)).catch(() => null),
          fetch(`${base}/api/v1/admin/users`, { signal }).then((r) => (r.ok ? r.json() : null)).catch(() => null),
          fetch(`${base}/api/v1/admin/logs?limit=50`, { signal }).then((r) => (r.ok ? r.json() : null)).catch(() => null),
          fetch(`${base}/api/v1/feedback/stats`, { signal }).then((r) => (r.ok ? r.json() : null)).catch(() => null),
        ];
      }

      const [healthRes, sessRes, catRes, cacheRes, compRes, analyticsRes, usersRes, logsRes, fbRes] =
        await Promise.all([
          healthPromise,
          sessionsPromise,
          catalogPromise,
          cachePromise,
          companyPromise,
          ...adminPromises,
        ]);

      if (signal.aborted) return;

      // Update Health & LLM status
      if (healthRes) {
        setIsOnline(true);
        setHealthData(healthRes);
        if (healthRes.warmup) {
          setWarmupState(healthRes.warmup);
          try {
            sessionStorage.setItem('ragops_warmup_state', JSON.stringify(healthRes.warmup));
          } catch (e) {}
        }
        if (healthRes.active_provider) setActiveProvider(healthRes.active_provider);
        if (healthRes.model) setModelName(healthRes.model);
      } else if (!healthData) {
        setIsOnline(false);
      }

      // Update Sessions
      const loadedSessions = sessRes?.sessions || [];
      setSessions(loadedSessions);

      // Auto-open most recent session if available and activeSessionId not set or invalid
      if (loadedSessions.length > 0) {
        setActiveSessionId((prev) => {
          if (!prev || !loadedSessions.some((s) => s.session_id === prev)) {
            return loadedSessions[0].session_id;
          }
          return prev;
        });
      } else {
        setActiveSessionId(null);
      }

      // Update Catalog & Cache
      if (catRes) setCatalogData(catRes);
      if (cacheRes) setCacheStats(cacheRes);
      if (compRes?.profile) setCompanyProfile(compRes.profile);

      // Update Admin Data
      if (analyticsRes) setAnalytics(analyticsRes);
      if (usersRes?.users) setUserList(usersRes.users);
      if (logsRes?.logs) setRecentLogs(logsRes.logs);
      if (fbRes) setFeedbackData(fbRes);

      setIsBootstrapping(false);
    } catch (err) {
      if (err.name !== 'AbortError') {
        console.error('Bootstrap fetch error:', err);
        setBootstrapError(err.message || 'Failed to connect to backend service');
        setIsBootstrapping(false);
      }
    }
  }, [apiBaseUrl, currentUser]);

  // Initial load and auto-refetch on user change or target API base change
  useEffect(() => {
    loadAppData(currentUser);
  }, [currentUser, apiBaseUrl, loadAppData]);

  // Periodic background refresh (every 30s) paused when document is hidden
  useEffect(() => {
    const interval = setInterval(() => {
      if (typeof document !== 'undefined' && document.hidden) return;
      loadAppData(currentUser);
    }, 30000);
    return () => clearInterval(interval);
  }, [currentUser, loadAppData]);

  const value = {
    // Auth & User
    currentUser,
    setCurrentUser,
    authToken,
    apiBaseUrl,
    setApiBaseUrl,
    theme,
    toggleTheme,

    // Status
    isOnline,
    healthData,
    modelName,
    activeProvider,
    warmupState,

    // Core Data
    sessions,
    setSessions,
    activeSessionId,
    setActiveSessionId,
    catalogData,
    setCatalogData,
    cacheStats,
    setCacheStats,
    companyProfile,
    setCompanyProfile,

    // Admin Data
    analytics,
    setAnalytics,
    userList,
    recentLogs,
    feedbackData,

    // Lifecycle & Actions
    isBootstrapping,
    bootstrapError,
    refreshData: () => loadAppData(currentUser),
  };

  return <AppStoreContext.Provider value={value}>{children}</AppStoreContext.Provider>;
}

export function useAppStore() {
  const context = useContext(AppStoreContext);
  if (!context) {
    throw new Error('useAppStore must be used within an AppStoreProvider');
  }
  return context;
}

