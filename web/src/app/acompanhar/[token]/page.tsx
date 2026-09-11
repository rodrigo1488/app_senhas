import type { Metadata } from "next";
import { TicketTracker } from "@/components/cliente/ticket-tracker";

export const metadata: Metadata = {
  title: "Acompanhar senha · AppSenhas",
  description: "Acompanhe sua senha e receba notificações",
};

type Props = { params: Promise<{ token: string }> };

export default async function AcompanharPage({ params }: Props) {
  const { token } = await params;
  return <TicketTracker token={token} />;
}
