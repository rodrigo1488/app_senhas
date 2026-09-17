"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Activity,
  Building2,
  FileText,
  Grid3x3,
  ImageIcon,
  LayoutDashboard,
  LogOut,
  Printer,
  Settings,
  Ticket,
  UserCog,
  Users,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { apiFetch, rotuloPapel, type AdminUser, type PapelPainel } from "@/lib/api";
import { cn } from "@/lib/utils";

const NAV_BASE: {
  href: string;
  label: string;
  icon: typeof LayoutDashboard;
  papeis: PapelPainel[];
}[] = [
  { href: "/admin", label: "Dashboard", icon: LayoutDashboard, papeis: ["admin", "gerente"] },
  { href: "/admin/relatorios", label: "Relatórios", icon: FileText, papeis: ["admin", "gerente"] },
  { href: "/admin/heatmap", label: "Mapa de calor", icon: Grid3x3, papeis: ["admin", "gerente"] },
  { href: "/admin/fila-ao-vivo", label: "Fila ao Vivo", icon: Activity, papeis: ["admin", "gerente"] },
  { href: "/admin/operadores", label: "Operadores", icon: Users, papeis: ["admin", "gerente"] },
  { href: "/admin/setores", label: "Setores", icon: Building2, papeis: ["admin", "gerente"] },
  { href: "/admin/propagandas", label: "Mídias", icon: ImageIcon, papeis: ["admin", "marketing"] },
  { href: "/admin/impressoras", label: "Impressoras", icon: Printer, papeis: ["admin", "gerente"] },
  { href: "/admin/usuarios", label: "Usuários", icon: UserCog, papeis: ["admin"] },
  { href: "/admin/configuracoes", label: "Configurações", icon: Settings, papeis: ["admin"] },
];

export function AppSidebar({
  nomeEmpresa,
  user,
}: {
  nomeEmpresa?: string;
  user?: AdminUser | null;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { open } = useSidebar();
  const papel: PapelPainel = user?.papel === "marketing" || user?.papel === "gerente" ? user.papel : "admin";
  const nav = NAV_BASE.filter((item) => item.papeis.includes(papel));

  async function logout() {
    try {
      await apiFetch("/api/v1/admin/logout", { method: "POST" });
    } catch {
      /* ignore */
    }
    router.replace("/login");
    router.refresh();
  }

  return (
    <Sidebar>
      <SidebarHeader>
        <div className={cn("flex items-center gap-3", !open && "justify-center")}>
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <Ticket className="h-5 w-5" />
          </div>
          {open && (
            <div className="min-w-0">
              <p className="truncate text-sm font-bold">CompuFlow</p>
              <p className="truncate text-xs text-muted-foreground">
                {nomeEmpresa || "Painel admin"}
              </p>
              {user?.papel ? (
                <p className="truncate text-[11px] text-muted-foreground">
                  {rotuloPapel(user.papel)}
                </p>
              ) : null}
            </div>
          )}
        </div>
      </SidebarHeader>
      <Separator />
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Menu</SidebarGroupLabel>
          <SidebarMenu>
            {nav.map((item) => {
              const active =
                item.href === "/admin"
                  ? pathname === "/admin"
                  : pathname.startsWith(item.href);
              const Icon = item.icon;
              return (
                <SidebarMenuItem key={item.href}>
                  <Link
                    href={item.href}
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                      active && "bg-sidebar-accent text-sidebar-accent-foreground",
                      !open && "justify-center px-2",
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    {open && <span>{item.label}</span>}
                  </Link>
                </SidebarMenuItem>
              );
            })}
          </SidebarMenu>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <Button variant="outline" className="w-full justify-start gap-2" onClick={logout}>
          <LogOut className="h-4 w-4" />
          {open && "Sair"}
        </Button>
      </SidebarFooter>
    </Sidebar>
  );
}
