"use client";
import { StubPage } from "@/components/layout/StubPage";
import { Lightbulb } from "lucide-react";

export default function WorkspacePage() {
  return (
    <StubPage
      title="Workspace"
      description="Resume and cover letter workspace with version switching, AI explanations, and diff view."
      icon={Lightbulb}
    />
  );
}
