"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { TrendingUp, TrendingDown, Target } from "lucide-react";

interface ATSScoreRingProps {
  score: number;
  confidence: number;
  trend?: "up" | "down" | "flat";
}

export function ATSScoreRing({ score, confidence, trend = "up" }: ATSScoreRingProps) {
  const [animatedScore, setAnimatedScore] = useState(0);
  
  // Animation for the score number itself
  useEffect(() => {
    let startTime: number;
    const duration = 1500;
    
    const animate = (time: number) => {
      if (!startTime) startTime = time;
      const progress = Math.min((time - startTime) / duration, 1);
      // easeOutCubic
      const easeProgress = 1 - Math.pow(1 - progress, 3);
      setAnimatedScore(Math.floor(easeProgress * score));
      
      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };
    
    requestAnimationFrame(animate);
  }, [score]);

  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  let colorClass = "text-red-500";
  let glowClass = "shadow-red-500/20";
  let strokeClass = "stroke-red-500";
  
  if (score >= 80) {
    colorClass = "text-emerald-400";
    glowClass = "shadow-emerald-500/20";
    strokeClass = "stroke-emerald-400";
  } else if (score >= 60) {
    colorClass = "text-teal-400";
    glowClass = "shadow-teal-500/20";
    strokeClass = "stroke-teal-400";
  } else if (score >= 40) {
    colorClass = "text-yellow-400";
    glowClass = "shadow-yellow-500/20";
    strokeClass = "stroke-yellow-400";
  }

  return (
    <div className="relative flex flex-col items-center justify-center p-6">
      <div className="relative w-48 h-48 flex items-center justify-center">
        {/* Background track */}
        <svg className="absolute inset-0 w-full h-full transform -rotate-90">
          <circle
            cx="96"
            cy="96"
            r={radius}
            className="stroke-surface-elevated"
            strokeWidth="8"
            fill="none"
          />
        </svg>

        {/* Animated Fill */}
        <svg className="absolute inset-0 w-full h-full transform -rotate-90 overflow-visible">
          <motion.circle
            cx="96"
            cy="96"
            r={radius}
            className={`${strokeClass} drop-shadow-[0_0_15px_rgba(var(--color-primary),0.3)]`}
            strokeWidth="8"
            fill="none"
            strokeLinecap="round"
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset }}
            transition={{ duration: 1.5, ease: "easeOut" }}
            style={{ strokeDasharray: circumference }}
          />
        </svg>

        {/* Inner Content */}
        <div className={`relative z-10 flex flex-col items-center justify-center w-32 h-32 rounded-full bg-surface/50 backdrop-blur-md border border-border/50 shadow-2xl ${glowClass}`}>
          <span className={`text-4xl font-bold tracking-tighter ${colorClass}`}>
            {animatedScore}
          </span>
          <span className="text-[10px] font-semibold text-muted-foreground tracking-widest uppercase mt-1">
            ATS Score
          </span>
        </div>

        {/* Floating Confidence Badge */}
        <motion.div 
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 1, type: "spring", stiffness: 200 }}
          className="absolute -bottom-2 bg-surface-elevated border border-border/50 px-3 py-1 rounded-full flex items-center gap-1.5 shadow-xl"
        >
          <Target className="h-3 w-3 text-teal-400" />
          <span className="text-[10px] font-bold text-foreground">{(confidence * 100).toFixed(0)}% Conf.</span>
        </motion.div>

        {/* Floating Trend Indicator */}
        <motion.div 
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 1.2, type: "spring", stiffness: 200 }}
          className="absolute -top-2 right-2 bg-surface-elevated border border-border/50 p-1.5 rounded-full shadow-xl"
        >
          {trend === "up" ? (
            <TrendingUp className="h-3 w-3 text-emerald-400" />
          ) : trend === "down" ? (
            <TrendingDown className="h-3 w-3 text-red-400" />
          ) : (
            <div className="h-3 w-3 rounded-full bg-yellow-400 opacity-50" />
          )}
        </motion.div>
      </div>
    </div>
  );
}
