"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button, LinkButton } from "@/components/ui/button";
import { Card, CardSection } from "@/components/ui/card";
import { EmptyState, ErrorNote, Skeleton } from "@/components/ui/feedback";
import { useJob } from "@/features/scrape/api";
import { JobStatusBadge } from "@/features/scrape/job-status-badge";
import { ApiError } from "@/lib/api/client";
import { isActive } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";

import { profileKeys, useDeleteProfile, useProfile, useRefreshProfile } from "./api";
import {
  ActivitySection,
  ContactSection,
  EducationSection,
  ExperienceSection,
} from "./profile-sections";

export function ProfileView() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: profile, isPending, error } = useProfile(id);
  const refresh = useRefreshProfile(id);
  const remove = useDeleteProfile(id);
  const [refreshJobId, setRefreshJobId] = useState<string | null>(null);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const { data: refreshJob } = useJob(refreshJobId);
  const refreshing = refresh.isPending || (refreshJob ? isActive(refreshJob) : false);

  // Reload the profile once its refresh job finishes.
  const refreshStatus = refreshJob && !isActive(refreshJob) ? refreshJob.status : null;
  useEffect(() => {
    if (refreshStatus === "succeeded") {
      void queryClient.invalidateQueries({ queryKey: profileKeys.detail(id) });
    }
  }, [refreshStatus, id, queryClient]);

  if (isPending) return <ProfileSkeleton />;
  if (error) {
    return error instanceof ApiError && error.status === 404 ? (
      <EmptyState title="Profile not found" hint="It may have been deleted." />
    ) : (
      <ErrorNote message={error.message} />
    );
  }

  return (
    <div className="space-y-5">
      <Card className="p-5 sm:p-6">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-start">
          <Avatar name={profile.full_name} src={profile.photo_url} className="size-20 text-2xl" />
          <div className="min-w-0 flex-1">
            <h1 className="text-2xl font-semibold tracking-tight">
              {profile.full_name ?? profile.public_id}
            </h1>
            {profile.headline && <p className="mt-1">{profile.headline}</p>}
            {profile.location && <p className="mt-1 text-sm text-muted">{profile.location}</p>}
            <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted">
              <Badge>source: {profile.source_provider}</Badge>
              <span>Last scraped {formatDateTime(profile.last_scraped_at)}</span>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 sm:flex-col sm:items-stretch">
            <LinkButton href={profile.url} target="_blank" rel="noopener noreferrer">
              Open on LinkedIn
            </LinkButton>
            <Button
              variant="secondary"
              loading={refreshing}
              onClick={() => refresh.mutate(undefined, { onSuccess: (job) => setRefreshJobId(job.id) })}
            >
              {refreshing ? "Refreshing…" : "Refresh"}
            </Button>
            {confirmingDelete ? (
              <div className="flex gap-2">
                <Button
                  variant="danger"
                  loading={remove.isPending}
                  onClick={() => remove.mutate(undefined, { onSuccess: () => router.push("/profiles") })}
                >
                  Confirm delete
                </Button>
                <Button variant="ghost" onClick={() => setConfirmingDelete(false)}>
                  Cancel
                </Button>
              </div>
            ) : (
              <Button variant="danger" onClick={() => setConfirmingDelete(true)}>
                Delete
              </Button>
            )}
          </div>
        </div>

        {(refreshJob || refresh.error || remove.error) && (
          <div aria-live="polite" className="mt-4 space-y-2 border-t border-border pt-4 text-sm">
            {refreshJob && (
              <div className="flex items-center gap-2">
                <JobStatusBadge status={refreshJob.status} />
                <span className="text-muted">
                  {refreshJob.status === "succeeded" ? "Profile updated." : "Refresh job"}
                </span>
              </div>
            )}
            {refreshJob?.error && !isActive(refreshJob) && <ErrorNote message={refreshJob.error} />}
            {refresh.error && <ErrorNote message={refresh.error.message} />}
            {remove.error && <ErrorNote message={remove.error.message} />}
          </div>
        )}
      </Card>

      <div className="grid gap-5 lg:grid-cols-3">
        <div className="space-y-5 lg:col-span-2">
          {profile.about && (
            <CardSection title="About">
              <p className="text-sm whitespace-pre-line">{profile.about}</p>
            </CardSection>
          )}
          <ExperienceSection experiences={profile.experiences} />
          <EducationSection educations={profile.educations} />
        </div>
        <div className="space-y-5">
          <ContactSection contacts={profile.contacts} />
          <ActivitySection activities={profile.activities} />
        </div>
      </div>
    </div>
  );
}

export function ProfileSkeleton() {
  return (
    <div className="space-y-5">
      <Skeleton className="h-40" />
      <div className="grid gap-5 lg:grid-cols-3">
        <Skeleton className="h-72 lg:col-span-2" />
        <Skeleton className="h-72" />
      </div>
    </div>
  );
}
