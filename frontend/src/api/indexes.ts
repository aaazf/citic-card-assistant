import { apiFetch } from "@/api/client";
import type { IndexListResponse, IndexVersionRead } from "@/api/types";

export function listIndexVersions(signal?: AbortSignal) {
  return apiFetch<IndexListResponse>("/indexes", { signal });
}

export function rebuildIndex() {
  return apiFetch<IndexVersionRead>("/indexes/rebuild", { method: "POST" });
}

export function activateIndex(versionId: string) {
  return apiFetch<IndexVersionRead>(`/indexes/${versionId}/activate`, {
    method: "POST",
  });
}
