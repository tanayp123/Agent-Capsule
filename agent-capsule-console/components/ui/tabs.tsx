"use client";

import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "@/lib/utils";

const Tabs = TabsPrimitive.Root;

function TabsList({ className, ...props }: TabsPrimitive.TabsListProps) {
  return (
    <TabsPrimitive.List
      className={cn("inline-flex h-9 items-center rounded-lg bg-card p-1 ring-1 ring-foreground/10", className)}
      {...props}
    />
  );
}

function TabsTrigger({ className, ...props }: TabsPrimitive.TabsTriggerProps) {
  return (
    <TabsPrimitive.Trigger
      className={cn(
        "inline-flex h-7 items-center justify-center rounded-md px-3 text-sm font-normal text-muted-foreground transition-colors data-[state=active]:bg-muted data-[state=active]:text-foreground",
        className
      )}
      {...props}
    />
  );
}

function TabsContent({ className, ...props }: TabsPrimitive.TabsContentProps) {
  return <TabsPrimitive.Content className={cn("mt-4", className)} {...props} />;
}

export { Tabs, TabsContent, TabsList, TabsTrigger };
