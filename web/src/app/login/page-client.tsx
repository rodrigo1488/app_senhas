"use client";

import { FormEvent, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Ticket } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ModeToggle } from "@/components/mode-toggle";
import { apiFetch, homeDoPapel, rotaAdminPermitida, type AdminUser } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const search = useSearchParams();
  const [email, setEmail] = useState("admin@compuflow.local");
  const [senha, setSenha] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await apiFetch<{ ok: boolean; user: AdminUser }>("/api/v1/admin/login", {
        method: "POST",
        body: JSON.stringify({ email, senha }),
      });
      const next = search.get("next") || "";
      const destino =
        next && rotaAdminPermitida(data.user.papel, next) ? next : homeDoPapel(data.user.papel);
      router.replace(destino);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha no login");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative flex min-h-svh items-center justify-center bg-background p-6">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_oklch(0.75_0.15_55_/_0.25),_transparent_55%),radial-gradient(ellipse_at_bottom_right,_oklch(0.65_0.2_41_/_0.18),_transparent_50%)] dark:bg-[radial-gradient(ellipse_at_top,_oklch(0.45_0.12_55_/_0.35),_transparent_55%),radial-gradient(ellipse_at_bottom_right,_oklch(0.4_0.14_41_/_0.25),_transparent_50%)]"
      />
      <div className="absolute right-4 top-4 z-10">
        <ModeToggle />
      </div>
      <Card className="relative w-full max-w-md shadow-xl">
        <CardHeader className="items-center text-center">
          <div className="mb-2 flex h-14 w-14 items-center justify-center rounded-full bg-primary text-primary-foreground">
            <Ticket className="h-7 w-7" />
          </div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-primary">CompuFlow</p>
          <CardTitle className="text-2xl">Painel Administrativo</CardTitle>
          <CardDescription>Entre com sua conta para gerenciar o sistema</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={onSubmit}>
            <div className="space-y-2">
              <Label htmlFor="email">E-mail</Label>
              <Input
                id="email"
                type="email"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="senha">Senha</Label>
              <Input
                id="senha"
                type="password"
                autoComplete="current-password"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                required
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Entrando..." : "Entrar"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
