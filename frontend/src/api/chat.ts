import { ApiError, apiFetch, apiUrl } from "@/api/client";
import type { ChatResponse, Citation, ChatRoute } from "@/api/types";

export type ChatStreamEvent =
  | {
      type: "search_status";
      status: "understanding" | "searching" | "found" | "evaluating" | "generating" | "completed";
      message: string;
      count: number | null;
    }
  | { type: "answer_delta"; delta: string }
  | { type: "citation"; citation: Citation }
  | {
      type: "completed";
      conversation_id: string;
      knowledge_base_id: string | null;
      route: ChatRoute;
      citations: Citation[];
      suggest_human?: boolean;
      follow_ups?: string[];
    }
  | { type: "error"; detail: string };

export function sendChat(message: string, conversationId?: string) {
  return apiFetch<ChatResponse>("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      conversation_id: conversationId ?? null,
      top_k: 5,
    }),
  });
}

type ChatStreamOptions = {
  conversationId?: string;
  knowledgeBaseId?: string;
  allowGeneralFallback?: boolean;
  channel?: "customer" | "staff";
  signal?: AbortSignal;
};

export async function sendChatStream(
  message: string,
  onEvent: (event: ChatStreamEvent) => void,
  options: ChatStreamOptions = {},
) {
  const response = await fetch(apiUrl("/chat"), {
    method: "POST",
    headers: {
      Accept: "text/event-stream",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message,
      conversation_id: options.conversationId ?? null,
      knowledge_base_id: options.knowledgeBaseId ?? null,
      allow_general_fallback: options.allowGeneralFallback ?? false,
      channel: options.channel ?? "customer",
      top_k: 5,
    }),
    signal: options.signal,
  });

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      detail = body.detail ?? detail;
    } catch {
      // Keep the status-based error when the response is not JSON.
    }
    throw new ApiError(detail, response.status);
  }
  if (!response.body) {
    throw new Error("Streaming response body is unavailable.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    let boundary = buffer.indexOf("\n\n");
    while (boundary >= 0) {
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      dispatchEventBlock(block, onEvent);
      boundary = buffer.indexOf("\n\n");
    }
    if (done) break;
  }
}

function dispatchEventBlock(block: string, onEvent: (event: ChatStreamEvent) => void) {
  const data = block
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart())
    .join("\n");
  if (data) onEvent(JSON.parse(data) as ChatStreamEvent);
}
