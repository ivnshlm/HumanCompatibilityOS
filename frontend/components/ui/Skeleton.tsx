import { cn } from "./cn";

/** Calm pulsing placeholder bar. */
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-control bg-white/5", className)} />;
}

const WIDTHS = {
  "3xl": "max-w-3xl",
  "4xl": "max-w-4xl",
  "6xl": "max-w-6xl",
} as const;

/** Standard full-page loading skeleton (title + two card placeholders). */
export function PageSkeleton({ width = "3xl" }: { width?: keyof typeof WIDTHS }) {
  return (
    <main className={cn("mx-auto px-6 py-12", WIDTHS[width])}>
      <Skeleton className="h-4 w-28" />
      <Skeleton className="mt-3 h-8 w-56" />
      <Skeleton className="mt-3 h-4 w-80 max-w-full" />
      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
      </div>
    </main>
  );
}
