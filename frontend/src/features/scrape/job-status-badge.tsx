import { Badge, type Tone } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/button";
import type { JobStatus } from "@/lib/api/types";

const STATUS: Record<JobStatus, { label: string; tone: Tone; busy?: boolean }> = {
  queued: { label: "Queued", tone: "neutral", busy: true },
  running: { label: "Scraping", tone: "info", busy: true },
  succeeded: { label: "Done", tone: "success" },
  failed: { label: "Failed", tone: "danger" },
  needs_attention: { label: "Needs attention", tone: "warning" },
};

export function JobStatusBadge({ status }: { status: JobStatus }) {
  const { label, tone, busy } = STATUS[status];
  return (
    <Badge tone={tone}>
      {busy && <Spinner className="size-3 border-[1.5px]" />}
      {label}
    </Badge>
  );
}
