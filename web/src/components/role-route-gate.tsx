"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { homeDoPapel, rotaAdminPermitida } from "@/lib/api";

export function RoleRouteGate({
  papel,
  children,
}: {
  papel: string;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const permitido = rotaAdminPermitida(papel, pathname);

  useEffect(() => {
    if (!permitido) {
      router.replace(homeDoPapel(papel));
    }
  }, [papel, permitido, router]);

  if (!permitido) return null;
  return children;
}
