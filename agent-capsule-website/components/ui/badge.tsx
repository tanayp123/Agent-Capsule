import * as React from "react";

import { cn } from "@/lib/utils";

export function Badge({ className, ...props }: React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm border border-border bg-muted px-2.5 py-1 text-xs leading-4 text-muted-foreground",
        className
      )}
      {...props}
    />
  );
}
