import { apiFetch } from "@/api/client";

export type UsageAggregate = {
  calls: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_cny: number;
};

export type UsageRecord = {
  created_at: string;
  source: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  cost_cny: number;
};

export type UsageSummary = {
  today: UsageAggregate;
  total: UsageAggregate;
  pricing: { input_per_million: number; output_per_million: number };
  recent: UsageRecord[];
};

export function getUsageSummary(signal?: AbortSignal) {
  return apiFetch<UsageSummary>("/usage/summary", { signal });
}
