import * as React from "react";

import { cn } from "@/lib/utils";

export function Badge({ className, ...props }: React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex h-5 items-center rounded-4xl border border-transparent bg-muted px-2 text-xs font-medium leading-none text-muted-foreground",
        className
      )}
      {...props}
    />
  );
}
