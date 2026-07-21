import { createFileRoute } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Sparkles } from "lucide-react";
import { toast } from "sonner";

import { PageHeader } from "@/components/page-header";
import { RecommendationGrid } from "@/components/recommendation-grid";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api, type RecommendationMode } from "@/lib/api";

const schema = z.object({
  user_id: z.string().min(1, "User ID is required"),
  k: z.number().int().min(1).max(50),
  mode: z.enum(["hybrid", "svd", "content", "popularity"]),
});
type FormValues = z.infer<typeof schema>;

export const Route = createFileRoute("/recommendations")({
  head: () => ({
    meta: [
      { title: "For You — Musify" },
      { name: "description", content: "Personalized artist recommendations for a known user." },
      { property: "og:title", content: "Personalized recommendations · Musify" },
      { property: "og:description", content: "Hybrid SVD + content + popularity recommender." },
    ],
  }),
  component: RecommendationsPage,
});

function RecommendationsPage() {
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { user_id: "1", k: 12, mode: "hybrid" },
  });

  const mutation = useMutation({
    mutationFn: (values: FormValues) => api.userRecommendations(values),
    onError: (e: Error) => toast.error(e.message),
    onSuccess: (data) => toast.success(`Loaded ${data.recommendations.length} recs (${data.model_used})`),
  });

  const onSubmit = form.handleSubmit((v) => mutation.mutate(v));

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="For You"
        title="Personalized recommendations"
        description="Enter a user ID to generate ranked artists using the model of your choice."
      />

      <form
        onSubmit={onSubmit}
        className="glass grid gap-4 rounded-xl p-5 sm:grid-cols-2 lg:grid-cols-[1fr_140px_180px_auto]"
      >
        <div className="space-y-1.5">
          <Label htmlFor="user_id">User ID</Label>
          <Input id="user_id" placeholder="e.g. 42" {...form.register("user_id")} />
          {form.formState.errors.user_id && (
            <p className="text-xs text-destructive">{form.formState.errors.user_id.message}</p>
          )}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="k">Results</Label>
          <Input id="k" type="number" min={1} max={50} {...form.register("k", { valueAsNumber: true })} />
        </div>
        <div className="space-y-1.5">
          <Label>Mode</Label>
          <Select
            value={form.watch("mode")}
            onValueChange={(v) => form.setValue("mode", v as RecommendationMode)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="hybrid">Hybrid</SelectItem>
              <SelectItem value="svd">SVD</SelectItem>
              <SelectItem value="content">Content-based</SelectItem>
              <SelectItem value="popularity">Popularity</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-end">
          <Button type="submit" className="w-full" disabled={mutation.isPending}>
            <Sparkles className="mr-2 h-4 w-4" />
            {mutation.isPending ? "Generating..." : "Recommend"}
          </Button>
        </div>
      </form>

      <RecommendationGrid
        items={mutation.data?.recommendations}
        isLoading={mutation.isPending}
        error={mutation.error as Error | null}
        onRetry={() => mutation.mutate(form.getValues())}
        emptyTitle="Ready when you are"
        emptyDescription="Submit a user ID above to see personalized artist recommendations."
      />
    </div>
  );
}