import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Activity, CheckCircle2, XCircle, Cpu, Users, Music } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/error-state";
import { api, API_URL } from "@/lib/api";

export const Route = createFileRoute("/health")({
  head: () => ({
    meta: [
      { title: "API Health — Musify" },
      { name: "description", content: "Live status of the Music Recommendation API and loaded models." },
      { property: "og:title", content: "API Health · Musify" },
      { property: "og:description", content: "Monitor backend availability and loaded models." },
    ],
  }),
  component: HealthPage,
});

function HealthPage() {
  const query = useQuery({
    queryKey: ["health"],
    queryFn: () => api.health(),
    refetchInterval: 15_000,
  });

  const ok = query.data?.status?.toLowerCase() === "ok" || query.data?.status?.toLowerCase() === "healthy";

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Diagnostics"
        title="API Health"
        description={`Connected to ${API_URL}`}
      />

      {query.isLoading ? (
        <div className="grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-xl" />
          ))}
        </div>
      ) : query.error ? (
        <ErrorState error={query.error as Error} onRetry={() => query.refetch()} />
      ) : query.data ? (
        <>
          <Card className="border-border/60 bg-card/60">
            <CardContent className="flex items-center justify-between p-6">
              <div className="flex items-center gap-3">
                {ok ? (
                  <CheckCircle2 className="h-8 w-8 text-primary" />
                ) : (
                  <XCircle className="h-8 w-8 text-destructive" />
                )}
                <div>
                  <p className="text-xs uppercase tracking-widest text-muted-foreground">Status</p>
                  <p className="text-xl font-semibold capitalize">{query.data.status}</p>
                </div>
              </div>
              <Badge variant={ok ? "default" : "destructive"}>
                <Activity className="mr-1 h-3 w-3" /> Live
              </Badge>
            </CardContent>
          </Card>

          <div className="grid gap-4 sm:grid-cols-3">
            <Stat icon={Cpu} label="Models loaded" value={query.data.models_loaded.length} />
            <Stat icon={Music} label="Total artists" value={query.data.total_artists.toLocaleString()} />
            <Stat icon={Users} label="Total users" value={query.data.total_users.toLocaleString()} />
          </div>

          <Card className="border-border/60 bg-card/60">
            <CardContent className="p-6">
              <p className="mb-3 text-xs uppercase tracking-widest text-muted-foreground">Loaded models</p>
              <div className="flex flex-wrap gap-2">
                {query.data.models_loaded.map((m) => (
                  <Badge key={m} variant="secondary" className="font-mono">
                    {m}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}

function Stat({ icon: Icon, label, value }: { icon: typeof Cpu; label: string; value: React.ReactNode }) {
  return (
    <Card className="border-border/60 bg-card/60">
      <CardContent className="flex items-center gap-4 p-6">
        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/15 text-primary">
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="text-xs uppercase tracking-widest text-muted-foreground">{label}</p>
          <p className="text-2xl font-bold">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}