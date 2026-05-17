"use client";

import { forwardRef } from "react";
import { cn } from "@/lib/utils";

interface GlassInputProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  variant?: "default" | "large";
}

export const GlassInput = forwardRef<HTMLTextAreaElement, GlassInputProps>(
  ({ variant = "default", className, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={cn(
          "glass-input w-full resize-none rounded-xl px-4 py-3 text-foreground placeholder:text-muted-foreground focus:outline-none",
          variant === "default" && "text-sm",
          variant === "large" && "text-base leading-relaxed min-h-[120px]",
          className
        )}
        {...props}
      />
    );
  }
);

GlassInput.displayName = "GlassInput";
