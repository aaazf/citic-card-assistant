import { apiFetch } from "@/api/client";
import type { KnowledgeBase } from "@/api/types";

export function listKnowledgeBases(signal?: AbortSignal) {
  return apiFetch<KnowledgeBase[]>("/knowledge", { signal });
}

export function createKnowledgeBase(input: { name: string; description?: string }) {
  return apiFetch<KnowledgeBase>("/knowledge", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export function deleteKnowledgeBase(id: string) {
  return apiFetch<{ detail: string }>(`/knowledge/${id}`, { method: "DELETE" });
}
