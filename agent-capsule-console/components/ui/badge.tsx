import * as React from "react";
import { cn } from "@/lib/utils";

type BadgeTone = "neutral" | "green" | "amber" | "red" | "blue";

const tones: Record<BadgeTone, string> = {
  neutral: "border-transparent bg-muted text-muted-foreground",
  green: "border-transparent bg-success-soft text-success",
  amber: "border-transparent bg-warning-soft text-warning",
  red: "border-transparent bg-destructive/10 text-destructive",
  blue: "border-transparent bg-info-soft text-info"
};

export function Badge({
  className,
  tone = "neutral",
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { tone?: BadgeTone }) {
  return (
    <span
      className={cn(
        "inline-flex h-5 items-center rounded-4xl border px-2 text-xs font-medium leading-none",
        tones[tone],
        className
      )}
      {...props}
    />
  );
}
