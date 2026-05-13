"use client";
import { StubPage } from "@/components/layout/StubPage";
import { FileText } from "lucide-react";

export default function ApplicationsPage() {
  return (
    <StubPage
      title="Applications"
      description="Pipeline view of all applications across hunts — saved, applied, interviewing, offer, rejected."
      icon={FileText}
    />
  );
}
