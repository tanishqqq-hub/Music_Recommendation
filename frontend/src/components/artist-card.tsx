import { motion } from "framer-motion";
import { Play, TrendingUp } from "lucide-react";
import { Link } from "@tanstack/react-router";

import { ArtistAvatar } from "./artist-avatar";
import { Badge } from "@/components/ui/badge";
import type { RecommendationItem } from "@/lib/api";

export function ArtistCard({ item, rank }: { item: RecommendationItem; rank?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      whileHover={{ y: -4 }}
      className="group relative"
    >
      <Link
        to="/similar"
        search={{ artist: item.artist_name }}
        className="block rounded-xl border border-border/60 bg-card/60 p-4 transition-all hover:border-primary/50 hover:bg-card hover:shadow-glow"
      >
        <div className="relative">
          <ArtistAvatar name={item.artist_name} className="aspect-square w-full rounded-lg text-3xl" />
          <button
            aria-label={`Play ${item.artist_name}`}
            className="absolute bottom-2 right-2 flex h-11 w-11 translate-y-2 items-center justify-center rounded-full bg-primary text-primary-foreground opacity-0 shadow-glow transition-all group-hover:translate-y-0 group-hover:opacity-100"
          >
            <Play className="h-5 w-5 fill-current" />
          </button>
          {typeof rank === "number" && (
            <div className="absolute left-2 top-2 rounded-md bg-black/60 px-2 py-0.5 text-xs font-semibold text-white backdrop-blur">
              #{rank + 1}
            </div>
          )}
        </div>
        <div className="mt-3 space-y-1">
          <p className="truncate font-semibold text-foreground">{item.artist_name}</p>
          <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
            <Badge variant="secondary" className="capitalize">
              {item.source}
            </Badge>
            <span className="flex items-center gap-1">
              <TrendingUp className="h-3 w-3" />
              {item.score.toFixed(3)}
            </span>
          </div>
        </div>
      </Link>
    </motion.div>
  );
}