import { cn } from "@/lib/cn";

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("rounded-xl border border-border bg-surface", className)} {...props} />
  );
}

export function CardSection({
  title,
  count,
  children,
}: {
  title: string;
  count?: number;
  children: React.ReactNode;
}) {
  return (
    <Card className="p-5 sm:p-6">
      <h2 className="mb-4 flex items-baseline gap-2 text-base font-semibold">
        {title}
        {count !== undefined && <span className="text-sm font-normal text-muted">{count}</span>}
      </h2>
      {children}
    </Card>
  );
}
