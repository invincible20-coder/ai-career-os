"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Terminal, Activity, CheckCircle2 } from "lucide-react";
import { GlassCard } from "@/components/glass/GlassCard";
import { getBackendBaseUrl } from "@/lib/api";

interface AIEvent {
  id: string;
  type: "START" | "PROGRESS" | "COMPLETE" | "FAILED" | "TIMEOUT";
  message: string;
  progress?: number;
  timestamp: string;
}

interface ResumeFeatureVector {
  ats_score: number;
  keyword_density: number;
  readability_score: number;
  action_verb_usage: number;
  technical_depth: number;
}

interface ResumeWeakness {
  weakness_id: string;
  category: string;
  severity: string;
  explanation: string;
  optimization_suggestion: string;
  expected_ats_impact: number;
}

export interface ResumeAnalysisResult {
  file_name: string;
  report: {
    fingerprint: {
      features: ResumeFeatureVector;
    };
    weaknesses: ResumeWeakness[];
    optimization_prediction: {
      confidence: number;
    };
  };
  timestamp: string;
}

interface ResumeStreamEnvelope {
  type?: string;
  timestamp?: string;
  payload?: {
    message?: string;
    progress?: number;
    data?: ResumeAnalysisResult;
  };
  message?: string;
  progress?: number;
  data?: ResumeAnalysisResult;
}

interface LiveAIActivityFeedProps {
  userId: string;
  onComplete: (data: ResumeAnalysisResult) => void;
}

export function LiveAIActivityFeed({ userId, onComplete }: LiveAIActivityFeedProps) {
  const [events, setEvents] = useState<AIEvent[]>([]);
  const [isListening, setIsListening] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const onCompleteRef = useRef(onComplete);

  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    if (!userId) return;

    const streamUrl = `${getBackendBaseUrl()}/api/v1/resume/stream/${encodeURIComponent(userId)}`;
    console.log("[SSE] Connecting to:", streamUrl);
    const eventSource = new EventSource(streamUrl);
    eventSourceRef.current = eventSource;

    // Map backend event types to frontend types
    const typeMap: Record<string, AIEvent["type"]> = {
      "resume_analysis_started": "START",
      "resume_analysis_progress": "PROGRESS",
      "resume_analysis_completed": "COMPLETE",
      "FAILED": "FAILED",
      "TIMEOUT": "TIMEOUT",
      "stream_connected": "START",
    };

    const handleEvent = (event: MessageEvent) => {
      console.log("[SSE] Event received:", event.type, event.data);
      try {
        const envelope = JSON.parse(event.data) as ResumeStreamEnvelope;
        const payload = envelope.payload || envelope;
        const eventType = envelope.type ?? event.type;
        const mappedType = typeMap[eventType] || "PROGRESS";

        const newEvent: AIEvent = {
          id: crypto.randomUUID(),
          type: mappedType,
          message: payload.message || "",
          progress: payload.progress,
          timestamp: envelope.timestamp || new Date().toISOString()
        };

        setEvents((prev) => [...prev, newEvent]);

        if (envelope.type === "resume_analysis_completed") {
          eventSource.close();
          eventSourceRef.current = null;
          setIsListening(false);
          if (payload.data) {
            onCompleteRef.current(payload.data);
          }
        }
      } catch (e) {
        console.error("[SSE] Parse error:", e);
      }
    };

    // Listen for named SSE events (backend sends "event: <type>\ndata: {...}\n\n")
    eventSource.addEventListener("stream_connected", handleEvent);
    eventSource.addEventListener("resume_analysis_started", handleEvent);
    eventSource.addEventListener("resume_analysis_progress", handleEvent);
    eventSource.addEventListener("resume_analysis_completed", handleEvent);
    eventSource.addEventListener("heartbeat", () => {
      console.log("[SSE] Heartbeat received");
    });

    eventSource.onopen = () => {
      console.log("[SSE] Connection opened, readyState:", eventSource.readyState);
      setIsListening(true);
    };

    eventSource.onerror = (error) => {
      console.error("[SSE] Error, readyState:", eventSource.readyState, error);
      // Only close if the connection is truly dead (CLOSED state = 2)
      if (eventSource.readyState === EventSource.CLOSED) {
        setIsListening(false);
        eventSourceRef.current = null;
      }
    };

    return () => {
      console.log("[SSE] Cleanup — closing connection");
      eventSourceRef.current?.close();
      eventSourceRef.current = null;
      setIsListening(false);
    };
  }, [userId]);

  return (
    <GlassCard className="p-4 bg-black/40 border-teal-500/20 backdrop-blur-3xl overflow-hidden relative">
      <div className="absolute inset-0 bg-gradient-to-b from-teal-500/5 to-transparent pointer-events-none"></div>
      
      <div className="flex items-center gap-2 mb-4 border-b border-border/50 pb-2">
        <Terminal className="h-4 w-4 text-teal-400" />
        <h3 className="text-xs font-mono font-semibold text-teal-300 tracking-wider">AI Execution Stream</h3>
        {isListening && (
          <span className="flex h-2 w-2 rounded-full bg-teal-500 ml-auto animate-pulse"></span>
        )}
      </div>

      <div className="space-y-3 font-mono text-[11px] max-h-[200px] overflow-y-auto scrollbar-thin">
        {events.length === 0 ? (
          <div className="flex items-center gap-2 text-indigo-200">
            <Activity className="h-3 w-3 text-teal-400 animate-pulse" />
            <span>Connecting to backend execution stream...</span>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {events.map((evt) => (
            <motion.div
              key={evt.id}
              initial={{ opacity: 0, x: -10, height: 0 }}
              animate={{ opacity: 1, x: 0, height: 'auto' }}
              className="flex items-start gap-2"
            >
              <div className="mt-0.5">
                {evt.type === 'COMPLETE' ? (
                  <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                ) : evt.type === 'FAILED' || evt.type === 'TIMEOUT' ? (
                  <Activity className="h-3 w-3 text-red-400" />
                ) : (
                  <Activity className="h-3 w-3 text-teal-400 animate-pulse" />
                )}
              </div>
              <div className="flex-1">
                <p className={`${evt.type === 'COMPLETE' ? 'text-emerald-300 font-bold' : 'text-indigo-200'}`}>
                  {evt.message}
                </p>
                {evt.progress !== undefined && evt.type !== 'COMPLETE' && (
                  <div className="w-full h-1 bg-black/50 rounded-full mt-1.5 overflow-hidden">
                    <motion.div 
                      className="h-full bg-teal-500"
                      initial={{ width: 0 }}
                      animate={{ width: `${evt.progress}%` }}
                      transition={{ duration: 0.5 }}
                    />
                  </div>
                )}
              </div>
              <span className="text-teal-500/50 shrink-0">
                {new Date(evt.timestamp).toLocaleTimeString([], { hour12: false, second: '2-digit' })}
              </span>
            </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>
    </GlassCard>
  );
}
