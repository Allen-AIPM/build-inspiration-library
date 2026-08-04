"use client";

type SplitTextProps = { text: string; className?: string; delay?: number; };

export default function SplitText({ text, className = "", delay = 55 }: SplitTextProps) {
  return (
    <span className={`split-text ${className}`} aria-label={text}>
      {Array.from(text).map((character, index) => (
        <span className="split-text__char" aria-hidden="true" key={`${character}-${index}`} style={{ animationDelay: `${index * delay}ms` }}>
          {character === " " ? "\u00a0" : character}
        </span>
      ))}
    </span>
  );
}
