import { ApiError, apiFetch } from "@/api/client";

export type EvalResultItem = {
  question: string;
  answer: string;
  route: string | null;
  citations_count: number;
  latency_ms: number;
  correct: boolean;
  hit_keywords: string[];
  missing_keywords: string[];
  error: string | null;
};

export type EvalReport = {
  dataset: string;
  created_at: string;
  total: number;
  correct: number;
  accuracy: number;
  results: EvalResultItem[];
};

export async function getLatestEvalReport(): Promise<EvalReport | null> {
  try {
    return await apiFetch<EvalReport>("/eval/reports/latest");
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export function runEval(): Promise<EvalReport> {
  return apiFetch<EvalReport>("/eval/run", { method: "POST" });
}
