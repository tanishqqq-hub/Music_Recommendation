import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowRight, Sparkles, Users, Snowflake, Activity } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { RecommendationGrid } from "@/components/recommendation-grid";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Musify — Discover your next favorite artist" },
      {
        name: "description",
        content: "A hybrid music recommender that blends SVD, content similarity, and popularity signals.",
      },
      { property: "og:title", content: "Musify — Discover your next favorite artist" },
      { property: "og:description", content: "Hybrid music recommendations, beautifully rendered." },
    ],
  }),
  component: HomePage,
});

const shortcuts = [
  {
    title: "Personalized for You",
    description: "Blend SVD, content, and popularity signals for a known user.",
    href: "/recommendations" as const,
    icon: Sparkles,
  },
  {
    title: "Find Similar Artists",
    description: "Explore artists that sit near your favorite in latent space.",
    href: "/similar" as const,
    icon: Users,
  },
  {
    title: "Cold Start Picks",
    description: "Popular artists for brand-new users with no history yet.",
    href: "/cold-start" as const,
    icon: Snowflake,
  },
  {
    title: "API Health",
    description: "Confirm the backend and models are online.",
    href: "/health" as const,
    icon: Activity,
  },
];

function HomePage() {
  const trending = useQuery({
    queryKey: ["trending", 10],
    queryFn: () => api.coldStart({ k: 10 }),
    staleTime: 60_000,
  });

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Hybrid recommender"
        title="Discover music you'll actually love."
        description="Musify combines matrix factorization, audio-feature similarity, and popularity signals to surface artists tailored to you."
        actions={
          <>
            <Button asChild size="lg">
              <Link to="/recommendations">
                Get recommendations <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link to="/similar">Explore similar artists</Link>
            </Button>
          </>
        }
      />

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {shortcuts.map((s, i) => (
          <motion.div
            key={s.href}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
          >
            <Link
              to={s.href}
              className="group flex h-full flex-col rounded-xl border border-border/60 bg-card/60 p-5 transition-all hover:-translate-y-1 hover:border-primary/50 hover:bg-card hover:shadow-glow"
            >
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/15 text-primary">
                <s.icon className="h-5 w-5" />
              </div>
              <h3 className="font-semibold text-foreground">{s.title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{s.description}</p>
              <span className="mt-4 inline-flex items-center gap-1 text-xs font-medium text-primary opacity-0 transition-opacity group-hover:opacity-100">
                Open <ArrowRight className="h-3 w-3" />
              </span>
            </Link>
          </motion.div>
        ))}
      </section>

      <section className="space-y-4">
        <div className="flex items-end justify-between">
          <div>
            <h2 className="text-xl font-bold tracking-tight">Trending right now</h2>
            <p className="text-sm text-muted-foreground">Globally popular artists — perfect for new listeners.</p>
          </div>
          <Button asChild variant="ghost" size="sm">
            <Link to="/cold-start">See all</Link>
          </Button>
        </div>
        <RecommendationGrid
          items={trending.data?.recommendations}
          isLoading={trending.isLoading}
          error={trending.error as Error | null}
          onRetry={() => trending.refetch()}
        />
      </section>
    </div>
  );
}