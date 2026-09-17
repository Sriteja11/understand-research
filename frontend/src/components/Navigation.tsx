import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { MessageSquare, Files, CheckCircle2 } from 'lucide-react';

export const Navigation: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const isChat = location.pathname.startsWith('/chat') || location.pathname === '/';
  const isDocs = location.pathname.startsWith('/documents');
  const isEval = location.pathname.startsWith('/evaluation');

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div
          onClick={() => navigate('/chat')}
          className="flex items-center space-x-3 cursor-pointer"
        >
          <div className="w-9 h-9 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold text-lg shadow-sm">
            R
          </div>
          <div>
            <h1 className="text-base font-semibold text-slate-900 leading-tight">
              Evidence grounded research assistant
            </h1>
            <p className="text-xs text-slate-500 font-mono">
              Local RAG with verified citations
            </p>
          </div>
        </div>

        <nav className="flex space-x-1 bg-slate-100 p-1 rounded-lg border border-slate-200">
          <button
            onClick={() => navigate('/chat')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-md text-sm font-medium transition-colors ${
              isChat
                ? 'bg-white text-indigo-700 shadow-sm'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
            }`}
          >
            <MessageSquare className="w-4 h-4" />
            <span>Chat</span>
          </button>

          <button
            onClick={() => navigate('/documents')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-md text-sm font-medium transition-colors ${
              isDocs
                ? 'bg-white text-indigo-700 shadow-sm'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
            }`}
          >
            <Files className="w-4 h-4" />
            <span>Documents</span>
          </button>

          <button
            onClick={() => navigate('/evaluation')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-md text-sm font-medium transition-colors ${
              isEval
                ? 'bg-white text-indigo-700 shadow-sm'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
            }`}
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>Evaluation</span>
          </button>
        </nav>

        <div className="flex items-center space-x-2 text-xs text-slate-500">
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
            Local vector store active
          </span>
        </div>
      </div>
    </header>
  );
};
