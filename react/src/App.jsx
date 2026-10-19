import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import SearchPage from './components/SearchPage';
import DashboardPage from './components/DashboardPage';
import DocsPage from './components/DocsPage';
import ChunkModal from './components/ChunkModal';
import AuthModal from './components/AuthModal';

export default function App() {
  const getInitialPage = () => {
    if (typeof window === 'undefined') return 'search';
    const hash = window.location.hash.toLowerCase();
    const path = window.location.pathname.toLowerCase();
    if (hash.includes('dashboard') || path.includes('/dashboard')) return 'dashboard';
    if (hash.includes('docs') || path.includes('/docs')) return 'docs';
    return 'search';
  };

  const [activePage, setActivePage] = useState(getInitialPage);
  const [selectedChunk, setSelectedChunk] = useState(null);
  const [searchInitialQuery, setSearchInitialQuery] = useState('');
  const [isOnline, setIsOnline] = useState(true);
  const [modelName, setModelName] = useState('Groq LLaMA 3.1 70B');

  // Authentication State
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const stored = localStorage.getItem('ragops_user');
      if (stored) return JSON.parse(stored);
    } catch (e) {}
    // Default active user is test1
    return {
      id: 2,
      username: 'test1',
      email: 'test1@ragops.io',
      role: 'user',
    };
  });

  // API base URL for multi-environment: empty string means local origin/proxy, or custom cloud URL
  const [apiBaseUrl, setApiBaseUrl] = useState(() => {
    return localStorage.getItem('ragops_api_base_url') || '';
  });

  const handlePageChange = (page) => {
    setActivePage(page);
    window.location.hash = page;
  };

  // Synchronize hash changes
  useEffect(() => {
    const onHashChange = () => {
      const hash = window.location.hash.toLowerCase();
      if (hash.includes('dashboard')) setActivePage('dashboard');
      else if (hash.includes('docs')) setActivePage('docs');
      else if (hash.includes('search')) setActivePage('search');
    };
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  // Verify backend connectivity
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const target = apiBaseUrl ? `${apiBaseUrl}/health/ready` : '/health/ready';
        const res = await fetch(target);
        if (res.ok) {
          const json = await res.json();
          setIsOnline(true);
          if (json.model) setModelName(`Groq ${json.model}`);
        } else {
          setIsOnline(false);
        }
      } catch (err) {
        setIsOnline(false);
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 20000);
    return () => clearInterval(interval);
  }, [apiBaseUrl]);

  const handleRerunQuery = (queryText) => {
    setSearchInitialQuery(queryText);
    handlePageChange('search');
  };

  const handleLogout = () => {
    localStorage.removeItem('ragops_token');
    localStorage.removeItem('ragops_user');
    setCurrentUser(null);
  };

  return (
    <div className="min-h-screen bg-[#07090e] text-slate-100 flex flex-col font-['Inter'] selection:bg-indigo-500 selection:text-white">
      {/* Top Navigation */}
      <Navbar
        activePage={activePage}
        setActivePage={handlePageChange}
        isOnline={isOnline}
        modelName={modelName}
        apiBaseUrl={apiBaseUrl}
        currentUser={currentUser}
        onOpenAuthModal={() => setIsAuthModalOpen(true)}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activePage === 'search' && (
          <SearchPage
            onChunkClick={(chunk) => setSelectedChunk(chunk)}
            initialQuery={searchInitialQuery}
            apiBaseUrl={apiBaseUrl}
            currentUser={currentUser}
            onOpenAuthModal={() => setIsAuthModalOpen(true)}
            onFeedbackRecorded={() => {}}
          />
        )}

        {activePage === 'dashboard' && (
          <DashboardPage 
            onRerunQuery={handleRerunQuery}
            apiBaseUrl={apiBaseUrl}
            currentUser={currentUser}
            onOpenAuthModal={() => setIsAuthModalOpen(true)}
          />
        )}

        {activePage === 'docs' && (
          <DocsPage 
            apiBaseUrl={apiBaseUrl} 
            setApiBaseUrl={setApiBaseUrl} 
          />
        )}
      </main>

      {/* Enterprise Footer */}
      <footer className="border-t border-white/5 py-6 bg-[#05070a] text-center text-xs text-slate-400">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>RAGOps Enterprise Production Stack &bull; PostgreSQL Telemetry + ChromaDB + Cross-Encoder</span>
          </div>
          <div>
            <span>Role-Based Access Control &bull; Chunk Provenance &bull; Grounded Inference</span>
          </div>
        </div>
      </footer>

      {/* Chunk Inspection Dialog */}
      {selectedChunk && (
        <ChunkModal
          chunk={selectedChunk}
          onClose={() => setSelectedChunk(null)}
        />
      )}

      {/* Authentication & User Switcher Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        currentUser={currentUser}
        onLoginSuccess={(user) => setCurrentUser(user)}
        onLogout={handleLogout}
        apiBaseUrl={apiBaseUrl}
      />
    </div>
  );
}
