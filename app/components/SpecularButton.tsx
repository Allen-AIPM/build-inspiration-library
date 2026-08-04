"use client";

import { ButtonHTMLAttributes, CSSProperties, MouseEvent, ReactNode, useRef } from "react";

type SpecularButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { children: ReactNode; tint?: string };

export default function SpecularButton({ children, className = "", tint = "rgba(255,255,255,.08)", onMouseMove, style, ...props }: SpecularButtonProps) {
  const ref = useRef<HTMLButtonElement>(null);
  function move(event: MouseEvent<HTMLButtonElement>) {
    const box = event.currentTarget.getBoundingClientRect();
    event.currentTarget.style.setProperty("--shine-x", `${event.clientX - box.left}px`);
    event.currentTarget.style.setProperty("--shine-y", `${event.clientY - box.top}px`);
    onMouseMove?.(event);
  }
  return <button ref={ref} data-cursor-target className={`specular-button ${className}`} style={{ ...style, "--specular-tint": tint } as CSSProperties} onMouseMove={move} {...props}><span>{children}</span></button>;
}
