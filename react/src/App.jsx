import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import SearchPage from './components/SearchPage';
import DashboardPage from './components/DashboardPage';
import DocsPage from './components/DocsPage';
import ChunkModal from './components/ChunkModal';
import AuthModal from './components/AuthModal';
import { Lock, ShieldAlert, ArrowLeft, UserCheck } from 'lucide-react';

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
    <div className={`${activePage === 'search' ? 'h-screen overflow-hidden' : 'min-h-screen'} bg-[#07090e] text-slate-100 flex flex-col font-['Inter'] selection:bg-indigo-500 selection:text-white`}>
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
      <main className={`flex-1 w-full flex flex-col min-h-0 ${
        activePage === 'search' 
          ? 'max-w-[1720px] w-full mx-auto px-2 sm:px-4 lg:px-6 py-2 overflow-hidden' 
          : 'max-w-7xl 2xl:max-w-[1680px] mx-auto px-4 sm:px-6 lg:px-8 py-8'
      }`}>
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
          currentUser?.role === 'admin' ? (
            <DashboardPage 
              onRerunQuery={handleRerunQuery}
              onChunkClick={(chunk) => setSelectedChunk(chunk)}
              apiBaseUrl={apiBaseUrl}
              currentUser={currentUser}
              onOpenAuthModal={() => setIsAuthModalOpen(true)}
            />
          ) : (
            <div className="max-w-xl mx-auto py-16 px-4 text-center animate-in fade-in duration-200">
              <div className="p-8 sm:p-10 rounded-3xl bg-[#0b0f19] border border-amber-500/30 shadow-2xl space-y-6">
                <div className="w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center mx-auto text-amber-400">
                  <Lock className="w-8 h-8" />
                </div>
                <div className="space-y-2">
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20 text-xs font-mono font-bold">
                    <ShieldAlert className="w-3.5 h-3.5" />
                    <span>ADMIN ONLY</span>
                  </div>
                  <h2 className="text-2xl font-bold text-white font-['Outfit']">
                    Administrator Access Required
                  </h2>
                  <p className="text-sm text-slate-400 max-w-md mx-auto leading-relaxed">
                    You are currently logged in as <span className="text-cyan-400 font-mono font-bold">@{currentUser?.username || 'user'}</span> (Standard User). The Enterprise Observability, User Directory, and Audit Dashboard is restricted to platform administrators.
                  </p>
                </div>
                <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
                  <button
                    onClick={() => setIsAuthModalOpen(true)}
                    className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-black font-semibold text-xs transition-all shadow-lg shadow-amber-500/20 cursor-pointer flex items-center justify-center gap-2"
                  >
                    <UserCheck className="w-4 h-4" />
                    <span>Switch to Admin Account</span>
                  </button>
                  <button
                    onClick={() => handlePageChange('search')}
                    className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 border border-white/10 font-semibold text-xs transition-all cursor-pointer flex items-center justify-center gap-2"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    <span>Return to Search &amp; Chat</span>
                  </button>
                </div>
              </div>
            </div>
          )
        )}

        {activePage === 'docs' && (
          <DocsPage 
            apiBaseUrl={apiBaseUrl} 
            setApiBaseUrl={setApiBaseUrl} 
          />
        )}
      </main>

      {/* Enterprise Footer */}
      <footer className={`border-t border-white/5 bg-[#05070a] text-center text-slate-400 shrink-0 ${
        activePage === 'search' ? 'py-2 text-[11px]' : 'py-6 text-xs'
      }`}>
        <div className={`mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2 ${
          activePage === 'search' ? 'max-w-[1720px]' : (activePage === 'dashboard' ? 'max-w-7xl 2xl:max-w-[1680px]' : 'max-w-7xl')
        }`}>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]" />
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
