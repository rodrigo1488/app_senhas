"use client";

import { useEffect, useRef } from "react";
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
  const itemId = item?.id ?? null;
  const arquivo = item?.arquivo ?? null;
  const onCompleteRef = useRef(onComplete);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const advancingRef = useRef(false);
  onCompleteRef.current = onComplete;

  useEffect(() => {
    advancingRef.current = false;
  }, [itemId, arquivo, url]);

  useEffect(() => {
    if (itemId == null || !url || isVideo || loop) return;
    const id = window.setTimeout(() => {
      if (advancingRef.current) return;
      advancingRef.current = true;
      onCompleteRef.current();
    }, Math.max(1000, intervaloMs));
    return () => window.clearTimeout(id);
  }, [itemId, arquivo, url, isVideo, loop, intervaloMs]);

  useEffect(() => {
    if (!isVideo || loop || !url || itemId == null) return;
    const video = videoRef.current;
    if (!video) return;
    let timeoutId = 0;
    const arm = () => {
      window.clearTimeout(timeoutId);
      const durationMs =
        Number.isFinite(video.duration) && video.duration > 0
          ? video.duration * 1000 + 2_500
          : 180_000;
      timeoutId = window.setTimeout(() => {
        if (advancingRef.current) return;
        advancingRef.current = true;
        onCompleteRef.current();
      }, durationMs);
    };
    video.addEventListener("loadedmetadata", arm);
    arm();
    return () => {
      video.removeEventListener("loadedmetadata", arm);
      window.clearTimeout(timeoutId);
    };
  }, [isVideo, loop, url, itemId]);

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
        ref={videoRef}
        key={item.id}
        src={url}
        muted
        autoPlay
        playsInline
        loop={loop}
        controls={false}
        className={cn("h-full w-full object-cover", className)}
        onEnded={loop ? undefined : () => {
          if (advancingRef.current) return;
          advancingRef.current = true;
          onCompleteRef.current();
        }}
        onError={loop ? undefined : () => {
          if (advancingRef.current) return;
          advancingRef.current = true;
          onCompleteRef.current();
        }}
      />
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={url} alt="Propaganda" className={cn("h-full w-full object-cover", className)} />
  );
}
