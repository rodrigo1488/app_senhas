"use client";

import { useCallback, useMemo, useState } from "react";
import { TvMediaSlide } from "@/components/tv/tv-media-slide";
import type { ClienteConfig } from "@/lib/cliente-socket";
import { uploadsUrl } from "@/lib/tv-api";

type Props = {
  config: ClienteConfig | null;
};

export function ClienteEsperaSlideshow({ config }: Props) {
  const imagens = config?.imagens ?? [];
  const [index, setIndex] = useState(0);
  const atual = imagens[imagens.length ? index % imagens.length : 0] ?? null;
  const url = useMemo(() => uploadsUrl(atual?.arquivo), [atual?.arquivo]);
  const intervaloMs = Math.max(1000, config?.intervalo_ms ?? 15_000);

  const onComplete = useCallback(() => {
    if (imagens.length <= 1) return;
    setIndex((current) => (current + 1) % imagens.length);
  }, [imagens.length]);

  if (!imagens.length || !atual) return null;

  return (
    <div className="w-full overflow-hidden rounded-2xl border bg-black shadow-sm">
      <div className="aspect-video w-full">
        <TvMediaSlide
          item={{
            id: atual.id,
            arquivo: atual.arquivo,
            ordem: atual.ordem,
            tipo: atual.tipo,
          }}
          url={url}
          intervaloMs={intervaloMs}
          onComplete={onComplete}
          loop={imagens.length <= 1}
          emptyLabel=""
        />
      </div>
    </div>
  );
}
