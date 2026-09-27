import { apiFetch } from "@/api/client";
import type { ConversationDetail, ConversationSummary } from "@/api/types";

export function listConversations(signal?: AbortSignal) {
  return apiFetch<ConversationSummary[]>("/conversations", { signal });
}

export function getConversation(id: string, signal?: AbortSignal) {
  return apiFetch<ConversationDetail>(`/conversations/${encodeURIComponent(id)}`, { signal });
}

export function deleteConversation(id: string) {
  return apiFetch<{ detail: string }>(`/conversations/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

export type HotQuestion = { text: string; count: number };

export function getHotQuestions(signal?: AbortSignal) {
  return apiFetch<HotQuestion[]>("/conversations/hot-questions", { signal });
}
