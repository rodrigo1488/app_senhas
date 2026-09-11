"use client";

import * as React from "react";
import { createContext, useContext, useMemo, useState } from "react";
import { PanelLeft } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

type SidebarContextValue = {
  open: boolean;
  setOpen: (v: boolean) => void;
  toggle: () => void;
};

const SidebarContext = createContext<SidebarContextValue | null>(null);

export function useSidebar() {
  const ctx = useContext(SidebarContext);
  if (!ctx) throw new Error("useSidebar must be used within SidebarProvider");
  return ctx;
}

export function SidebarProvider({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(true);
  const value = useMemo(
    () => ({ open, setOpen, toggle: () => setOpen((o) => !o) }),
    [open],
  );
  return (
    <SidebarContext.Provider value={value}>
      <div className="flex min-h-svh w-full bg-background">{children}</div>
    </SidebarContext.Provider>
  );
}

export function Sidebar({ children, className }: { children: React.ReactNode; className?: string }) {
  const { open } = useSidebar();
  return (
    <aside
      className={cn(
        "sticky top-0 z-20 hidden h-svh shrink-0 border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-[width] md:flex md:flex-col",
        open ? "w-64" : "w-[4.5rem]",
        className,
      )}
    >
      {children}
    </aside>
  );
}

export function SidebarHeader({ className, ...props }: React.ComponentProps<"div">) {
  return <div className={cn("flex flex-col gap-2 p-4", className)} {...props} />;
}

export function SidebarContent({ className, ...props }: React.ComponentProps<"div">) {
  return <div className={cn("flex-1 overflow-y-auto px-2 py-2", className)} {...props} />;
}

export function SidebarFooter({ className, ...props }: React.ComponentProps<"div">) {
  return <div className={cn("mt-auto border-t border-sidebar-border p-3", className)} {...props} />;
}

export function SidebarGroup({ className, ...props }: React.ComponentProps<"div">) {
  return <div className={cn("mb-4 flex flex-col gap-1", className)} {...props} />;
}

export function SidebarGroupLabel({ className, ...props }: React.ComponentProps<"div">) {
  const { open } = useSidebar();
  if (!open) return null;
  return (
    <div className={cn("px-2 py-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground", className)} {...props} />
  );
}

export function SidebarMenu({ className, ...props }: React.ComponentProps<"ul">) {
  return <ul className={cn("flex flex-col gap-1", className)} {...props} />;
}

export function SidebarMenuItem({ className, ...props }: React.ComponentProps<"li">) {
  return <li className={cn("relative", className)} {...props} />;
}

export function SidebarMenuButton({
  className,
  isActive,
  children,
  ...props
}: React.ComponentProps<"a"> & { isActive?: boolean }) {
  const { open } = useSidebar();
  return (
    <a
      className={cn(
        "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
        isActive && "bg-sidebar-accent text-sidebar-accent-foreground",
        !open && "justify-center px-2",
        className,
      )}
      {...props}
    >
      {children}
    </a>
  );
}

export function SidebarInset({ className, ...props }: React.ComponentProps<"main">) {
  return <main className={cn("flex min-h-svh flex-1 flex-col", className)} {...props} />;
}

export function SidebarTrigger({ className }: { className?: string }) {
  const { toggle } = useSidebar();
  return (
    <Button variant="ghost" size="icon" className={className} onClick={toggle} aria-label="Alternar menu">
      <PanelLeft className="h-5 w-5" />
    </Button>
  );
}
