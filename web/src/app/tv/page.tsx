import { TvPanel } from "@/components/tv/tv-panel";

type Props = {
  searchParams: Promise<{ codigo?: string }>;
};

export default async function TvPage({ searchParams }: Props) {
  const params = await searchParams;
  return <TvPanel initialCodigo={params.codigo ?? null} />;
}
