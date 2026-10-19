import React, { useState } from 'react';
import { 
  ShieldCheck, 
  User, 
  KeyRound, 
  LogIn, 
  LogOut, 
  CheckCircle2, 
  AlertCircle, 
  Sparkles, 
  X,
  Crown
} from 'lucide-react';

export default function AuthModal({ isOpen, onClose, currentUser, onLoginSuccess, onLogout, apiBaseUrl = '' }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  if (!isOpen) return null;

  const handleCustomLogin = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setErrorMessage('Please enter both username and password.');
      return;
    }
    await executeLogin(username.trim(), password.trim());
  };

  const handleQuickLogin = async (uname, pwd) => {
    setUsername(uname);
    setPassword(pwd);
    await executeLogin(uname, pwd);
  };

  const executeLogin = async (uname, pwd) => {
    setLoading(true);
    setErrorMessage('');
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: uname, password: pwd }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Invalid username or password');
      }

      const data = await res.json();
      localStorage.setItem('ragops_token', data.access_token);
      localStorage.setItem('ragops_user', JSON.stringify(data.user));
      onLoginSuccess(data.user);
      onClose();
    } catch (err) {
      setErrorMessage(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-[#0b0f19] border border-white/10 rounded-2xl w-full max-w-md overflow-hidden shadow-2xl shadow-indigo-950/50">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-white/[0.02]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-indigo-400">
              <KeyRound className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white font-['Outfit']">
                {currentUser ? 'Switch User / Account' : 'Sign In to RAGOps'}
              </h2>
              <p className="text-[11px] text-slate-400">
                PostgreSQL Role-Based Access &amp; Telemetry
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-6 space-y-5">
          
          {/* Active User Card if Logged In */}
          {currentUser && (
            <div className="p-3.5 rounded-xl bg-indigo-950/40 border border-indigo-500/30 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-indigo-600 flex items-center justify-center text-white font-bold text-sm">
                  {currentUser.username.charAt(0).toUpperCase()}
                </div>
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm font-semibold text-white">{currentUser.username}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono font-bold ${
                      currentUser.role === 'admin' 
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' 
                        : 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                    }`}>
                      {currentUser.role.toUpperCase()}
                    </span>
                  </div>
                  <span className="text-xs text-slate-400">{currentUser.email}</span>
                </div>
              </div>
              <button
                onClick={() => {
                  onLogout();
                  onClose();
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 text-xs font-medium transition-colors cursor-pointer"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>Log Out</span>
              </button>
            </div>
          )}

          {/* Quick 1-Click Test Credentials */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                <span>1-Click Test Accounts</span>
              </label>
              <span className="text-[10px] text-slate-400 font-mono">Pre-seeded SHA-256</span>
            </div>

            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => handleQuickLogin('admin', 'admin123')}
                disabled={loading}
                className="flex flex-col items-center justify-center p-2.5 rounded-xl bg-white/[0.03] hover:bg-amber-500/10 border border-white/10 hover:border-amber-500/40 text-left transition-all cursor-pointer group"
              >
                <Crown className="w-4 h-4 text-amber-400 mb-1 group-hover:scale-110 transition-transform" />
                <span className="text-xs font-bold text-white">admin</span>
                <span className="text-[10px] text-slate-400">admin123</span>
                <span className="text-[9px] px-1 rounded bg-amber-500/20 text-amber-300 mt-1 font-mono font-medium">ADMIN</span>
              </button>

              <button
                type="button"
                onClick={() => handleQuickLogin('test1', 'test123')}
                disabled={loading}
                className="flex flex-col items-center justify-center p-2.5 rounded-xl bg-white/[0.03] hover:bg-cyan-500/10 border border-white/10 hover:border-cyan-500/40 text-left transition-all cursor-pointer group"
              >
                <User className="w-4 h-4 text-cyan-400 mb-1 group-hover:scale-110 transition-transform" />
                <span className="text-xs font-bold text-white">test1</span>
                <span className="text-[10px] text-slate-400">test123</span>
                <span className="text-[9px] px-1 rounded bg-cyan-500/20 text-cyan-300 mt-1 font-mono font-medium">USER</span>
              </button>

              <button
                type="button"
                onClick={() => handleQuickLogin('test2', 'test223')}
                disabled={loading}
                className="flex flex-col items-center justify-center p-2.5 rounded-xl bg-white/[0.03] hover:bg-indigo-500/10 border border-white/10 hover:border-indigo-500/40 text-left transition-all cursor-pointer group"
              >
                <User className="w-4 h-4 text-indigo-400 mb-1 group-hover:scale-110 transition-transform" />
                <span className="text-xs font-bold text-white">test2</span>
                <span className="text-[10px] text-slate-400">test223</span>
                <span className="text-[9px] px-1 rounded bg-indigo-500/20 text-indigo-300 mt-1 font-mono font-medium">USER</span>
              </button>
            </div>
          </div>

          <div className="relative flex items-center justify-center">
            <div className="border-t border-white/10 w-full" />
            <span className="bg-[#0b0f19] px-3 text-[11px] text-slate-400 uppercase tracking-widest font-mono shrink-0">
              or enter manually
            </span>
          </div>

          {/* Manual Credentials Form */}
          <form onSubmit={handleCustomLogin} className="space-y-3">
            {errorMessage && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin, test1, test2"
                className="w-full px-3 py-2 bg-white/[0.04] border border-white/10 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-3 py-2 bg-white/[0.04] border border-white/10 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-white font-semibold text-xs transition-all shadow-md shadow-indigo-600/30 flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
            >
              {loading ? (
                <span>Authenticating...</span>
              ) : (
                <>
                  <LogIn className="w-4 h-4" />
                  <span>Sign In &amp; Bind Chat Session</span>
                </>
              )}
            </button>
          </form>

        </div>
      </div>
    </div>
  );
}
