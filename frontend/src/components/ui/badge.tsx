import { cn } from "@/lib/cn";

export type Tone = "neutral" | "info" | "success" | "danger" | "warning";

const tones: Record<Tone, string> = {
  neutral: "bg-surface-2 text-muted",
  info: "bg-accent-soft text-accent",
  success: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300",
  danger: "bg-red-100 text-red-800 dark:bg-red-950/60 dark:text-red-300",
  warning: "bg-amber-100 text-amber-900 dark:bg-amber-950/60 dark:text-amber-300",
};

export function Badge({
  tone = "neutral",
  className,
  children,
}: {
  tone?: Tone;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
