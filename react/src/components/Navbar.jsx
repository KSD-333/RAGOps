import React, { useState } from 'react';
import { 
  Layers, 
  Search, 
  LayoutDashboard, 
  BookOpen, 
  ExternalLink, 
  CheckCircle2,
  Sun,
  Moon,
  Loader2,
  Cpu
} from 'lucide-react';
import { useAppStore } from '../context/AppContext';

export default function Navbar({ activePage, setActivePage, onOpenAuthModal }) {
  const {
    isOnline,
    modelName,
    activeProvider,
    warmupState,
    apiBaseUrl,
    currentUser,
    theme,
    toggleTheme,
  } = useAppStore();

  const [showModelTooltip, setShowModelTooltip] = useState(false);

  // Computed Swagger URL
  const swaggerUrl = apiBaseUrl 
    ? `${apiBaseUrl}/docs` 
    : (typeof window !== 'undefined' && window.location.port === '5173' ? 'http://127.0.0.1:8000/docs' : '/docs');

  const isWarming = warmupState?.status === 'warming';

  return (
    <header className="sticky top-0 z-50 bg-[#080b11]/90 backdrop-blur-md border-b border-white/[0.08] shadow-sm">
      <div className="mx-auto px-3 sm:px-4 lg:px-6 h-13 flex items-center justify-between gap-3 max-w-[1720px]">
        
        {/* Brand Logo & Name */}
        <div 
          className="flex items-center gap-2.5 cursor-pointer select-none shrink-0" 
          onClick={() => setActivePage('search')}
        >
          <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-sm transition-transform hover:scale-105">
            <Layers className="w-4 h-4" />
          </div>
          <div className="flex items-center gap-1.5">
            <span className="font-['Outfit'] font-bold text-base text-white tracking-tight">
              RAG<span className="text-indigo-400">Ops</span>
            </span>
            <span className="hidden sm:inline-block text-[10px] px-1.5 py-0.2 rounded bg-white/[0.06] text-slate-300 font-medium">
              v0.1
            </span>
          </div>
        </div>

        {/* Central Segmented Pill Navigation */}
        <nav className="flex items-center p-0.5 bg-[#0e131f] border border-white/10 rounded-lg shrink-0">
          <button
            onClick={() => setActivePage('search')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-all cursor-pointer ${
              activePage === 'search'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Search className="w-3.5 h-3.5" />
            <span>Chat</span>
          </button>

          <button
            onClick={() => setActivePage('dashboard')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-all cursor-pointer ${
              activePage === 'dashboard'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <LayoutDashboard className="w-3.5 h-3.5" />
            <span>Dashboard</span>
            {currentUser?.role === 'admin' && (
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
            )}
          </button>

          <button
            onClick={() => setActivePage('docs')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-all cursor-pointer ${
              activePage === 'docs'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Docs</span>
          </button>
        </nav>

        {/* Right Status Controls */}
        <div className="flex items-center gap-2 shrink-0">
          
          {/* Warmup Badge */}
          {isWarming ? (
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[11px] font-medium animate-pulse">
              <Loader2 className="w-3 h-3 animate-spin text-amber-400" />
              <span>Warming up…</span>
            </div>
          ) : warmupState?.took_ms > 0 ? (
            <div className="hidden md:flex items-center gap-1 px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[10px] font-mono" title={`Subsystems ready in ${warmupState.took_ms}ms`}>
              <CheckCircle2 className="w-2.5 h-2.5" />
              <span>Ready ({Math.round(warmupState.took_ms)}ms)</span>
            </div>
          ) : null}

          {/* Provider Status Indicator */}
          <div className="relative">
            <button
              onClick={() => setShowModelTooltip(!showModelTooltip)}
              onMouseEnter={() => setShowModelTooltip(true)}
              onMouseLeave={() => setShowModelTooltip(false)}
              className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 text-xs text-slate-300 transition-all cursor-pointer"
            >
              <span className={`w-2 h-2 rounded-full ${
                !isOnline 
                  ? 'bg-rose-500' 
                  : activeProvider === 'ollama' 
                  ? 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.7)]' 
                  : activeProvider === 'groq' 
                  ? 'bg-cyan-400 shadow-[0_0_6px_rgba(34,211,238,0.7)]' 
                  : 'bg-amber-400'
              }`} />
              <span className="font-mono text-[11px] uppercase tracking-wider hidden sm:inline">
                {activeProvider}
              </span>
            </button>

            {/* Model Tooltip */}
            {showModelTooltip && (
              <div className="absolute top-full mt-2 right-0 z-50 bg-[#0f1422] border border-white/10 text-white text-xs rounded-xl p-2.5 shadow-xl w-60 animate-in fade-in zoom-in-95 duration-100">
                <div className="flex items-center gap-1.5 text-emerald-400 font-medium mb-1">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>Subsystem Connected</span>
                </div>
                <div className="text-[11px] text-slate-400 font-mono space-y-0.5">
                  <div>Provider: <span className="text-white font-semibold capitalize">{activeProvider}</span></div>
                  <div>Model: <span className="text-cyan-300 truncate block">{modelName}</span></div>
                  <div>Status: <span className="text-emerald-300">{isOnline ? 'Online' : 'Offline'}</span></div>
                </div>
              </div>
            )}
          </div>

          {/* Dark / Light Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="p-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 text-slate-400 hover:text-white transition-all cursor-pointer"
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
          </button>

          {/* User Account / Auth Switcher Badge */}
          <button
            type="button"
            onClick={onOpenAuthModal}
            className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 text-xs text-white transition-all cursor-pointer"
            title="Click to switch accounts (admin, test1, test2)"
          >
            <div className={`w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold ${
              currentUser?.role === 'admin' ? 'bg-amber-500 text-black' : 'bg-indigo-600 text-white'
            }`}>
              {currentUser?.username ? currentUser.username.charAt(0).toUpperCase() : 'U'}
            </div>
            <span className="font-medium hidden sm:inline text-xs">
              {currentUser?.username || 'Sign In'}
            </span>
            {currentUser?.role === 'admin' && (
              <span className="text-[9px] px-1 py-0.2 rounded font-mono font-bold uppercase bg-amber-500/20 text-amber-300">
                Admin
              </span>
            )}
          </button>

          {/* Swagger Link */}
          <a
            href={swaggerUrl}
            target="_blank"
            rel="noopener noreferrer"
            title="Open Swagger OpenAPI Documentation"
            className="hidden lg:flex items-center gap-1 px-2 py-1 rounded-md bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/20 text-xs font-medium transition-all"
          >
            <span>API</span>
            <ExternalLink className="w-3 h-3" />
          </a>

        </div>

      </div>
    </header>
  );
}
