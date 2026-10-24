import React, { useState } from 'react';
import { 
  Layers, 
  Search, 
  LayoutDashboard, 
  BookOpen, 
  ExternalLink, 
  Globe, 
  CheckCircle2 
} from 'lucide-react';

export default function Navbar({ activePage, setActivePage, isOnline, modelName, apiBaseUrl, currentUser, onOpenAuthModal }) {
  const [showModelTooltip, setShowModelTooltip] = useState(false);

  // Computed Swagger URL
  const swaggerUrl = apiBaseUrl 
    ? `${apiBaseUrl}/docs` 
    : (typeof window !== 'undefined' && window.location.port === '5173' ? 'http://127.0.0.1:8000/docs' : '/docs');

  return (
    <header className="sticky top-0 z-50 bg-[#07090e]/85 backdrop-blur-xl border-b border-white/[0.08] shadow-lg shadow-black/40">
      <div className={`mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4 ${
        activePage === 'search' ? 'max-w-[1720px]' : (activePage === 'dashboard' ? 'max-w-7xl 2xl:max-w-[1680px]' : 'max-w-7xl')
      }`}>
        
        {/* Brand Logo & Name */}
        <div 
          className="flex items-center gap-3 cursor-pointer select-none shrink-0" 
          onClick={() => setActivePage('search')}
        >
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 via-indigo-600 to-cyan-400 flex items-center justify-center text-white shadow-md shadow-indigo-500/25 transition-transform hover:scale-105">
            <Layers className="w-5 h-5" />
          </div>
          <div className="flex items-center gap-2">
            <span className="font-['Outfit'] font-bold text-xl text-white tracking-tight">
              RAG<span className="bg-gradient-to-r from-cyan-400 to-indigo-400 bg-clip-text text-transparent">Ops</span>
            </span>
            <span className="hidden sm:inline-block text-[11px] px-2 py-0.5 rounded-full bg-white/[0.05] text-slate-300 border border-white/10 font-medium">
              Enterprise
            </span>
          </div>
        </div>

        {/* Central Segmented Pill Navigation */}
        <nav className="flex items-center p-1 bg-[#0c101a] border border-white/10 rounded-xl shadow-inner shrink-0">
          <button
            onClick={() => setActivePage('search')}
            className={`flex items-center gap-2 px-3 sm:px-4 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all cursor-pointer ${
              activePage === 'search'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
            }`}
          >
            <Search className="w-4 h-4 shrink-0" />
            <span>Search &amp; Chat</span>
          </button>

          {currentUser?.role === 'admin' && (
            <button
              onClick={() => setActivePage('dashboard')}
              className={`flex items-center gap-2 px-3 sm:px-4 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all cursor-pointer ${
                activePage === 'dashboard'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
              }`}
            >
              <LayoutDashboard className="w-4 h-4 shrink-0 text-amber-400" />
              <span>Dashboard</span>
              <span className="text-[9px] px-1.5 py-0.2 rounded font-mono font-bold bg-amber-500/20 text-amber-300">
                ADMIN
              </span>
            </button>
          )}

          <button
            onClick={() => setActivePage('docs')}
            className={`flex items-center gap-2 px-3 sm:px-4 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all cursor-pointer ${
              activePage === 'docs'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
            }`}
          >
            <BookOpen className="w-4 h-4 shrink-0" />
            <span>Docs</span>
          </button>
        </nav>

        {/* Right Status Badges & Swagger Button */}
        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          
          {/* Target Host Environment Badge */}
          <button
            type="button"
            onClick={() => setActivePage('docs')}
            title="Click to view or switch API target server"
            className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/[0.03] hover:bg-white/[0.07] border border-white/10 text-xs text-slate-300 font-mono transition-colors cursor-pointer"
          >
            <Globe className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
            <span className="text-[11px]">{apiBaseUrl ? 'Live Cloud' : 'Local Dev'}</span>
          </button>

          {/* Online / Model Status Pill (Hoverable Tooltip) */}
          <div 
            className="relative flex items-center"
            onMouseEnter={() => setShowModelTooltip(true)}
            onMouseLeave={() => setShowModelTooltip(false)}
          >
            <div className="flex items-center gap-2 px-2.5 sm:px-3 py-1 rounded-full bg-[#0a0e18] border border-white/10 text-xs text-slate-300 cursor-help select-none">
              <span className={`w-2 h-2 rounded-full ${
                isOnline 
                  ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)] animate-pulse' 
                  : 'bg-rose-400 shadow-[0_0_8px_rgba(251,113,133,0.8)]'
              }`} />
              <span className="font-medium text-[11px] sm:text-xs">
                {isOnline ? 'Online' : 'Offline'}
              </span>
            </div>

            {/* Clean Model Tooltip */}
            {showModelTooltip && (
              <div className="absolute top-full mt-2 right-0 z-50 bg-[#0f1422] border border-white/10 text-white text-xs rounded-xl p-3 shadow-2xl shadow-black/80 w-64 animate-in fade-in zoom-in-95 duration-150">
                <div className="flex items-center gap-2 text-emerald-400 font-medium mb-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Backend Health Probe OK</span>
                </div>
                <div className="text-[11px] text-slate-400 font-mono space-y-1">
                  <div>Model: <span className="text-white font-semibold">{modelName || 'Groq LLaMA 3.1 70B'}</span></div>
                  <div>Target: <span className="text-cyan-400">{apiBaseUrl || 'http://127.0.0.1:8000'}</span></div>
                </div>
              </div>
            )}
          </div>

          {/* User Account / Auth Switcher Badge */}
          <button
            type="button"
            onClick={onOpenAuthModal}
            className="flex items-center gap-2 px-2.5 sm:px-3 py-1.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 text-xs text-white transition-all cursor-pointer shadow-sm"
            title="Click to switch between admin, test1, test2 accounts"
          >
            <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
              currentUser?.role === 'admin' 
                ? 'bg-amber-500 text-black' 
                : 'bg-indigo-600 text-white'
            }`}>
              {currentUser?.username ? currentUser.username.charAt(0).toUpperCase() : 'U'}
            </div>
            <span className="font-medium hidden sm:inline-block">
              {currentUser?.username || 'Sign In'}
            </span>
            {currentUser?.role && (
              <span className={`text-[9px] px-1 py-0.2 rounded font-mono font-bold uppercase ${
                currentUser.role === 'admin' 
                  ? 'bg-amber-500/20 text-amber-300' 
                  : 'bg-cyan-500/20 text-cyan-300'
              }`}>
                {currentUser.role}
              </span>
            )}
          </button>

          {/* Swagger API Direct Button */}
          <a
            href={swaggerUrl}
            target="_blank"
            rel="noopener noreferrer"
            title="Open OpenAPI Swagger Interactive Documentation"
            className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-indigo-500/20 to-cyan-500/20 hover:from-indigo-500/30 hover:to-cyan-500/30 text-cyan-300 hover:text-white border border-cyan-500/30 text-xs font-semibold transition-all shadow-sm shadow-cyan-500/10 cursor-pointer"
          >
            <span>Swagger</span>
            <ExternalLink className="w-3.5 h-3.5 shrink-0" />
          </a>

        </div>

      </div>
    </header>
  );
}
