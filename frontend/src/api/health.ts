import { apiFetch } from "@/api/client";
import type { HealthResponse, ModelStatusResponse } from "@/api/types";

export function getHealth(signal?: AbortSignal) {
  return apiFetch<HealthResponse>("/health", { signal });
}

export function getModelStatus(signal?: AbortSignal) {
  return apiFetch<ModelStatusResponse>("/model/status", { signal });
}
