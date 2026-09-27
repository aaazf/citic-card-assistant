export type HealthResponse = {
  status: "ok";
  version: string;
  database: "ok";
};

export type ProviderStatus = {
  kind: "llm" | "embedding";
  connected: boolean;
  provider: string | null;
  model: string | null;
};

export type ModelStatusResponse = {
  providers: ProviderStatus[];
};

export type KnowledgeBase = {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
};

export type DocumentStatus = "pending" | "processing" | "ready" | "failed";

export type Document = {
  id: string;
  knowledge_base_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: DocumentStatus;
  chunk_count: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type Citation = {
  document_id: string;
  filename: string;
  page: number | null;
  chunk_id: string;
  score: number;
};

export type ChatRoute = "knowledge" | "hybrid" | "general" | "guidance";

export type ChatResponse = {
  conversation_id: string;
  knowledge_base_id: string | null;
  answer: string;
  route: ChatRoute;
  citations: Citation[];
  suggest_human?: boolean;
  follow_ups?: string[];
};

export type ConversationSummary = {
  id: string;
  channel: "customer" | "staff";
  knowledge_base_id: string | null;
  title: string;
  created_at: string;
  updated_at: string;
};

export type ConversationMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations: Citation[];
  created_at: string;
};

export type ConversationDetail = ConversationSummary & {
  messages: ConversationMessage[];
};

export type DocumentChunk = {
  chunk_id: string;
  document_id: string;
  content: string;
  metadata: Record<string, unknown>;
};

export type ProviderConfigRead = {
  provider: string | null;
  model: string | null;
  base_url: string | null;
  api_key_configured: boolean;
  enabled: boolean;
};

export type ProviderConfigUpdate = {
  provider?: string;
  model?: string;
  base_url?: string | null;
  api_key?: string;
  enabled?: boolean;
};

export type SettingsRead = {
  llm: ProviderConfigRead;
  embedding: ProviderConfigRead;
  retrieval: {
    top_k: number;
    similarity_threshold: number;
    reranker_enabled: boolean;
  };
  pricing: {
    input_per_million: number;
    output_per_million: number;
  };
  system: {
    data_dir: string;
  };
};

export type SettingsUpdate = {
  llm?: ProviderConfigUpdate;
  embedding?: ProviderConfigUpdate;
  retrieval?: {
    top_k?: number;
    similarity_threshold?: number;
    reranker_enabled?: boolean;
  };
  pricing?: {
    input_per_million?: number;
    output_per_million?: number;
  };
};


export type ModelTestRequest = {
  kind: "llm" | "embedding";
  provider: string;
  model: string;
  base_url: string;
  api_key?: string;
};

export type ModelTestResponse = {
  kind: "llm" | "embedding";
  connected: boolean;
  message: string;
  latency_ms: number | null;
  model: string | null;
  dimension: number | null;
};

export type IndexVersionStatus = "building" | "ready" | "failed";

export type IndexVersionRead = {
  id: string;
  collection_name: string;
  provider: string;
  model: string;
  base_url: string | null;
  dimension: number;
  chunk_size: number;
  chunk_overlap: number;
  status: IndexVersionStatus;
  total_documents: number;
  processed_documents: number;
  failed_documents: number;
  total_chunks: number;
  error_message: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  activated_at: string | null;
};

export type IndexListResponse = {
  active_version_id: string | null;
  versions: IndexVersionRead[];
};
