"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import { UploadCloud, File, X, ShieldAlert } from "lucide-react";
import { GlassCard } from "@/components/glass/GlassCard";

interface ResumeUploadZoneProps {
  onUploadStart: (userId: string, fileName: string) => void;
  userId: string;
}

export function ResumeUploadZone({ onUploadStart, userId }: ResumeUploadZoneProps) {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setError(null);
    if (acceptedFiles.length > 0) {
      const selectedFile = acceptedFiles[0];
      if (selectedFile.size > 5 * 1024 * 1024) {
        setError("File size exceeds 5MB limit.");
        return;
      }
      setFile(selectedFile);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
    },
    maxFiles: 1
  });

  const handleUpload = async () => {
    if (!file) return;

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/resume/upload`, {
        method: 'POST',
        headers: {
          'x-user-id': userId
        },
        body: formData
      });

      if (!response.ok) throw new Error("Upload failed");
      
      onUploadStart(userId, file.name);
    } catch (err) {
      setError("Failed to initialize intelligence analysis.");
    }
  };

  return (
    <div className="w-full">
      <AnimatePresence>
        {error && (
          <motion.div 
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-2 text-red-400 text-sm"
          >
            <ShieldAlert className="h-4 w-4" />
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      {!file ? (
        <div 
          {...getRootProps()} 
          className={`
            relative overflow-hidden rounded-2xl border-2 border-dashed transition-all duration-300 ease-out
            ${isDragActive ? 'border-indigo-500 bg-indigo-500/5 shadow-[0_0_30px_-5px_rgba(129,140,248,0.2)]' : 'border-border hover:border-indigo-500/50 hover:bg-surface'}
          `}
        >
          <input {...getInputProps()} />
          <div className="p-10 text-center flex flex-col items-center justify-center">
            <motion.div
              animate={{ y: isDragActive ? -5 : 0, scale: isDragActive ? 1.1 : 1 }}
              className={`h-16 w-16 rounded-2xl flex items-center justify-center mb-4 transition-colors ${isDragActive ? 'bg-indigo-500/20 text-indigo-400' : 'bg-surface-elevated text-muted-foreground'}`}
            >
              <UploadCloud className="h-8 w-8" />
            </motion.div>
            <h3 className="text-lg font-semibold text-foreground tracking-tight">
              {isDragActive ? "Initialize Data Transfer" : "Drop Profile Data"}
            </h3>
            <p className="text-sm text-muted-foreground mt-2 max-w-sm mx-auto">
              Drag & drop your resume (PDF or DOCX) here to begin adaptive analysis. Maximum size 5MB.
            </p>
          </div>
        </div>
      ) : (
        <GlassCard className="p-6 relative overflow-hidden">
          <div className="flex items-center gap-4 relative z-10">
            <div className="h-12 w-12 bg-indigo-500/10 rounded-xl flex items-center justify-center shrink-0">
              <File className="h-6 w-6 text-indigo-400" />
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-semibold text-foreground truncate">{file.name}</h4>
              <p className="text-xs text-muted-foreground mt-0.5">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
            </div>
            <button 
              onClick={() => setFile(null)}
              className="p-2 hover:bg-surface rounded-lg transition-colors text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          
          <div className="mt-6">
            <button
              onClick={handleUpload}
              className="w-full py-3 px-4 bg-indigo-500 hover:bg-indigo-600 text-white rounded-xl text-sm font-semibold transition-all shadow-[0_0_20px_-5px_rgba(129,140,248,0.4)] hover:shadow-[0_0_30px_-5px_rgba(129,140,248,0.6)]"
            >
              Begin Intelligence Analysis
            </button>
          </div>
        </GlassCard>
      )}
    </div>
  );
}
