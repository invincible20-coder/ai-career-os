"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
import { motion } from "framer-motion";
import { GlassCard } from "@/components/glass/GlassCard";
import { Mail, Hexagon, Fingerprint, Lock, ShieldCheck } from "lucide-react";

const Github = (props: React.SVGProps<SVGSVGElement>) => (
  <svg
    {...props}
    xmlns="http://www.w3.org/2000/svg"
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
    <path d="M9 18c-4.51 2-5-2-7-2" />
  </svg>
);

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    await signIn("credentials", { email, password, callbackUrl: "/" });
    setIsLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden bg-background">
      {/* Background Mesh */}
      <div className="absolute inset-0 z-0 gradient-mesh opacity-60"></div>
      
      {/* Central Identity Form */}
      <motion.div 
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        className="w-full max-w-md z-10"
      >
        <div className="text-center mb-8">
          <motion.div 
            className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500/20 to-violet-500/20 mb-4 animate-pulse-glow"
            initial={{ rotate: -15 }}
            animate={{ rotate: 0 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
          >
            <Hexagon className="h-8 w-8 text-indigo-400 animate-orb-breathe" />
          </motion.div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Identity Protocol</h1>
          <p className="text-muted-foreground mt-2 text-sm">Synchronize your professional state</p>
        </div>

        <GlassCard className="p-8 backdrop-blur-2xl bg-surface-elevated border-border/50">
          <form onSubmit={handleEmailLogin} className="space-y-4">
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground pl-1 uppercase tracking-wider">Secure Email</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-muted-foreground">
                  <Mail className="h-4 w-4" />
                </div>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-background/50 border border-border/50 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all text-foreground placeholder:text-muted-foreground/50 glass-input"
                  placeholder="name@example.com"
                  required
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground pl-1 uppercase tracking-wider">Access Token</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-muted-foreground">
                  <Lock className="h-4 w-4" />
                </div>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-background/50 border border-border/50 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all text-foreground placeholder:text-muted-foreground/50 glass-input"
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 px-4 bg-gradient-to-r from-indigo-500 to-violet-500 hover:from-indigo-600 hover:to-violet-600 text-white rounded-xl text-sm font-semibold shadow-lg shadow-indigo-500/25 transition-all flex justify-center items-center gap-2 group relative overflow-hidden"
            >
              <span className="relative z-10">{isLoading ? "Synchronizing..." : "Initialize Session"}</span>
              {!isLoading && <Fingerprint className="h-4 w-4 opacity-70 group-hover:opacity-100 transition-opacity relative z-10" />}
              <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300 ease-out"></div>
            </button>
          </form>

          <div className="my-6 flex items-center">
            <div className="flex-grow border-t border-border/50"></div>
            <span className="mx-4 text-xs text-muted-foreground uppercase tracking-wider">External Identity</span>
            <div className="flex-grow border-t border-border/50"></div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <ProviderButton 
              name="Google" 
              icon={<ShieldCheck className="h-4 w-4" />} 
              onClick={() => signIn("google")} 
              glowColor="group-hover:shadow-red-500/20"
            />
            <ProviderButton 
              name="GitHub" 
              icon={<Github className="h-4 w-4" />} 
              onClick={() => signIn("github")} 
              glowColor="group-hover:shadow-gray-500/20"
            />
            <ProviderButton 
              name="Apple" 
              icon={<ShieldCheck className="h-4 w-4" />} 
              onClick={() => signIn("apple")} 
              glowColor="group-hover:shadow-gray-500/20"
            />
            <ProviderButton 
              name="LinkedIn" 
              icon={<ShieldCheck className="h-4 w-4" />} 
              onClick={() => signIn("linkedin")} 
              glowColor="group-hover:shadow-blue-500/20"
            />
            <ProviderButton 
              name="Microsoft" 
              icon={<ShieldCheck className="h-4 w-4" />} 
              onClick={() => signIn("azure-ad")} 
              glowColor="group-hover:shadow-blue-500/20"
            />
            <ProviderButton 
              name="Discord" 
              icon={<ShieldCheck className="h-4 w-4" />} 
              onClick={() => signIn("discord")} 
              glowColor="group-hover:shadow-indigo-500/20"
            />
          </div>
        </GlassCard>
        
        <p className="text-center text-xs text-muted-foreground mt-6">
          By initializing a session, you confirm connection to the autonomous AI network.
        </p>
      </motion.div>
    </div>
  );
}

function ProviderButton({ name, icon, onClick, glowColor }: { name: string, icon: React.ReactNode, onClick: () => void, glowColor: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`group flex items-center justify-center gap-2 w-full py-2.5 px-4 bg-background/50 hover:bg-background/80 border border-border/50 rounded-xl text-sm font-medium transition-all duration-300 hover:border-border ${glowColor} hover:shadow-lg`}
    >
      <span className="text-muted-foreground group-hover:text-foreground transition-colors">{icon}</span>
      <span className="text-muted-foreground group-hover:text-foreground transition-colors">{name}</span>
    </button>
  );
}
