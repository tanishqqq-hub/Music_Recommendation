import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Search } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { RecommendationGrid } from "@/components/recommendation-grid";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";

export const Route = createFileRoute("/similar")({
  validateSearch: (search: Record<string, unknown>) => ({
    artist: typeof search.artist === "string" ? search.artist : undefined,
    k: typeof search.k === "number"
      ? search.k
      : typeof search.k === "string" && search.k !== ""
        ? Number(search.k)
        : undefined,
  }),
  head: () => ({
    meta: [
      { title: "Similar Artists — Musify" },
      { name: "description", content: "Find artists similar to any artist using latent-space similarity." },
      { property: "og:title", content: "Similar Artists · Musify" },
      { property: "og:description", content: "SVD latent-space + audio feature similarity." },
    ],
  }),
  component: SimilarPage,
});

const formSchema = z.object({
  artist_name: z.string().min(1, "Artist name is required"),
  k: z.number().int().min(1).max(50),
});
type FormValues = z.infer<typeof formSchema>;

function SimilarPage() {
  const search = Route.useSearch();
  const navigate = useNavigate({ from: Route.fullPath });

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    values: { artist_name: search.artist ?? "", k: search.k ?? 12 },
  });

  const query = useQuery({
    queryKey: ["similar", search.artist, search.k ?? 12],
    queryFn: () => api.similarArtists({ artist_name: search.artist!, k: search.k ?? 12 }),
    enabled: Boolean(search.artist),
    staleTime: 60_000,
  });

  const onSubmit = form.handleSubmit((v) => {
    navigate({ search: { artist: v.artist_name, k: v.k } });
  });

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Similar Artists"
        title="Explore the neighborhood of any artist."
        description="Uses SVD latent space similarity, falling back to audio-feature similarity."
      />

      <form
        onSubmit={onSubmit}
        className="glass grid gap-4 rounded-xl p-5 sm:grid-cols-[1fr_140px_auto]"
      >
        <div className="space-y-1.5">
          <Label htmlFor="artist_name">Artist name</Label>
          <Input id="artist_name" placeholder="e.g. radiohead" {...form.register("artist_name")} />
          {form.formState.errors.artist_name && (
            <p className="text-xs text-destructive">{form.formState.errors.artist_name.message}</p>
          )}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="k">Results</Label>
          <Input id="k" type="number" min={1} max={50} {...form.register("k", { valueAsNumber: true })} />
        </div>
        <div className="flex items-end">
          <Button type="submit" className="w-full">
            <Search className="mr-2 h-4 w-4" />
            Search
          </Button>
        </div>
      </form>

      <RecommendationGrid
        items={query.data?.recommendations}
        isLoading={query.isLoading && Boolean(search.artist)}
        error={query.error as Error | null}
        onRetry={() => query.refetch()}
        emptyTitle={search.artist ? "No similar artists found" : "Search an artist to begin"}
        emptyDescription={search.artist ? "Try a different artist name." : "Type an artist name above to explore nearby artists."}
      />
    </div>
  );
}