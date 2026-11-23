"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { Button, LinkButton } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ErrorNote } from "@/components/ui/feedback";
import { profileKeys } from "@/features/profiles/api";
import { isActive } from "@/lib/api/types";

import { jobKeys, useCreateJob, useJob } from "./api";
import { JobStatusBadge } from "./job-status-badge";
import { profileUrlSchema } from "./profile-url";

export function ScrapeForm() {
  const [url, setUrl] = useState("");
  const [force, setForce] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);

  const createJob = useCreateJob();
  const { data: job } = useJob(jobId);
  const queryClient = useQueryClient();
  const busy = createJob.isPending || (job ? isActive(job) : false);

  // When the tracked job settles, refresh the lists that depend on it.
  const settledStatus = job && !isActive(job) ? job.status : null;
  useEffect(() => {
    if (!settledStatus) return;
    void queryClient.invalidateQueries({ queryKey: jobKeys.list() });
    void queryClient.invalidateQueries({ queryKey: profileKeys.all });
  }, [settledStatus, queryClient]);

  function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    const parsed = profileUrlSchema.safeParse(url);
    if (!parsed.success) {
      setValidationError(parsed.error.issues[0].message);
      return;
    }
    setValidationError(null);
    createJob.mutate({ url: parsed.data, force }, { onSuccess: (created) => setJobId(created.id) });
  }

  const error = validationError ?? createJob.error?.message ?? null;

  return (
    <Card className="p-5 sm:p-6">
      <form onSubmit={onSubmit} noValidate>
        <label htmlFor="profile-url" className="text-sm font-medium">
          LinkedIn profile URL
        </label>
        <div className="mt-2 flex flex-col gap-3 sm:flex-row">
          <input
            id="profile-url"
            type="url"
            inputMode="url"
            autoComplete="off"
            spellCheck={false}
            placeholder="https://www.linkedin.com/in/name"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? "profile-url-error" : undefined}
            className="h-10 min-w-0 flex-1 rounded-lg border border-border bg-bg px-3 text-sm placeholder:text-muted aria-invalid:border-red-500"
          />
          <Button type="submit" loading={busy}>
            {busy ? "Working…" : "Scrape profile"}
          </Button>
        </div>
        <label className="mt-3 flex w-fit cursor-pointer items-center gap-2 text-sm text-muted">
          <input
            type="checkbox"
            checked={force}
            onChange={(event) => setForce(event.target.checked)}
            className="size-4 accent-(--accent)"
          />
          Re-scrape even if a recent copy is stored
        </label>
        {error && <ErrorNote message={error} className="mt-3" />}
      </form>

      {job && (
        <div
          aria-live="polite"
          className="mt-5 flex flex-wrap items-center gap-x-3 gap-y-2 border-t border-border pt-4 text-sm"
        >
          <JobStatusBadge status={job.status} />
          <span className="min-w-0 truncate font-mono text-xs text-muted">{job.public_id}</span>
          {job.from_cache && <span className="text-muted">Served from the stored copy</span>}
          {job.status === "succeeded" && job.profile_id && (
            <LinkButton href={`/profiles/${job.profile_id}`} variant="primary" className="ml-auto h-8">
              View profile
            </LinkButton>
          )}
          {job.error && !isActive(job) && <ErrorNote message={job.error} className="w-full" />}
          {job.status === "needs_attention" && (
            <p className="w-full text-muted">Fix the issue above, then submit the URL again.</p>
          )}
        </div>
      )}
    </Card>
  );
}
