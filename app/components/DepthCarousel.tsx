"use client";

import { useEffect, useState } from "react";

type CarouselItem = { image: string; alt?: string };
type DepthCarouselProps = { items: CarouselItem[]; onItemClick?: (index: number) => void };

export default function DepthCarousel({ items, onItemClick }: DepthCarouselProps) {
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(false);
  const count = items.length;
  const next = () => setActive((index) => count ? (index + 1) % count : 0);
  const previous = () => setActive((index) => count ? (index - 1 + count) % count : 0);

  useEffect(() => {
    if (paused || count < 2) return;
    const timer = window.setInterval(next, 3200);
    return () => window.clearInterval(timer);
  }, [paused, count]);

  return <div className="depth-carousel" role="region" aria-label="建筑灵感纵深轮播" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}>
    <div className="depth-carousel__stage">{items.map((item, index) => {
      const depth = (index - active + count) % count;
      const visible = depth < Math.min(4, count);
      return <button data-cursor-target className="depth-carousel__card" key={item.image} aria-label={`查看 ${item.alt || "建筑灵感"}`} style={{ "--depth": depth, opacity: visible ? 1 - depth * .2 : 0, pointerEvents: visible ? "auto" : "none" }} onClick={() => depth === 0 ? onItemClick?.(index) : setActive(index)}><img src={item.image} alt="" draggable={false} /></button>;
    })}</div>
    {count > 1 && <><button data-cursor-target className="depth-carousel__arrow depth-carousel__arrow--prev" aria-label="上一张" onClick={previous}>←</button><button data-cursor-target className="depth-carousel__arrow depth-carousel__arrow--next" aria-label="下一张" onClick={next}>→</button><div className="depth-carousel__dots">{items.slice(0, Math.min(count, 6)).map((_, index) => <button data-cursor-target key={index} className={index === active % Math.min(count, 6) ? "is-active" : ""} aria-label={`切换至第 ${index + 1} 张`} onClick={() => setActive(index)} />)}</div></>}
  </div>;
}
