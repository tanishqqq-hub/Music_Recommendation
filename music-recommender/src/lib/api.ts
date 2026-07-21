import { z } from "zod";

const resolvedApiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
export const API_URL = resolvedApiUrl.replace(/\/$/, "");

export const RecommendationItemSchema = z.object({
  artist_name: z.string(),
  score: z.number(),
  source: z.string(),
});

export const RecommendationResponseSchema = z.object({
  user_id: z.string().nullable(),
  k: z.number(),
  recommendations: z.array(RecommendationItemSchema),
  model_used: z.string(),
});

export const HealthResponseSchema = z.object({
  status: z.string(),
  models_loaded: z.array(z.string()),
  total_artists: z.number(),
  total_users: z.number(),
});

export type RecommendationItem = z.infer<typeof RecommendationItemSchema>;
export type RecommendationResponse = z.infer<typeof RecommendationResponseSchema>;
export type HealthResponse = z.infer<typeof HealthResponseSchema>;
export type RecommendationMode = "hybrid" | "svd" | "content" | "popularity";

async function request<T>(path: string, init?: RequestInit, schema?: z.ZodType<T>): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* noop */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  const json = await res.json();
  return schema ? schema.parse(json) : (json as T);
}

export const api = {
  health: () => request("/health", { method: "GET" }, HealthResponseSchema),

  userRecommendations: (payload: { user_id: string; k?: number; mode?: RecommendationMode }) =>
    request(
      "/recommend/user",
      { method: "POST", body: JSON.stringify({ k: 10, mode: "hybrid", ...payload }) },
      RecommendationResponseSchema,
    ),

  similarArtists: (payload: { artist_name: string; k?: number }) =>
    request(
      "/recommend/similar",
      { method: "POST", body: JSON.stringify({ k: 10, ...payload }) },
      RecommendationResponseSchema,
    ),

  coldStart: (payload: { k?: number } = {}) =>
    request(
      "/recommend/cold-start",
      { method: "POST", body: JSON.stringify({ k: 10, ...payload }) },
      RecommendationResponseSchema,
    ),
};