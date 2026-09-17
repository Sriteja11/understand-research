import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Send,
  Plus,
  Trash2,
  Clock,
  ChevronDown,
  ChevronRight,
  FileText,
  ShieldAlert,
  Sparkles,
  Copy,
  Check,
  PanelLeftClose,
  PanelLeft,
  Sliders,
  Search,
  ExternalLink
} from 'lucide-react';
import { Message, Session, EvidenceItem } from '../types';
import { fetchSessions, createSession, fetchSession, deleteSession } from '../api/sessions';
import { streamChat } from '../api/chat';

const QUICK_PROMPTS = [
  "What is scaled dot-product attention and how is it computed?",
  "What is the difference between RAG-Sequence and RAG-Token models?",
  "How does ReAct combine reasoning traces and task-specific actions?",
  "What is indirect prompt injection according to Greshake et al.?"
];

export const ChatPage: React.FC = () => {
  const { sessionId: routeSessionId } = useParams<{ sessionId?: string }>();
  const navigate = useNavigate();

  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string>('');
  const [currentTitle, setCurrentTitle] = useState<string>('New Research Session');
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputQuery, setInputQuery] = useState<string>('');
  const [topK, setTopK] = useState<number>(10);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [expandedEvidence, setExpandedEvidence] = useState<{ [msgId: string]: boolean }>({});
  const [copiedMsgId, setCopiedMsgId] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(true);
  const [showSettings, setShowSettings] = useState<boolean>(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      const list = await fetchSessions();
      setSessions(list);
      if (routeSessionId) {
        loadSessionData(routeSessionId);
      } else if (list.length > 0) {
        navigate(`/chat/${list[0].id}`, { replace: true });
      } else {
        handleNewSession();
      }
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    if (routeSessionId && routeSessionId !== currentSessionId) {
      loadSessionData(routeSessionId);
    }
  }, [routeSessionId]);

  const loadSessionData = async (id: string) => {
    try {
      const data = await fetchSession(id);
      setCurrentSessionId(data.id);
      setMessages(data.messages || []);
      if (data.title) setCurrentTitle(data.title);
    } catch {
      navigate('/chat', { replace: true });
    }
  };

  const handleNewSession = async () => {
    try {
      const newSess = await createSession('New Research Session');
      setSessions((prev) => [newSess, ...prev]);
      setCurrentSessionId(newSess.id);
      setCurrentTitle(newSess.title);
      setMessages([]);
      navigate(`/chat/${newSess.id}`);
      if (textareaRef.current) textareaRef.current.focus();
    } catch {
      // ignore
    }
  };

  const handleDeleteSession = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await deleteSession(id);
      const remaining = sessions.filter((s) => s.id !== id);
      setSessions(remaining);
      if (currentSessionId === id) {
        if (remaining.length > 0) {
          navigate(`/chat/${remaining[0].id}`);
        } else {
          handleNewSession();
        }
      }
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  const toggleEvidence = (msgId: string) => {
    setExpandedEvidence((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  const copyToClipboard = (text: string, msgId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedMsgId(msgId);
    setTimeout(() => setCopiedMsgId(null), 2000);
  };

  const handleSendMessage = async (queryText?: string) => {
    const textToSend = (queryText || inputQuery).trim();
    if (!textToSend || isStreaming) return;

    setInputQuery('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    const userMsgId = `user_${Date.now()}`;
    const assistantMsgId = `asst_${Date.now()}`;

    const userMessage: Message = {
      id: userMsgId,
      role: 'user',
      content: textToSend,
    };

    const assistantPlaceholder: Message = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      isStreaming: true,
      evidence: [],
      citations: [],
    };

    setMessages((prev) => [...prev, userMessage, assistantPlaceholder]);
    setIsStreaming(true);

    // If session was default title, eagerly update title in UI
    if (currentTitle === 'New Research Session') {
      const cleanTitle = textToSend.slice(0, 50) + (textToSend.length > 50 ? '...' : '');
      setCurrentTitle(cleanTitle);
      setSessions((prev) =>
        prev.map((s) => (s.id === currentSessionId ? { ...s, title: cleanTitle } : s))
      );
    }

    let accumulatedTokens = '';

    await streamChat(textToSend, currentSessionId, topK, {
      onToken: (token) => {
        accumulatedTokens += token;
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantMsgId ? { ...m, content: accumulatedTokens } : m))
        );
      },
      onEvidence: (evidence) => {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantMsgId ? { ...m, evidence } : m))
        );
      },
      onCitation: (citations) => {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantMsgId ? { ...m, citations } : m))
        );
      },
      onComplete: (data) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  content: data.answer,
                  evidence: data.evidence,
                  citations: data.citations,
                  grounded: data.grounded,
                  latency_ms: data.latency_ms,
                  isStreaming: false,
                }
              : m
          )
        );
        setIsStreaming(false);
        // Refresh session list to pick up updated title from backend
        fetchSessions().then(setSessions).catch(() => {});
      },
      onError: (err) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  content: `Error: ${err}`,
                  isStreaming: false,
                }
              : m
          )
        );
        setIsStreaming(false);
      },
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleTextareaInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputQuery(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] w-full overflow-hidden bg-slate-50">
      {/* Collapsible Sidebar */}
      <aside
        className={`${
          isSidebarOpen ? 'w-72 lg:w-80' : 'w-0'
        } transition-all duration-200 ease-in-out border-r border-slate-200 bg-white flex flex-col z-10 shrink-0 overflow-hidden`}
      >
        <div className="p-3.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold text-slate-700 tracking-wide">
              Research sessions
            </span>
            <span className="text-[11px] font-mono bg-slate-200 text-slate-600 px-1.5 py-0.2 rounded-full">
              {sessions.length}
            </span>
          </div>
          <button
            onClick={handleNewSession}
            className="inline-flex items-center space-x-1 text-xs bg-indigo-600 text-white hover:bg-indigo-700 px-2.5 py-1.5 rounded-md font-medium shadow-sm transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New chat</span>
          </button>
        </div>

        {/* Sessions list */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {sessions.length === 0 ? (
            <div className="text-center py-8 text-xs text-slate-400">No sessions yet</div>
          ) : (
            sessions.map((s) => {
              const isSelected = currentSessionId === s.id;
              return (
                <div
                  key={s.id}
                  onClick={() => navigate(`/chat/${s.id}`)}
                  className={`group relative flex items-center justify-between px-3 py-2.5 rounded-lg text-xs cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-indigo-50 text-indigo-950 font-medium border border-indigo-200/70 shadow-xs'
                      : 'text-slate-700 hover:bg-slate-100 border border-transparent'
                  }`}
                >
                  <div className="flex items-center space-x-2 truncate pr-6">
                    <FileText
                      className={`w-3.5 h-3.5 shrink-0 ${
                        isSelected ? 'text-indigo-600' : 'text-slate-400'
                      }`}
                    />
                    <span className="truncate">{s.title || 'New Research Session'}</span>
                  </div>
                  <button
                    onClick={(e) => handleDeleteSession(s.id, e)}
                    className="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-rose-600 rounded transition-opacity absolute right-2"
                    title="Delete session"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* Retrieval Settings Footer */}
        <div className="p-3.5 border-t border-slate-200 bg-slate-50 text-xs space-y-2">
          <div className="flex items-center justify-between text-slate-600 font-medium">
            <span className="flex items-center space-x-1.5">
              <Sliders className="w-3.5 h-3.5 text-indigo-600" />
              <span>Initial Top-K chunks</span>
            </span>
            <span className="font-semibold text-slate-900 bg-white px-2 py-0.5 rounded border border-slate-200">
              {topK}
            </span>
          </div>
          <input
            type="range"
            min="3"
            max="25"
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
            className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
          />
          <p className="text-[11px] text-slate-400 leading-tight">
            Top candidates passed to the hybrid cross-encoder reranker.
          </p>
        </div>
      </aside>

      {/* Main Chat Workspace */}
      <main className="flex-1 flex flex-col h-full min-w-0 overflow-hidden">
        {/* Workspace Top Bar */}
        <div className="h-12 bg-white border-b border-slate-200 px-4 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-3 truncate">
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-md transition-colors"
              title={isSidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
            >
              {isSidebarOpen ? (
                <PanelLeftClose className="w-4 h-4" />
              ) : (
                <PanelLeft className="w-4 h-4" />
              )}
            </button>
            <span className="text-sm font-semibold text-slate-800 truncate max-w-lg">
              {currentTitle}
            </span>
          </div>

          <div className="flex items-center space-x-2 text-xs text-slate-500">
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700">
              Rerank Top-4
            </span>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-indigo-50 text-indigo-700">
              OpenRouter + Fallback
            </span>
          </div>
        </div>

        {/* Message Thread Scroll Area */}
        <div className="flex-1 overflow-y-auto px-4 lg:px-8 py-6 space-y-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {messages.length === 0 && (
              <div className="py-16 text-center space-y-4">
                <div className="w-12 h-12 bg-indigo-100 text-indigo-600 rounded-xl flex items-center justify-center mx-auto shadow-inner">
                  <Sparkles className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-slate-800">
                    AI Research Knowledge Base
                  </h2>
                  <p className="text-sm text-slate-500 max-w-md mx-auto mt-1">
                    Ask questions across 5 bundled research papers. Every answer is grounded in retrieved excerpts with verified citations.
                  </p>
                </div>

                {/* Quick prompt cards */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-w-2xl mx-auto pt-4 text-left">
                  {QUICK_PROMPTS.map((prompt, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSendMessage(prompt)}
                      className="p-3 bg-white hover:bg-indigo-50/50 border border-slate-200 hover:border-indigo-300 rounded-xl text-xs text-slate-700 transition-all shadow-xs hover:shadow-sm text-left flex items-start space-x-2 group"
                    >
                      <Search className="w-3.5 h-3.5 text-indigo-500 mt-0.5 shrink-0 group-hover:scale-110 transition-transform" />
                      <span className="line-clamp-2">{prompt}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m) => {
              const isUser = m.role === 'user';
              return (
                <div
                  key={m.id}
                  className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} space-y-1.5`}
                >
                  <div className="flex items-center space-x-2 text-[11px] font-mono text-slate-400 px-1">
                    <span>{isUser ? 'You' : 'AI Assistant'}</span>
                  </div>

                  <div
                    className={`rounded-2xl px-5 py-4 text-sm leading-relaxed max-w-full lg:max-w-3xl shadow-xs ${
                      isUser
                        ? 'bg-indigo-600 text-white font-normal'
                        : 'bg-white border border-slate-200/90 text-slate-800'
                    }`}
                  >
                    {/* Markdown rendering for assistant or plain text for user */}
                    {isUser ? (
                      <div className="whitespace-pre-wrap">{m.content}</div>
                    ) : (
                      <div className="prose prose-sm prose-slate max-w-none prose-headings:font-semibold prose-headings:text-slate-900 prose-headings:mb-2 prose-headings:mt-4 prose-p:my-2 prose-ul:my-2 prose-li:my-0.5 prose-pre:bg-slate-900 prose-pre:text-slate-100 prose-pre:rounded-lg prose-code:text-indigo-600 prose-code:bg-indigo-50 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none">
                        {m.content ? (
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {m.content}
                          </ReactMarkdown>
                        ) : m.isStreaming ? (
                          <div className="flex items-center space-x-2 text-slate-500 py-1 font-sans">
                            <span className="inline-block w-2 h-2 rounded-full bg-indigo-600 animate-ping" />
                            <span>Retrieving evidence and formulating answer...</span>
                          </div>
                        ) : null}
                      </div>
                    )}

                    {/* Assistant Metadata Footer */}
                    {!isUser && !m.isStreaming && (
                      <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-xs">
                        <div className="flex items-center space-x-2">
                          {m.latency_ms !== undefined && (
                            <span className="inline-flex items-center space-x-1 text-slate-500 bg-slate-100 px-2 py-0.5 rounded text-[11px]">
                              <Clock className="w-3 h-3" />
                              <span>{m.latency_ms.toFixed(0)} ms</span>
                            </span>
                          )}

                          {m.grounded === false ? (
                            <span className="bg-amber-100 text-amber-800 px-2 py-0.5 rounded text-[11px] font-medium">
                              Refusal / Insufficient evidence
                            </span>
                          ) : (
                            <span className="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded text-[11px] font-medium">
                              Evidence grounded
                            </span>
                          )}
                        </div>

                        <div className="flex items-center space-x-3">
                          <button
                            onClick={() => copyToClipboard(m.content, m.id)}
                            className="inline-flex items-center space-x-1 text-slate-400 hover:text-slate-700 transition-colors"
                            title="Copy response"
                          >
                            {copiedMsgId === m.id ? (
                              <Check className="w-3.5 h-3.5 text-emerald-600" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                            <span className="text-[11px]">
                              {copiedMsgId === m.id ? 'Copied' : 'Copy'}
                            </span>
                          </button>

                          {m.evidence && m.evidence.length > 0 && (
                            <button
                              onClick={() => toggleEvidence(m.id)}
                              className="inline-flex items-center space-x-1 text-indigo-600 hover:text-indigo-800 font-medium text-[11px]"
                            >
                              <span>{m.evidence.length} supporting passages</span>
                              {expandedEvidence[m.id] ? (
                                <ChevronDown className="w-3.5 h-3.5" />
                              ) : (
                                <ChevronRight className="w-3.5 h-3.5" />
                              )}
                            </button>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Citations Badges */}
                    {!isUser && m.citations && m.citations.length > 0 && (
                      <div className="mt-3.5 flex flex-wrap gap-1.5">
                        {m.citations.map((c, i) => (
                          <span
                            key={i}
                            className="inline-flex items-center space-x-1 text-[11px] bg-indigo-50/70 text-indigo-900 border border-indigo-200/60 px-2.5 py-1 rounded-md"
                          >
                            <FileText className="w-3 h-3 text-indigo-500 shrink-0" />
                            <span className="font-semibold truncate max-w-[200px]">
                              {c.document}
                            </span>
                            <span className="text-slate-500">· Page {c.page}</span>
                            <span className="text-slate-400 font-mono text-[10px]">
                              [{c.chunk_id}]
                            </span>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Supporting Passages Drawer */}
                  {!isUser && expandedEvidence[m.id] && m.evidence && (
                    <div className="mt-2 w-full max-w-full lg:max-w-3xl bg-slate-100/90 border border-slate-200 rounded-xl p-4 space-y-3">
                      <div className="flex items-center justify-between text-xs font-semibold text-slate-700 uppercase tracking-wider">
                        <span>Retrieved Evidence Passages (Top {m.evidence.length})</span>
                        <span className="text-[11px] font-normal text-slate-500">
                          Ranked by hybrid score
                        </span>
                      </div>

                      <div className="space-y-2.5">
                        {m.evidence.map((ev, idx) => (
                          <div
                            key={idx}
                            className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-2xs text-xs space-y-1.5"
                          >
                            <div className="flex flex-wrap items-center justify-between gap-1 text-slate-600">
                              <div className="flex items-center space-x-1.5 font-semibold text-slate-900">
                                <FileText className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
                                <span>{ev.document}</span>
                                <span className="text-slate-400 font-normal">· Page {ev.page}</span>
                              </div>
                              <span className="bg-indigo-50 text-indigo-700 font-mono text-[11px] px-2 py-0.5 rounded-full font-medium">
                                Relevance: {(ev.score * 100).toFixed(1)}%
                              </span>
                            </div>

                            <div className="flex items-center space-x-2 text-[11px] text-slate-400 font-mono">
                              <span>Section: {ev.section}</span>
                              <span>•</span>
                              <span>ID: {ev.chunk_id}</span>
                            </div>

                            <p className="text-slate-700 whitespace-pre-wrap leading-relaxed pt-1 border-t border-slate-50 font-sans">
                              {ev.text}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Bar Area */}
        <div className="p-4 lg:px-8 bg-white border-t border-slate-200 shrink-0">
          <div className="max-w-4xl mx-auto">
            <div className="relative flex items-end bg-slate-50 border border-slate-300 focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-200/50 rounded-2xl p-2 transition-all shadow-xs">
              <textarea
                ref={textareaRef}
                value={inputQuery}
                onChange={handleTextareaInput}
                onKeyDown={handleKeyDown}
                placeholder="Ask a technical question from the AI research papers (Enter to send, Shift+Enter for newline)..."
                disabled={isStreaming}
                rows={1}
                className="w-full bg-transparent resize-none px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-none max-h-40 min-h-[40px]"
              />
              <button
                type="button"
                onClick={() => handleSendMessage()}
                disabled={isStreaming || !inputQuery.trim()}
                className="mb-1 mr-1 p-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl disabled:opacity-40 disabled:cursor-not-allowed transition-colors shrink-0 shadow-xs"
                title="Send message"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>

            <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400 px-1">
              <span>Press Enter to send, Shift+Enter for new line</span>
              <span>All retrieved context treated as untrusted data</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};
