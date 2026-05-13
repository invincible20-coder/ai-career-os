"use client";

import { useEffect } from "react";
import { motion } from "framer-motion";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { HeroInput } from "@/components/dashboard/HeroInput";
import { QuickActions } from "@/components/dashboard/QuickActions";
import { PlanVisualization } from "@/components/dashboard/PlanVisualization";
import { ActivityStream } from "@/components/dashboard/ActivityStream";
import { MetricsBar, BehaviorStrip } from "@/components/dashboard/MetricsBar";
import { JobList } from "@/components/jobs/JobList";
import { ContentViewer } from "@/components/content/ContentViewer";
import { TrackerTable } from "@/components/tracking/TrackerTable";
import { RecommendationPanel } from "@/components/career/RecommendationPanel";
import { ErrorPanel } from "@/components/shared/ErrorPanel";
import { useHuntStore } from "@/lib/store";

export default function CommandCenterPage() {
  const checkHealth = useHuntStore((s) => s.checkHealth);
  const fetchAnalytics = useHuntStore((s) => s.fetchAnalytics);
  const huntId = useHuntStore((s) => s.huntId);
  const isPolling = useHuntStore((s) => s.isPolling);
  const refreshHunt = useHuntStore((s) => s.refreshHunt);
  const sidebarCollapsed = useHuntStore((s) => s.sidebarCollapsed);

  // Initial checks
  useEffect(() => {
    checkHealth();
    fetchAnalytics();
  }, [checkHealth, fetchAnalytics]);

  // Polling
  useEffect(() => {
    if (!huntId || !isPolling) return;
    const id = window.setInterval(() => refreshHunt(), 1800);
    return () => window.clearInterval(id);
  }, [huntId, isPolling, refreshHunt]);

  return (
    <div className="flex min-h-screen bg-[#0B1020]">
      <Sidebar />

      {/* Main content area */}
      <motion.main
        initial={false}
        animate={{ marginLeft: sidebarCollapsed ? 64 : 240 }}
        transition={{ duration: 0.2, ease: "easeInOut" }}
        className="flex-1 min-w-0"
      >
        <TopBar title="Command Center" />

        <div className="p-6 space-y-4 max-w-[1600px] mx-auto">
          {/* Row 1: Hero Input + Quick Actions */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <HeroInput />
            <div className="mt-3">
              <QuickActions />
            </div>
          </motion.div>

          {/* Row 2: Metrics */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.05 }}
          >
            <MetricsBar />
          </motion.div>

          {/* Row 3: Plan + Activity + Recommendations */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.1 }}
            className="grid grid-cols-1 lg:grid-cols-3 gap-4"
          >
            <PlanVisualization />
            <ActivityStream />
            <RecommendationPanel />
          </motion.div>

          {/* Row 4: Jobs + Content Viewer */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.15 }}
            className="grid grid-cols-1 lg:grid-cols-2 gap-4"
          >
            <JobList />
            <ContentViewer />
          </motion.div>

          {/* Row 5: Behavior + Tracker */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.2 }}
            className="space-y-4"
          >
            <BehaviorStrip />
            <TrackerTable />
          </motion.div>
        </div>
      </motion.main>

      {/* Error overlay */}
      <ErrorPanel />
    </div>
  );
}
