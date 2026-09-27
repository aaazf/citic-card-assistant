import { apiFetch, apiUrl } from "@/api/client";
import type { Document, DocumentChunk } from "@/api/types";

export function listDocuments(knowledgeBaseId?: string, signal?: AbortSignal) {
  const query = knowledgeBaseId
    ? `?knowledge_base_id=${encodeURIComponent(knowledgeBaseId)}`
    : "";
  return apiFetch<Document[]>(`/documents${query}`, { signal });
}

export function uploadDocument(knowledgeBaseId: string, file: File) {
  const body = new FormData();
  body.append("knowledge_base_id", knowledgeBaseId);
  body.append("file", file);
  return apiFetch<Document>("/documents/upload", {
    method: "POST",
    body,
  });
}

export function deleteDocument(id: string) {
  return apiFetch<{ detail: string }>(`/documents/${id}`, { method: "DELETE" });
}


export function getDocumentChunk(documentId: string, chunkId: string, signal?: AbortSignal) {
  return apiFetch<DocumentChunk>(
    `/documents/${encodeURIComponent(documentId)}/chunks/${encodeURIComponent(chunkId)}`,
    { signal },
  );
}


export function getDocument(id: string, signal?: AbortSignal) {
  return apiFetch<Document>(`/documents/${encodeURIComponent(id)}`, { signal });
}

export function listDocumentChunks(id: string, signal?: AbortSignal) {
  return apiFetch<DocumentChunk[]>(`/documents/${encodeURIComponent(id)}/chunks`, { signal });
}

export function documentContentUrl(id: string) {
  return apiUrl(`/documents/${encodeURIComponent(id)}/content`);
}

export async function getDocumentText(id: string, signal?: AbortSignal) {
  const response = await fetch(documentContentUrl(id), { signal });
  if (!response.ok) throw new Error(`Failed to load document: ${response.status}`);
  return response.text();
}
