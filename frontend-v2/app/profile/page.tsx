"use client";
import { StubPage } from "@/components/layout/StubPage";
import { User } from "lucide-react";

export default function ProfilePage() {
  return (
    <StubPage
      title="Profile Intelligence"
      description="Your strengths, weaknesses, skill graph, recommended growth areas, and behavioral insights."
      icon={User}
    />
  );
}
