import { useMemo } from "react";

// Deterministic gradient per artist, so cards feel like album art without needing images.
const PALETTES = [
  ["#1DB954", "#0f5132"],
  ["#FF6B6B", "#7a1f1f"],
  ["#4C6EF5", "#1a2a6c"],
  ["#F59F00", "#5a3a00"],
  ["#BE4BDB", "#3d1250"],
  ["#15AABF", "#0b3a45"],
  ["#FA5252", "#4a0f0f"],
  ["#20C997", "#0b3d2f"],
];

function hash(str: string) {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h << 5) - h + str.charCodeAt(i);
  return Math.abs(h);
}

export function ArtistAvatar({ name, className }: { name: string; className?: string }) {
  const { bg, initials } = useMemo(() => {
    const [a, b] = PALETTES[hash(name) % PALETTES.length];
    return {
      bg: `linear-gradient(135deg, ${a}, ${b})`,
      initials: name
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((w) => w[0]?.toUpperCase())
        .join(""),
    };
  }, [name]);

  return (
    <div
      className={
        "flex items-center justify-center rounded-lg font-bold text-white/90 shadow-inner " +
        (className ?? "aspect-square w-full text-2xl")
      }
      style={{ background: bg }}
    >
      {initials || "?"}
    </div>
  );
}