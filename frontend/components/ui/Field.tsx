import {
  forwardRef,
  type InputHTMLAttributes,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
  type ReactNode,
} from "react";

import { cn } from "./cn";

const CONTROL =
  "w-full rounded-control border border-edge bg-surface-2 px-3 py-2 text-sm text-ink " +
  "outline-none transition-colors placeholder:text-ink-faint focus:border-white/30";

/** Optional label wrapper around a control. */
export function Field({ label, children }: { label?: ReactNode; children: ReactNode }) {
  return (
    <label className="block">
      {label && <span className="text-sm text-ink-muted">{label}</span>}
      <span className={label ? "mt-1 block" : "block"}>{children}</span>
    </label>
  );
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return <input ref={ref} className={cn(CONTROL, className)} {...props} />;
  },
);

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement>
>(function Textarea({ className, ...props }, ref) {
  return <textarea ref={ref} className={cn(CONTROL, className)} {...props} />;
});

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className, ...props }, ref) {
    return <select ref={ref} className={cn(CONTROL, className)} {...props} />;
  },
);
