import type { ReactNode } from "react";

import { cn } from "./cn";

/**
 * Permanent ethical disclaimer surface. By doctrine it must stay visible on
 * every individual-result screen — do not hide or collapse it.
 */
export function Disclaimer({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "flex gap-2.5 rounded-card border border-edge-2 bg-surface-2 px-4 py-3 text-xs leading-relaxed text-ink-muted",
        className,
      )}
    >
      <span
        aria-hidden
        className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-ink-faint text-[10px] text-ink-faint"
      >
        i
      </span>
      <p>{children}</p>
    </div>
  );
}
