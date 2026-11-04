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
  const isLight = theme === 'light';

  // Computed Swagger URL
  const swaggerUrl = apiBaseUrl 
    ? `${apiBaseUrl}/docs` 
    : (typeof window !== 'undefined' && window.location.port === '5173' ? 'http://127.0.0.1:8000/docs' : '/docs');

  const isWarming = warmupState?.status === 'warming';

  return (
    <header className={`sticky top-0 z-50 backdrop-blur-md border-b shadow-sm transition-colors duration-200 ${
      isLight ? 'bg-white/95 border-slate-200 text-slate-800' : 'bg-[#080b11]/90 border-white/[0.08] text-slate-100'
    }`}>
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
            <span className={`font-['Outfit'] font-bold text-base tracking-tight ${isLight ? 'text-slate-900' : 'text-white'}`}>
              RAG<span className={isLight ? "text-indigo-600" : "text-indigo-400"}>Ops</span>
            </span>
            <span className={`hidden sm:inline-block text-[10px] px-1.5 py-0.5 rounded font-medium ${
              isLight ? 'bg-slate-100 text-slate-600 border border-slate-200' : 'bg-white/[0.06] text-slate-300'
            }`}>
              v0.1
            </span>
          </div>
        </div>

        {/* Central Segmented Pill Navigation */}
        <nav className={`flex items-center p-0.5 border rounded-lg shrink-0 transition-colors ${
          isLight ? 'bg-slate-100 border-slate-200' : 'bg-[#0e131f] border-white/10'
        }`}>
          <button
            onClick={() => setActivePage('search')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-all cursor-pointer ${
              activePage === 'search'
                ? 'bg-indigo-600 text-white shadow-sm'
                : isLight
                ? 'text-slate-600 hover:text-slate-900 hover:bg-white/70'
                : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
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
                : isLight
                ? 'text-slate-600 hover:text-slate-900 hover:bg-white/70'
                : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
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
                : isLight
                ? 'text-slate-600 hover:text-slate-900 hover:bg-white/70'
                : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
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
            <div className={`flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] font-medium animate-pulse border ${
              isLight ? 'bg-amber-50 border-amber-200 text-amber-800' : 'bg-amber-500/10 border-amber-500/30 text-amber-300'
            }`}>
              <Loader2 className="w-3 h-3 animate-spin text-amber-500" />
              <span>Warming up…</span>
            </div>
          ) : warmupState?.took_ms > 0 ? (
            <div className={`hidden md:flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono border ${
              isLight ? 'bg-emerald-50 border-emerald-200 text-emerald-700' : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
            }`} title={`Subsystems ready in ${warmupState.took_ms}ms`}>
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
              className={`flex items-center gap-1.5 px-2 py-1 rounded-lg border text-xs transition-all cursor-pointer ${
                isLight ? 'bg-slate-100/70 hover:bg-slate-100 border-slate-200 text-slate-700' : 'bg-white/[0.04] hover:bg-white/[0.08] border-white/10 text-slate-300'
              }`}
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
              <div className={`absolute top-full mt-2 right-0 z-50 border text-xs rounded-xl p-2.5 shadow-xl w-60 animate-in fade-in zoom-in-95 duration-100 ${
                isLight ? 'bg-white border-slate-200 text-slate-800 shadow-slate-200/50' : 'bg-[#0f1422] border-white/10 text-white'
              }`}>
                <div className="flex items-center gap-1.5 text-emerald-500 font-medium mb-1">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>Subsystem Connected</span>
                </div>
                <div className={`text-[11px] font-mono space-y-0.5 ${isLight ? 'text-slate-500' : 'text-slate-400'}`}>
                  <div>Provider: <span className={`font-semibold capitalize ${isLight ? 'text-slate-800' : 'text-white'}`}>{activeProvider}</span></div>
                  <div>Model: <span className="text-cyan-600 dark:text-cyan-300 truncate block">{modelName}</span></div>
                  <div>Status: <span className="text-emerald-600 dark:text-emerald-300">{isOnline ? 'Online' : 'Offline'}</span></div>
                </div>
              </div>
            )}
          </div>

          {/* Dark / Light Theme Toggle */}
          <button
            onClick={toggleTheme}
            className={`p-1.5 rounded-lg border transition-all cursor-pointer ${
              isLight 
                ? 'bg-slate-100/70 hover:bg-slate-100 border-slate-200 text-slate-700 hover:text-slate-900' 
                : 'bg-white/[0.04] hover:bg-white/[0.08] border-white/10 text-slate-400 hover:text-white'
            }`}
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? <Sun className="w-3.5 h-3.5 text-amber-400" /> : <Moon className="w-3.5 h-3.5 text-indigo-600" />}
          </button>

          {/* User Account / Auth Switcher Badge */}
          <button
            type="button"
            onClick={onOpenAuthModal}
            className={`flex items-center gap-1.5 px-2 py-1 rounded-lg border text-xs transition-all cursor-pointer ${
              isLight ? 'bg-slate-100/70 hover:bg-slate-100 border-slate-200 text-slate-800' : 'bg-white/[0.04] hover:bg-white/[0.08] border-white/10 text-white'
            }`}
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
              <span className="text-[9px] px-1 py-0.2 rounded font-mono font-bold uppercase bg-amber-500/20 text-amber-500">
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
            className={`hidden lg:flex items-center gap-1 px-2 py-1 rounded-md border text-xs font-medium transition-all ${
              isLight 
                ? 'bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border-indigo-200' 
                : 'bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border-indigo-500/20'
            }`}
          >
            <span>API</span>
            <ExternalLink className="w-3 h-3" />
          </a>

        </div>

      </div>
    </header>
  );
}
