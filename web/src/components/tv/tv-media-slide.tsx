"use client";

import { useEffect } from "react";
import { cn } from "@/lib/utils";
import type { TvPropagandaImagem } from "@/lib/tv-api";

type Props = {
  item: TvPropagandaImagem | null;
  url: string | null;
  intervaloMs: number;
  onComplete: () => void;
  loop?: boolean;
  className?: string;
  emptyLabel?: string;
};

export function TvMediaSlide({
  item,
  url,
  intervaloMs,
  onComplete,
  loop = false,
  className,
  emptyLabel = "Sem mídia de propaganda",
}: Props) {
  const isVideo = (item?.tipo || "image") === "video";

  useEffect(() => {
    if (!item || !url || isVideo || loop) return;
    const id = window.setTimeout(onComplete, Math.max(1000, intervaloMs));
    return () => window.clearTimeout(id);
  }, [item, url, isVideo, loop, intervaloMs, onComplete]);

  if (!url || !item) {
    return (
      <div className={cn("flex h-full items-center justify-center bg-zinc-950 text-white/40", className)}>
        {emptyLabel}
      </div>
    );
  }

  if (isVideo) {
    return (
      <video
        key={item.id}
        src={url}
        muted
        autoPlay
        playsInline
        loop={loop}
        controls={false}
        className={cn("h-full w-full object-cover", className)}
        onEnded={loop ? undefined : onComplete}
        onError={loop ? undefined : onComplete}
      />
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={url} alt="Propaganda" className={cn("h-full w-full object-cover", className)} />
  );
}
