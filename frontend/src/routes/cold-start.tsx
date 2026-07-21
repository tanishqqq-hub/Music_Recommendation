import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Snowflake } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { RecommendationGrid } from "@/components/recommendation-grid";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

export const Route = createFileRoute("/cold-start")({
  head: () => ({
    meta: [
      { title: "Cold Start — Musify" },
      { name: "description", content: "Globally popular artists for new users with no history." },
      { property: "og:title", content: "Cold Start · Musify" },
      { property: "og:description", content: "Popularity-based recommendations for brand-new users." },
    ],
  }),
  component: ColdStartPage,
});

const OPTIONS = [10, 20, 30, 50] as const;

function ColdStartPage() {
  const [k, setK] = useState<number>(20);

  const query = useQuery({
    queryKey: ["cold-start", k],
    queryFn: () => api.coldStart({ k }),
    staleTime: 60_000,
  });

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Discover"
        title="Fresh to Musify? Start here."
        description="Popularity-ranked artists — perfect for cold-start scenarios."
        actions={
          <div className="flex gap-2">
            {OPTIONS.map((opt) => (
              <Button
                key={opt}
                size="sm"
                variant={k === opt ? "default" : "outline"}
                onClick={() => setK(opt)}
              >
                Top {opt}
              </Button>
            ))}
          </div>
        }
      />

      <RecommendationGrid
        items={query.data?.recommendations}
        isLoading={query.isLoading}
        error={query.error as Error | null}
        onRetry={() => query.refetch()}
        emptyTitle="No popular artists"
        emptyDescription="The backend returned an empty list."
      />

      {!query.isLoading && !query.error && (
        <p className="flex items-center gap-2 text-xs text-muted-foreground">
          <Snowflake className="h-3 w-3" />
          Model used: <span className="font-mono text-foreground">{query.data?.model_used}</span>
        </p>
      )}
    </div>
  );
}