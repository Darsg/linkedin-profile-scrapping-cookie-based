import { cn } from "@/lib/cn";
import { initials } from "@/lib/format";

export function Avatar({
  name,
  src,
  className,
}: {
  name: string | null;
  src: string | null;
  className?: string;
}) {
  const shared = cn("shrink-0 rounded-full", className ?? "size-10 text-sm");
  if (src) {
    // Remote profile photos come from arbitrary CDNs, so next/image is not configured for them.
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={src} alt="" referrerPolicy="no-referrer" className={cn(shared, "object-cover")} />;
  }
  return (
    <span
      aria-hidden
      className={cn(shared, "grid place-items-center bg-accent-soft font-semibold text-accent")}
    >
      {initials(name)}
    </span>
  );
}
