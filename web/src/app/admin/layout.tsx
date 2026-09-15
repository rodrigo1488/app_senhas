import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import { Separator } from "@/components/ui/separator";
import { ModeToggle } from "@/components/mode-toggle";
import type { AdminUser } from "@/lib/api";

async function fetchMe(): Promise<AdminUser | null> {
  const cookieStore = await cookies();
  const cookieHeader = cookieStore
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");
  const base = process.env.API_INTERNAL_URL || "http://127.0.0.1:5000";
  try {
    const res = await fetch(`${base}/api/v1/admin/me`, {
      headers: { Cookie: cookieHeader },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return (await res.json()) as AdminUser;
  } catch {
    return null;
  }
}

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const me = await fetchMe();
  if (!me) {
    redirect("/login");
  }

  return (
    <SidebarProvider>
      <AppSidebar nomeEmpresa={me.nome_empresa} user={me} />
      <SidebarInset>
        <header className="sticky top-0 z-10 flex h-14 items-center gap-3 border-b bg-card/80 px-4 backdrop-blur">
          <SidebarTrigger />
          <Separator orientation="vertical" className="h-6" />
          <div className="flex flex-1 items-center justify-between gap-3">
            <p className="text-sm font-medium text-muted-foreground">
              {me.papel === "gerente" ? "Painel do gerente" : "Administração"}
            </p>
            <div className="flex items-center gap-1">
              <p className="hidden text-sm text-muted-foreground sm:block">{me.email}</p>
              <ModeToggle />
            </div>
          </div>
        </header>
        <div className="flex-1 p-6">{children}</div>
      </SidebarInset>
    </SidebarProvider>
  );
}
