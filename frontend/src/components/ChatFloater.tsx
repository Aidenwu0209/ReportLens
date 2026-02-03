/**
 * Q&A chat floater – a bottom-right floating panel for asking questions
 * about the annual report. Answers include page citations with
 * clickable highlights.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import apiClient from '../api/client';
import { useAppStore } from '../stores/appStore';
import type { ChatMessage } from '../types/api';

interface ChatFloaterProps {
  versionId: string;
}

export default function ChatFloater({ versionId }: ChatFloaterProps) {
  const { chatSessionId, setChatSession, setHighlights } = useAppStore();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Create session on first open
  useEffect(() => {
    if (open && !chatSessionId) {
      apiClient.createChatSession(versionId).then((s) => {
        setChatSession(s.session_id);
      });
    }
  }, [open, chatSessionId, versionId, setChatSession]);

  const sendMessage = useCallback(async () => {
    if (!input.trim() || !chatSessionId || loading) return;
    const text = input.trim();
    setInput('');
    setLoading(true);

    // Optimistic user msg
    setMessages((prev) => [
      ...prev,
      {
        message_id: `tmp_${Date.now()}`,
        role: 'user',
        content: text,
        evidence_refs: null,
        created_at: new Date().toISOString(),
      },
    ]);

    try {
      const resp = await apiClient.sendMessage(chatSessionId, text);
      setMessages((prev) => [...prev.filter((m) => !m.message_id.startsWith('tmp_')), {
        message_id: prev.find(m => m.message_id.startsWith('tmp_'))?.message_id.replace('tmp_', 'usr_') || `usr_${Date.now()}`,
        role: 'user',
        content: text,
        evidence_refs: null,
        created_at: new Date().toISOString(),
      }, resp]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          message_id: `err_${Date.now()}`,
          role: 'assistant',
          content: '抱歉，暂时无法回答，请稍后重试。',
          evidence_refs: null,
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  }, [input, chatSessionId, loading]);

  // Auto-scroll
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const handleEvidenceClick = (refs: any[]) => {
    if (refs?.length) {
      setHighlights(refs, refs[0].page_no);
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 w-14 h-14 bg-primary-electric hover:bg-primary-hover rounded-full shadow-glow flex items-center justify-center transition-all duration-300 z-50"
      >
        <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
          />
        </svg>
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 w-96 h-[500px] glass-card-elevated flex flex-col z-50 animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
        <h3 className="text-text-primary font-medium text-sm">智能问答</h3>
        <button onClick={() => setOpen(false)} className="text-text-muted hover:text-text-primary">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <p className="text-text-muted text-xs text-center mt-8">
            输入问题，AI 将基于年报内容回答
          </p>
        )}
        {messages.map((msg) => (
          <div
            key={msg.message_id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                msg.role === 'user'
                  ? 'bg-primary-electric text-white'
                  : 'bg-surface-elevated text-text-primary'
              }`}
            >
              <p>{msg.content}</p>
              {msg.evidence_refs && msg.evidence_refs.length > 0 && (
                <button
                  onClick={() => handleEvidenceClick(msg.evidence_refs!)}
                  className="text-primary-hover text-[10px] mt-1 hover:underline"
                >
                  查看来源 (第{msg.evidence_refs.map((e) => e.page_no).join(', ')}页)
                </button>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-surface-elevated rounded-lg px-3 py-2">
              <div className="flex gap-1">
                <div className="w-2 h-2 rounded-full bg-text-muted animate-bounce" />
                <div className="w-2 h-2 rounded-full bg-text-muted animate-bounce" style={{ animationDelay: '0.1s' }} />
                <div className="w-2 h-2 rounded-full bg-text-muted animate-bounce" style={{ animationDelay: '0.2s' }} />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-white/10">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="输入问题..."
            className="flex-1 bg-surface rounded-lg px-3 py-2 text-sm text-text-primary placeholder-text-muted outline-none focus:ring-1 focus:ring-primary-electric"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="bg-primary-electric hover:bg-primary-hover disabled:opacity-40 text-white rounded-lg px-3 py-2 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
