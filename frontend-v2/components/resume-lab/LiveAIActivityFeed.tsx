"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Terminal, Activity, CheckCircle2 } from "lucide-react";
import { GlassCard } from "@/components/glass/GlassCard";

interface AIEvent {
  id: string;
  type: "START" | "PROGRESS" | "COMPLETE";
  message: string;
  progress?: number;
  timestamp: string;
}

export function LiveAIActivityFeed({ userId, onComplete }: { userId: string, onComplete: (data: any) => void }) {
  const [events, setEvents] = useState<AIEvent[]>([]);
  const [isListening, setIsListening] = useState(false);

  useEffect(() => {
    if (!userId) return;

    setIsListening(true);
    // Connect to SSE stream
    const eventSource = new EventSource(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/resume/stream/${userId}`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      const newEvent: AIEvent = {
        id: Math.random().toString(36).substr(2, 9),
        type: data.type,
        message: data.message,
        progress: data.progress,
        timestamp: new Date().toISOString()
      };

      setEvents((prev) => [...prev, newEvent]);

      if (data.type === "COMPLETE") {
        eventSource.close();
        setIsListening(false);
        if (onComplete && data.data) {
          onComplete(data.data);
        }
      }
    };

    eventSource.onerror = (error) => {
      console.error("SSE Error:", error);
      eventSource.close();
      setIsListening(false);
    };

    return () => {
      eventSource.close();
    };
  }, [userId, onComplete]);

  if (events.length === 0) return null;

  return (
    <GlassCard className="p-4 bg-black/40 border-indigo-500/20 backdrop-blur-3xl overflow-hidden relative">
      <div className="absolute inset-0 bg-gradient-to-b from-indigo-500/5 to-transparent pointer-events-none"></div>
      
      <div className="flex items-center gap-2 mb-4 border-b border-border/50 pb-2">
        <Terminal className="h-4 w-4 text-indigo-400" />
        <h3 className="text-xs font-mono font-semibold text-indigo-300 tracking-wider">AI Execution Stream</h3>
        {isListening && (
          <span className="flex h-2 w-2 rounded-full bg-indigo-500 ml-auto animate-pulse"></span>
        )}
      </div>

      <div className="space-y-3 font-mono text-[11px] max-h-[200px] overflow-y-auto scrollbar-thin">
        <AnimatePresence initial={false}>
          {events.map((evt, idx) => (
            <motion.div
              key={evt.id}
              initial={{ opacity: 0, x: -10, height: 0 }}
              animate={{ opacity: 1, x: 0, height: 'auto' }}
              className="flex items-start gap-2"
            >
              <div className="mt-0.5">
                {evt.type === 'COMPLETE' ? (
                  <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                ) : (
                  <Activity className="h-3 w-3 text-indigo-400 animate-pulse" />
                )}
              </div>
              <div className="flex-1">
                <p className={`${evt.type === 'COMPLETE' ? 'text-emerald-300 font-bold' : 'text-indigo-200'}`}>
                  {evt.message}
                </p>
                {evt.progress !== undefined && evt.type !== 'COMPLETE' && (
                  <div className="w-full h-1 bg-black/50 rounded-full mt-1.5 overflow-hidden">
                    <motion.div 
                      className="h-full bg-indigo-500"
                      initial={{ width: 0 }}
                      animate={{ width: `${evt.progress}%` }}
                      transition={{ duration: 0.5 }}
                    />
                  </div>
                )}
              </div>
              <span className="text-indigo-500/50 shrink-0">
                {new Date(evt.timestamp).toLocaleTimeString([], { hour12: false, second: '2-digit' })}
              </span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </GlassCard>
  );
}
