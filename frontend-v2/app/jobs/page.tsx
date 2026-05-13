"use client";
import { StubPage } from "@/components/layout/StubPage";
import { Briefcase } from "lucide-react";

export default function JobsPage() {
  return (
    <StubPage
      title="Job Results"
      description="Full job search results with advanced filtering, match scoring, and skill overlap analysis."
      icon={Briefcase}
    />
  );
}
