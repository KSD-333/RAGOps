import React, { useState } from 'react';
import { X, Copy, Check, FileText, CheckCircle2 } from 'lucide-react';

export default function ChunkModal({ chunk, onClose }) {
  const [copied, setCopied] = useState(false);

  if (!chunk) return null;

  const handleCopy = () => {
    if (chunk.text) {
      navigator.clipboard.writeText(chunk.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div 
        className="bg-[#0f1422] border border-white/10 rounded-2xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl shadow-black overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between bg-white/[0.02]">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <span className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-semibold">
                {chunk.document || 'source.md'}
              </span>
              <h3 className="text-base font-semibold text-white mt-1">
                Retrieved Context Chunk ({chunk.chunk_id || 'chunk_1'})
              </h3>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.08] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Metadata Strip */}
        <div className="px-6 py-3 bg-[#0a0d15] border-b border-white/5 flex flex-wrap items-center justify-between gap-4 text-xs font-mono text-slate-400">
          <div className="flex items-center gap-4">
            <div>
              <span className="text-slate-500">Relevance: </span>
              <span className="text-emerald-400 font-semibold">{chunk.score || '92% Match'}</span>
            </div>
            <div>
              <span className="text-slate-500">Section: </span>
              <span className="text-slate-200">{chunk.section || 'General'}</span>
            </div>
          </div>
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.06] hover:bg-white/[0.12] text-slate-200 border border-white/10 transition-colors"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy Payload'}</span>
          </button>
        </div>

        {/* Modal Body - Chunk Content */}
        <div className="p-6 overflow-y-auto flex-1 bg-[#07090e]">
          <div className="text-xs uppercase tracking-wider text-slate-400 font-semibold mb-2">
            Exact Raw Payload Sent to LLM Grounding Context:
          </div>
          <div className="bg-[#0c101a] border border-white/10 rounded-xl p-4 text-sm font-mono text-slate-200 leading-relaxed whitespace-pre-wrap select-all">
            {chunk.text || 'No text content available for this chunk.'}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-white/10 bg-white/[0.02] flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-white text-sm font-medium transition-colors"
          >
            Close Dialog
          </button>
        </div>
      </div>
    </div>
  );
}
