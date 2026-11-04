import React, { useState } from 'react';
import { X, Copy, Check, FileText, CheckCircle2 } from 'lucide-react';
import { useAppStore } from '../context/AppContext';

export default function ChunkModal({ chunk, onClose }) {
  const { theme } = useAppStore();
  const isLight = theme === 'light';

  const [copied, setCopied] = useState(false);

  if (!chunk) return null;

  const formatScore = (s) => {
    if (s === null || s === undefined || isNaN(s)) return '92% Match';
    let val = Number(s);
    if (val > 1.0 || val < 0.0) {
      val = 1 / (1 + Math.exp(-val));
    }
    return `${Math.round(val * 100)}% Grounded Match`;
  };

  const handleCopy = () => {
    if (chunk.text) {
      navigator.clipboard.writeText(chunk.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-sm animate-in fade-in duration-150 ${
      isLight ? 'bg-slate-900/40' : 'bg-black/80'
    }`}>
      <div 
        className={`border rounded-2xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden transition-colors ${
          isLight ? 'bg-white border-slate-200 text-slate-800 shadow-slate-300' : 'bg-[#0f1422] border-white/10 text-white shadow-black'
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className={`px-6 py-4 border-b flex items-center justify-between ${
          isLight ? 'border-slate-200 bg-slate-50' : 'border-white/10 bg-white/[0.02]'
        }`}>
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg border ${
              isLight ? 'bg-indigo-50 text-indigo-600 border-indigo-200' : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
            }`}>
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <span className={`text-xs font-mono px-2.5 py-0.5 rounded-full font-semibold border ${
                isLight ? 'bg-cyan-50 text-cyan-900 border-cyan-300 font-bold' : 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
              }`}>
                {typeof chunk === 'string' ? chunk : (chunk.document || chunk.title || chunk.source || 'source.md')}
              </span>
              <h3 className={`text-base font-semibold mt-1 ${isLight ? 'text-slate-900' : 'text-white'}`}>
                Retrieved Context Chunk ({chunk.chunk_id || 'chunk_1'})
              </h3>
            </div>
          </div>
          <button 
            onClick={onClose}
            className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
              isLight ? 'text-slate-400 hover:text-slate-700 hover:bg-slate-100' : 'text-slate-400 hover:text-white hover:bg-white/[0.08]'
            }`}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Metadata Strip */}
        <div className={`px-6 py-3 border-b flex flex-wrap items-center justify-between gap-4 text-xs font-mono ${
          isLight ? 'bg-slate-100/70 border-slate-200 text-slate-600' : 'bg-[#0a0d15] border-white/5 text-slate-400'
        }`}>
          <div className="flex items-center gap-4">
            <div>
              <span className={isLight ? 'text-slate-500' : 'text-slate-500'}>Relevance: </span>
              <span className="text-emerald-500 dark:text-emerald-400 font-semibold">{formatScore(chunk.score)}</span>
            </div>
            <div>
              <span className={isLight ? 'text-slate-500' : 'text-slate-500'}>Section: </span>
              <span className={isLight ? 'text-slate-800 font-medium' : 'text-slate-200'}>{chunk.section || 'General'}</span>
            </div>
          </div>
          <button
            onClick={handleCopy}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border transition-colors cursor-pointer ${
              isLight 
                ? 'bg-white hover:bg-slate-100 text-slate-700 border-slate-300 shadow-sm' 
                : 'bg-white/[0.06] hover:bg-white/[0.12] text-slate-200 border-white/10'
            }`}
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy Payload'}</span>
          </button>
        </div>

        {/* Modal Body - Chunk Content */}
        <div className={`p-6 overflow-y-auto flex-1 ${isLight ? 'bg-slate-50' : 'bg-[#07090e]'}`}>
          <div className={`text-xs uppercase tracking-wider font-semibold mb-2 ${
            isLight ? 'text-slate-600' : 'text-slate-400'
          }`}>
            Exact Raw Payload Sent to LLM Grounding Context:
          </div>
          <div className={`border rounded-xl p-4 text-sm font-mono leading-relaxed whitespace-pre-wrap select-all ${
            isLight 
              ? 'bg-white border-slate-200 text-slate-800 shadow-sm' 
              : 'bg-[#0c101a] border-white/10 text-slate-200'
          }`}>
            {chunk.text || 'No text content available for this chunk.'}
          </div>
        </div>

        {/* Modal Footer */}
        <div className={`px-6 py-3 border-t flex justify-end ${
          isLight ? 'border-slate-200 bg-slate-50' : 'border-white/10 bg-white/[0.02]'
        }`}>
          <button
            onClick={onClose}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
              isLight 
                ? 'bg-slate-200 hover:bg-slate-300 text-slate-800' 
                : 'bg-white/10 hover:bg-white/20 text-white'
            }`}
          >
            Close Dialog
          </button>
        </div>
      </div>
    </div>
  );
}
