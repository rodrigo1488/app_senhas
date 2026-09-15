import type { Metadata } from "next";
import { ForceLightTheme } from "@/components/tv/force-light-theme";

export const metadata: Metadata = {
  title: "Painel TV · CompuFlow",
  description: "Painel de chamadas para televisão via navegador",
};

export default function TvLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="light min-h-screen overflow-hidden bg-background text-foreground antialiased">
      <ForceLightTheme />
      {children}
    </div>
  );
}
