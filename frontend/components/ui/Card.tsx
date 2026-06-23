import type { HTMLAttributes } from "react";

import { cn } from "./cn";

type CardProps = HTMLAttributes<HTMLDivElement> & {
  /** `inset` = nested surface (bars, chips, disclaimers). */
  variant?: "default" | "inset";
};

/** Surface container — the basic building block of every screen. */
export function Card({ variant = "default", className, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-card border p-5",
        variant === "default"
          ? "border-edge bg-surface"
          : "border-edge-2 bg-surface-2",
        className,
      )}
      {...props}
    />
  );
}
