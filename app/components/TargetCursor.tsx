"use client";

import { useEffect, useRef } from "react";

export default function TargetCursor() {
  const cursor = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const update = (event: MouseEvent) => {
      const element = (event.target as HTMLElement | null)?.closest<HTMLElement>("[data-cursor-target]");
      const node = cursor.current;
      if (!node) return;
      if (element) {
        const box = element.getBoundingClientRect();
        node.classList.add("target-cursor--active");
        node.style.width = `${box.width + 10}px`;
        node.style.height = `${box.height + 10}px`;
        node.style.transform = `translate(${box.left - 5}px, ${box.top - 5}px)`;
      } else {
        node.classList.remove("target-cursor--active");
        node.style.width = "16px";
        node.style.height = "16px";
        node.style.transform = `translate(${event.clientX - 8}px, ${event.clientY - 8}px)`;
      }
    };
    window.addEventListener("mousemove", update);
    return () => window.removeEventListener("mousemove", update);
  }, []);

  return <div className="target-cursor" ref={cursor} aria-hidden="true"><i /><b /><em /><strong /></div>;
}
