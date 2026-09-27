import { apiFetch } from "@/api/client";
import type {
  ModelTestRequest,
  ModelTestResponse,
  SettingsRead,
  SettingsUpdate,
} from "@/api/types";

export function getSettings(signal?: AbortSignal) {
  return apiFetch<SettingsRead>("/settings", { signal });
}

export function updateSettings(input: SettingsUpdate) {
  return apiFetch<SettingsRead>("/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}


export function testModelConnection(input: ModelTestRequest) {
  return apiFetch<ModelTestResponse>("/settings/test-model", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}
