"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Paperclip, Bot, User, Sparkles, Zap, Copy, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { GlassCard } from "@/components/glass/GlassCard";
import { useChatStore, type ChatMessage, type ChatAction } from "@/lib/chat-store";
import { AppShell } from "@/components/layout/AppShell";

export default function ChatPage() {
  const messages = useChatStore((s) => s.messages);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const activeIntent = useChatStore((s) => s.activeIntent);
  const simulateResponse = useChatStore((s) => s.simulateResponse);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const handleSend = useCallback(() => {
    const text = input.trim();
    if (!text || isStreaming) return;
    setInput("");
    simulateResponse(text);
  }, [input, isStreaming, simulateResponse]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  return (
    <AppShell title="Chat" contextContent={<ChatContext intent={activeIntent} />}>
      <div className="flex flex-col h-[calc(100vh-8rem)]">
        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-4 pb-4">
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
          {isStreaming && <ThinkingIndicator />}
        </div>

        {/* Input */}
        <div className="pt-3" style={{ borderTop: "1px solid var(--glass-border)" }}>
          <div className="glass-card !rounded-xl p-1">
            <div className="flex items-end gap-2">
              <button className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:text-foreground transition-colors mb-1" style={{ background: "var(--glass-bg)" }}>
                <Paperclip className="h-4 w-4" />
              </button>
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Tell the AI what's on your mind..."
                rows={1}
                className="flex-1 resize-none bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none py-2.5 max-h-[120px]"
                style={{ minHeight: "40px" }}
              />
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleSend}
                disabled={!input.trim() || isStreaming}
                className={cn(
                  "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-all mb-1",
                  input.trim() ? "bg-gradient-to-r from-indigo-500 to-violet-600 text-white shadow-lg shadow-indigo-500/20" : "text-muted-foreground"
                )}
                style={!input.trim() ? { background: "var(--glass-bg)" } : {}}
              >
                <Send className="h-4 w-4" />
              </motion.button>
            </div>
          </div>
          <p className="text-[10px] text-muted-foreground text-center mt-2">
            Enter to send · Shift+Enter for new line · AI responses are simulated
          </p>
        </div>
      </div>
    </AppShell>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);

  const copyContent = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn("flex gap-3", isUser && "flex-row-reverse")}
    >
      {/* Avatar */}
      <div className={cn(
        "flex h-8 w-8 shrink-0 items-center justify-center rounded-xl",
        isUser ? "bg-gradient-to-br from-violet-500/20 to-indigo-500/20" : "bg-gradient-to-br from-indigo-500/20 to-cyan-500/20"
      )}>
        {isUser ? <User className="h-4 w-4 text-violet-400" /> : <Bot className="h-4 w-4 text-primary" />}
      </div>

      {/* Content */}
      <div className={cn("flex-1 max-w-[85%] min-w-0", isUser && "flex flex-col items-end")}>
        {/* Intent badge */}
        {message.intent && (
          <div className="flex items-center gap-1.5 mb-1.5">
            <Sparkles className="h-3 w-3 text-primary" />
            <span className="text-[10px] font-semibold text-primary">{message.intent.label}</span>
            <span className="text-[10px] text-muted-foreground">{message.intent.confidence}%</span>
          </div>
        )}

        {/* Memory chips */}
        {message.memory && message.memory.length > 0 && !isUser && (
          <div className="flex flex-wrap gap-1 mb-2">
            {message.memory.map((m) => (
              <span key={m} className="text-[10px] px-2 py-0.5 rounded-md bg-violet-500/10 text-violet-400 border border-violet-500/20">
                🧠 {m}
              </span>
            ))}
          </div>
        )}

        {/* Execution steps */}
        {message.executionSteps && !isUser && (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {message.executionSteps.map((step) => (
              <span key={step.label} className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-md" style={{ background: "var(--glass-bg)", border: "1px solid var(--glass-border)" }}>
                {step.status === "done" ? <Check className="h-2.5 w-2.5 text-emerald-400" /> : <Zap className="h-2.5 w-2.5 text-primary animate-pulse" />}
                <span className="text-muted-foreground">{step.label}</span>
              </span>
            ))}
          </div>
        )}

        {/* Message body */}
        <GlassCard className={cn(
          "p-4 !rounded-2xl",
          isUser ? "!rounded-tr-md bg-gradient-to-br from-indigo-500/10 to-violet-500/5" : "!rounded-tl-md"
        )}>
          <div className="prose prose-sm prose-invert max-w-none text-sm text-foreground leading-relaxed">
            <MarkdownContent content={message.content} />
            {message.isStreaming && <span className="inline-block w-0.5 h-4 bg-primary animate-pulse ml-0.5 align-text-bottom" />}
          </div>

          {/* Copy button */}
          {!isUser && message.content && !message.isStreaming && (
            <button onClick={copyContent} className="mt-2 flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors">
              {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
              {copied ? "Copied" : "Copy"}
            </button>
          )}
        </GlassCard>

        {/* Action buttons */}
        {message.actions && !message.isStreaming && (
          <div className="flex flex-wrap gap-2 mt-2">
            {message.actions.map((action) => (
              <ActionBtn key={action.id} action={action} />
            ))}
          </div>
        )}

        {/* Timestamp */}
        <span className="text-[10px] text-muted-foreground mt-1 block">
          {new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </span>
      </div>
    </motion.div>
  );
}

function ActionBtn({ action }: { action: ChatAction }) {
  return (
    <motion.button
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.97 }}
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium text-primary glass-card !rounded-lg"
    >
      <Zap className="h-3 w-3" />
      {action.label}
    </motion.button>
  );
}

function MarkdownContent({ content }: { content: string }) {
  // Simple markdown renderer
  const lines = content.split("\n");
  return (
    <>
      {lines.map((line, i) => {
        if (line.startsWith("## ")) return <h3 key={i} className="text-sm font-bold text-foreground mt-3 mb-1">{line.slice(3)}</h3>;
        if (line.startsWith("**") && line.endsWith("**")) return <p key={i} className="font-semibold text-foreground">{line.slice(2, -2)}</p>;
        if (line.startsWith("> ")) return <blockquote key={i} className="border-l-2 border-primary/30 pl-3 text-muted-foreground italic my-2">{line.slice(2)}</blockquote>;
        if (line.startsWith("- ")) return <div key={i} className="flex items-start gap-2"><span className="text-primary mt-1">•</span><span>{formatInline(line.slice(2))}</span></div>;
        if (/^\d+\.\s/.test(line)) return <div key={i} className="flex items-start gap-2"><span className="text-primary font-semibold">{line.match(/^(\d+)/)?.[1]}.</span><span>{formatInline(line.replace(/^\d+\.\s/, ""))}</span></div>;
        if (line.startsWith("*") && line.endsWith("*")) return <p key={i} className="italic text-muted-foreground">{line.slice(1, -1)}</p>;
        if (line === "") return <div key={i} className="h-2" />;
        return <p key={i}>{formatInline(line)}</p>;
      })}
    </>
  );
}

function formatInline(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={i} className="font-semibold text-foreground">{part.slice(2, -2)}</strong>;
    return <span key={i}>{part}</span>;
  });
}

function ThinkingIndicator() {
  const hints = ["Analyzing behavioral patterns…", "Evaluating career signals…", "Computing recommendations…"];
  const [idx, setIdx] = useState(0);
  useEffect(() => { const t = setInterval(() => setIdx((i) => (i + 1) % hints.length), 2000); return () => clearInterval(t); }, [hints.length]);

  return (
    <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} className="flex gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/20 to-cyan-500/20">
        <Bot className="h-4 w-4 text-primary animate-pulse" />
      </div>
      <GlassCard className="p-3 !rounded-2xl !rounded-tl-md">
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            <div className="h-1.5 w-1.5 rounded-full bg-primary typing-dot" />
            <div className="h-1.5 w-1.5 rounded-full bg-primary typing-dot" />
            <div className="h-1.5 w-1.5 rounded-full bg-primary typing-dot" />
          </div>
          <AnimatePresence mode="wait">
            <motion.span key={idx} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-[11px] text-primary font-medium">
              {hints[idx]}
            </motion.span>
          </AnimatePresence>
        </div>
      </GlassCard>
    </motion.div>
  );
}

function ChatContext({ intent }: { intent: { type: string; confidence: number; label: string } | null }) {
  return (
    <div className="space-y-4">
      <GlassCard className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="h-3.5 w-3.5 text-primary" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Detected Intent</span>
        </div>
        {intent ? (
          <div>
            <p className="text-sm font-semibold text-foreground">{intent.label}</p>
            <p className="text-[11px] text-muted-foreground mt-1">Confidence: {intent.confidence}%</p>
            <div className="h-1 rounded-full mt-2 overflow-hidden" style={{ background: "var(--glass-bg-elevated)" }}>
              <motion.div className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500" animate={{ width: `${intent.confidence}%` }} transition={{ duration: 0.8 }} />
            </div>
          </div>
        ) : (
          <p className="text-[11px] text-muted-foreground">Send a message to activate intent detection</p>
        )}
      </GlassCard>

      <GlassCard className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">🧠 Conversation Memory</span>
        </div>
        <div className="space-y-1.5">
          <p className="text-[11px] text-muted-foreground">Memory grows as you chat. The AI remembers your goals, preferences, and frustrations.</p>
        </div>
      </GlassCard>
    </div>
  );
}
