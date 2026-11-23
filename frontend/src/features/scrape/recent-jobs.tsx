"use client";

import Link from "next/link";

import { Card } from "@/components/ui/card";
import { EmptyState, ErrorNote, Skeleton } from "@/components/ui/feedback";
import { formatRelative } from "@/lib/format";

import { useRecentJobs } from "./api";
import { JobStatusBadge } from "./job-status-badge";

export function RecentJobs() {
  const { data, isPending, error } = useRecentJobs();

  if (isPending) {
    return (
      <div className="space-y-2">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-14" />
        ))}
      </div>
    );
  }
  if (error) return <ErrorNote message={error.message} />;
  if (data.items.length === 0) {
    return <EmptyState title="No scrapes yet" hint="Submit a profile URL above to start." />;
  }

  return (
    <Card className="divide-y divide-border">
      {data.items.map((job) => (
        <div key={job.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3 text-sm">
          <JobStatusBadge status={job.status} />
          <span className="min-w-0 flex-1 truncate font-medium">{job.public_id}</span>
          <span className="text-xs text-muted">
            {job.provider}
            {job.from_cache ? " · cached" : ""} · {formatRelative(job.created_at)}
          </span>
          {job.profile_id && (
            <Link href={`/profiles/${job.profile_id}`} className="font-medium text-accent hover:underline">
              View
            </Link>
          )}
          {job.error && job.status !== "queued" && job.status !== "running" && (
            <p className="w-full text-xs text-muted">{job.error}</p>
          )}
        </div>
      ))}
    </Card>
  );
}
