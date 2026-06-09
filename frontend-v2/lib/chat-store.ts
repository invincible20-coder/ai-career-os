"use client";

import { create } from "zustand";
import { recordIntent } from "./api";

export type MessageRole = "user" | "assistant" | "system";
export type IntentType = "exploring" | "uncertain" | "focused" | "desperate" | "confident" | "burnout" | "technical";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  isStreaming?: boolean;
  intent?: { type: IntentType; confidence: number; label: string };
  actions?: ChatAction[];
  memory?: string[];
  executionSteps?: ExecutionStep[];
}

export interface ChatAction {
  id: string;
  label: string;
  type: "apply" | "analyze" | "generate" | "improve" | "view";
  loading?: boolean;
}

export interface ExecutionStep {
  label: string;
  status: "pending" | "active" | "done";
}

interface ChatStore {
  messages: ChatMessage[];
  isStreaming: boolean;
  activeIntent: { type: IntentType; confidence: number; label: string } | null;
  sessionId: string;
  userId: string;
  addMessage: (msg: Omit<ChatMessage, "id" | "timestamp">) => void;
  updateLastAssistant: (content: string, done?: boolean) => void;
  setStreaming: (v: boolean) => void;
  setIntent: (intent: ChatStore["activeIntent"]) => void;
  simulateResponse: (userMessage: string) => void;
}

interface BackendIntent {
  career_clarity?: number;
  uncertainty?: number;
  exploration_mode?: boolean;
  urgency?: number;
  category_preference?: string;
}

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function detectIntent(text: string): { type: IntentType; confidence: number; label: string } {
  const l = text.toLowerCase();
  if (l.includes("don't know") || l.includes("confused")) return { type: "uncertain", confidence: 72, label: "Career State: Uncertain" };
  if (l.includes("burned out") || l.includes("hate")) return { type: "burnout", confidence: 65, label: "Mood: Burnout Detected" };
  if (l.includes("urgent") || l.includes("desperate")) return { type: "desperate", confidence: 78, label: "Urgency: High" };
  if (l.includes("backend") || l.includes("python") || l.includes("react")) return { type: "technical", confidence: 80, label: "Focus: Technical Role" };
  return { type: "exploring", confidence: 55, label: "Career State: Exploring" };
}

// Local fallback when backend is unavailable
function getFallbackResponse(msg: string) {
  const l = msg.toLowerCase();
  if (l.includes("backend") || l.includes("python")) {
    return {
      content: "Great choice! Based on your interest in backend engineering, I've identified several strong opportunities.\n\n## Analysis\n\n**Your Profile Signals:**\n- Strong backend orientation detected\n- Python/FastAPI ecosystem alignment\n\n**Recommended Focus Areas:**\n1. **Distributed Systems** — High demand, matches your profile\n2. **API Engineering** — Leverages your experience\n3. **Platform Engineering** — Growing field\n\n> Your backend applications show a **24% interview rate** — above average.\n\nWould you like me to search for specific roles?",
      actions: [
        { id: "1", label: "Search Backend Jobs", type: "view" as const },
        { id: "2", label: "Analyze Resume", type: "analyze" as const },
      ],
      memory: ["Backend interest noted", "Python skills detected"],
      executionSteps: [
        { label: "Analyzing career signals", status: "done" as const },
        { label: "Computing predictions", status: "done" as const },
      ],
    };
  }
  return {
    content: "I understand your situation. Let me help guide you.\n\n**What I've observed:**\n- You're in an exploration phase\n- This is completely normal\n\n**What I recommend:**\n1. Tell me about projects you've enjoyed\n2. Share what work energizes you\n3. Mention skills you want to grow\n\n*I'm here to understand you, not just find you a job.*",
    actions: [{ id: "1", label: "Explore Careers", type: "view" as const }],
    memory: ["Initial exploration"],
    executionSteps: [{ label: "Processing context", status: "done" as const }],
  };
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [{
    id: "welcome", role: "assistant",
    content: "Welcome to HuntAI. I'm your adaptive career intelligence system.\n\nUnlike a regular chatbot, I learn from every interaction.\n\n**Try telling me:**\n- What kind of work excites you\n- Where you feel stuck\n- What your ideal role looks like\n\nSpeak freely — confusion is data too.",
    timestamp: new Date().toISOString(), memory: ["Session initialized"],
  }],
  isStreaming: false,
  activeIntent: null,
  sessionId: `session-${uid()}`,
  userId: "demo-user",

  addMessage(msg) {
    set((s) => ({ messages: [...s.messages, { ...msg, id: uid(), timestamp: new Date().toISOString() }] }));
  },
  updateLastAssistant(content, done = false) {
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") msgs[msgs.length - 1] = { ...last, content, isStreaming: !done };
      return { messages: msgs, isStreaming: !done };
    });
  },
  setStreaming(v) { set({ isStreaming: v }); },
  setIntent(intent) { set({ activeIntent: intent }); },

  simulateResponse(userMessage: string) {
    const intent = detectIntent(userMessage);
    get().setIntent(intent);
    get().addMessage({ role: "user", content: userMessage, intent });
    set({ isStreaming: true });

    // Try to send the message to the real backend intent service
    const { sessionId, userId } = get();
    recordIntent({ message: userMessage, session_id: sessionId }, userId)
      .then((backendIntent) => {
        // Backend returned real intent data — use it
        if (backendIntent && typeof backendIntent === "object") {
          const bi = backendIntent as BackendIntent;
          const realIntent: ChatStore["activeIntent"] = {
            type: (bi.exploration_mode ? "exploring" : "focused") as IntentType,
            confidence: Math.round((bi.career_clarity ?? 0.5) * 100),
            label: bi.exploration_mode
              ? `Exploring (clarity: ${Math.round((bi.career_clarity ?? 0) * 100)}%)`
              : `Focused (clarity: ${Math.round((bi.career_clarity ?? 0) * 100)}%)`,
          };
          get().setIntent(realIntent);

          // Build a response from real backend signals
          const clarityPct = Math.round((bi.career_clarity ?? 0) * 100);
          const uncertaintyPct = Math.round((bi.uncertainty ?? 0) * 100);
          const content = `I've processed your input through the adaptive intelligence engine.\n\n## Analysis from Backend\n\n**Career Clarity:** ${clarityPct}%\n**Uncertainty:** ${uncertaintyPct}%\n**Exploration Mode:** ${bi.exploration_mode ? "Active" : "Inactive"}\n**Urgency:** ${Math.round((bi.urgency ?? 0) * 100)}%\n\n${bi.category_preference ? `**Detected Preference:** ${bi.category_preference}` : ""}\n\n> This data feeds into the adaptive ranking engine — future job recommendations will reflect these signals.\n\nTell me more about what excites you or what you're looking for.`;

          get().addMessage({
            role: "assistant",
            content: "",
            isStreaming: true,
            memory: [`Intent recorded: clarity ${clarityPct}%`, `Uncertainty: ${uncertaintyPct}%`],
            executionSteps: [
              { label: "Sent to backend intent engine", status: "done" },
              { label: "Career signals updated", status: "done" },
            ],
            actions: [
              { id: "1", label: "View Intelligence Profile", type: "view" },
              { id: "2", label: "Start Job Hunt", type: "apply" },
            ],
          });

          // Simulate streaming the response text
          let i = 0;
          const interval = setInterval(() => {
            i += Math.floor(Math.random() * 3) + 1;
            if (i >= content.length) {
              get().updateLastAssistant(content, true);
              clearInterval(interval);
            } else {
              get().updateLastAssistant(content.slice(0, i));
            }
          }, 18);
        } else {
          throw new Error("Empty backend response");
        }
      })
      .catch(() => {
        // Backend unavailable — fall back to local mock
        console.warn("[Chat] Backend intent service unavailable, using local fallback");
        const response = getFallbackResponse(userMessage);
        get().addMessage({
          role: "assistant",
          content: "",
          isStreaming: true,
          actions: response.actions,
          memory: [...(response.memory || []), "⚠ Backend offline — using local AI"],
          executionSteps: response.executionSteps,
        });
        let i = 0;
        const interval = setInterval(() => {
          i += Math.floor(Math.random() * 3) + 1;
          if (i >= response.content.length) {
            get().updateLastAssistant(response.content, true);
            clearInterval(interval);
          } else {
            get().updateLastAssistant(response.content.slice(0, i));
          }
        }, 18);
      });
  },
}));
