import { ArtistCard } from "./artist-card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "./empty-state";
import { ErrorState } from "./error-state";
import type { RecommendationItem } from "@/lib/api";
import { Music2 } from "lucide-react";

interface Props {
  items?: RecommendationItem[];
  isLoading?: boolean;
  error?: Error | null;
  onRetry?: () => void;
  emptyTitle?: string;
  emptyDescription?: string;
}

export function RecommendationGrid({
  items,
  isLoading,
  error,
  onRetry,
  emptyTitle = "Nothing to show yet",
  emptyDescription = "Try adjusting your query to see recommendations.",
}: Props) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} className="rounded-xl border border-border/60 bg-card/40 p-4">
            <Skeleton className="aspect-square w-full rounded-lg" />
            <Skeleton className="mt-3 h-4 w-3/4" />
            <Skeleton className="mt-2 h-3 w-1/2" />
          </div>
        ))}
      </div>
    );
  }

  if (error) return <ErrorState error={error} onRetry={onRetry} />;
  if (!items || items.length === 0)
    return <EmptyState icon={Music2} title={emptyTitle} description={emptyDescription} />;

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
      {items.map((item, i) => (
        <ArtistCard key={`${item.artist_name}-${i}`} item={item} rank={i} />
      ))}
    </div>
  );
}