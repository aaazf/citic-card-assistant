import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import App from "@/App";
import { sendChatStream } from "@/api/chat";
import type { ChatStreamEvent } from "@/api/chat";
import { testModelConnection } from "@/api/settings";

vi.mock("@/api/indexes", () => ({
  listIndexVersions: vi.fn().mockResolvedValue({
    active_version_id: null,
    versions: [],
  }),
  rebuildIndex: vi.fn(),
  activateIndex: vi.fn(),
}));

vi.mock("@/api/eval", () => ({
  getLatestEvalReport: vi.fn().mockResolvedValue({
    dataset: "citic-demo",
    created_at: "2026-09-22T00:00:00Z",
    total: 3,
    correct: 2,
    accuracy: 0.667,
    results: [
      {
        question: "忘记还款了怎么办？",
        answer: "测试回答",
        route: "knowledge",
        citations_count: 2,
        latency_ms: 800,
        correct: true,
        hit_keywords: ["逾期"],
        missing_keywords: [],
        error: null,
      },
    ],
  }),
  runEval: vi.fn(),
}));

vi.mock("@/api/health", () => ({
  getModelStatus: vi.fn().mockResolvedValue({
    providers: [
      { kind: "llm", connected: false, provider: null, model: null },
      { kind: "embedding", connected: false, provider: null, model: null },
    ],
  }),
}));

vi.mock("@/api/knowledge", () => ({
  listKnowledgeBases: vi.fn().mockResolvedValue([]),
  createKnowledgeBase: vi.fn(),
  deleteKnowledgeBase: vi.fn(),
}));

vi.mock("@/api/documents", () => ({
  listDocuments: vi.fn().mockResolvedValue([]),
  getDocumentChunk: vi.fn().mockResolvedValue({
    chunk_id: "chunk-1",
    document_id: "document-1",
    content: "引用原文内容",
    metadata: { filename: "notes.txt" },
  }),
  getDocument: vi.fn(),
  listDocumentChunks: vi.fn().mockResolvedValue([]),
  documentContentUrl: vi.fn().mockReturnValue("/api/v1/documents/document-1/content"),
  getDocumentText: vi.fn().mockResolvedValue("预览原文内容"),
  uploadDocument: vi.fn(),
  deleteDocument: vi.fn(),
}));

const { citation } = vi.hoisted(() => ({
  citation: {
  document_id: "document-1",
  filename: "notes.txt",
  page: null,
    chunk_id: "chunk-1",
    score: 0.9,
  },
}));

vi.mock("@/api/chat", () => ({
  sendChatStream: vi.fn().mockImplementation(
    async (_message: string, onEvent: (event: ChatStreamEvent) => void) => {
    onEvent({
      type: "search_status",
      status: "generating",
      message: "正在整理答案……",
      count: 1,
    });
    onEvent({ type: "citation", citation });
    onEvent({ type: "answer_delta", delta: "测试回答 [1]" });
    onEvent({
      type: "completed",
      conversation_id: "conversation-1",
      knowledge_base_id: null,
      route: "knowledge",
      citations: [citation],
    });
    },
  ),
}));

vi.mock("@/api/conversations", () => ({
  listConversations: vi.fn().mockResolvedValue([]),
  getConversation: vi.fn().mockResolvedValue({
    id: "conversation-1",
    title: "历史会话",
    created_at: "2026-09-14T00:00:00Z",
    updated_at: "2026-09-14T00:00:00Z",
    messages: [
      {
        id: "message-1",
        role: "assistant",
        content: "历史回答",
        citations: [],
        created_at: "2026-09-14T00:00:00Z",
      },
    ],
  }),
  deleteConversation: vi.fn(),
  getHotQuestions: vi.fn().mockResolvedValue([]),
}));

vi.mock("@/api/settings", () => ({
  getSettings: vi.fn().mockResolvedValue({
    llm: { provider: null, model: null, base_url: null, api_key_configured: false, enabled: false },
    embedding: {
      provider: null,
      model: null,
      base_url: null,
      api_key_configured: false,
      enabled: false,
    },
    retrieval: { top_k: 5, similarity_threshold: 0.5, reranker_enabled: false },
    pricing: { input_per_million: 2, output_per_million: 8 },
    system: { data_dir: "C:/data" },
  }),
  updateSettings: vi.fn(),
  testModelConnection: vi.fn().mockResolvedValue({
    kind: "llm",
    connected: true,
    message: "连接成功",
    latency_ms: 123,
    model: "test-model",
    dimension: 2048,
  }),
}));

vi.mock("@/api/usage", () => ({
  getUsageSummary: vi.fn().mockResolvedValue({
    today: { calls: 2, prompt_tokens: 1200, completion_tokens: 600, total_tokens: 1800, cost_cny: 0.0072 },
    total: { calls: 5, prompt_tokens: 5200, completion_tokens: 2600, total_tokens: 7800, cost_cny: 0.0312 },
    pricing: { input_per_million: 2, output_per_million: 8 },
    recent: [
      {
        created_at: "2026-09-22T06:30:00Z",
        source: "chat",
        model: "fake-model",
        prompt_tokens: 1200,
        completion_tokens: 600,
        cost_cny: 0.0072,
      },
    ],
  }),
}));

function renderAt(path: string, options: { landingSeen?: boolean } = {}) {
  if (options.landingSeen === false) {
    window.localStorage.removeItem("personal-knowledge:landing-seen");
  } else {
    window.localStorage.setItem("personal-knowledge:landing-seen", "1");
  }
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("App", () => {
  it("renders the main shell and chat empty state", () => {
    renderAt("/");

    expect(screen.getByRole("heading", { name: "您好，请问有什么可以帮您？" })).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/请输入您的问题/)).toBeInTheDocument();
  });

  it("hides staff navigation from the customer chat", () => {
    renderAt("/");

    expect(screen.queryByText("知识库管理")).not.toBeInTheDocument();
    expect(screen.queryByText("模型设置")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "工作人员入口" })).toBeInTheDocument();
  });

  it("shows the landing page before the system on first visit", () => {
    renderAt("/", { landingSeen: false });

    expect(screen.getByText("信用卡智能咨询助手")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /开始咨询/ })).toBeInTheDocument();
  });

  it("renders the admin knowledge route directly without the landing gate", async () => {
    renderAt("/admin/knowledge", { landingSeen: false });

    expect(screen.getByRole("heading", { name: "知识库" })).toBeInTheDocument();
    expect(await screen.findByText("还没有知识库，点击上方按钮新建。")).toBeInTheDocument();
  });

  it("redirects the admin index to the knowledge page", async () => {
    renderAt("/admin");

    expect(screen.getByRole("heading", { name: "知识库" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "知识库管理" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "测试问答" })).toBeInTheDocument();
  });

  it("renders the eval report page in admin", async () => {
    renderAt("/admin/eval");

    expect(await screen.findByRole("heading", { name: "评估报告" })).toBeInTheDocument();
    expect(screen.getByText("66.7%")).toBeInTheDocument();
    expect(screen.getByText("忘记还款了怎么办？")).toBeInTheDocument();
  });

  it("collapses and expands the desktop sidebar", () => {
    renderAt("/admin/knowledge");

    fireEvent.click(screen.getByLabelText("收起侧栏"));

    expect(screen.getByLabelText("展开侧栏")).toBeInTheDocument();
  });

  it("renders the settings form", async () => {
    renderAt("/admin/settings");

    expect(await screen.findByRole("button", { name: "保存设置" })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "测试连接" })).toHaveLength(2);
    expect(screen.getByText("索引管理")).toBeInTheDocument();
    expect(screen.getByText(/数据目录/)).toBeInTheDocument();
  });

  it("tests model connection with the current form values", async () => {
    renderAt("/admin/settings");

    const providerInputs = await screen.findAllByLabelText("Provider");
    fireEvent.change(providerInputs[0], { target: { value: "custom" } });
    fireEvent.change(screen.getAllByLabelText("Model")[0], {
      target: { value: "test-model" },
    });
    fireEvent.change(screen.getAllByLabelText("Base URL")[0], {
      target: { value: "http://localhost:9999/v1" },
    });
    fireEvent.change(screen.getAllByLabelText("API Key")[0], {
      target: { value: "test-key" },
    });
    fireEvent.click(screen.getAllByRole("button", { name: "测试连接" })[0]);

    expect(await screen.findByText("连接成功 · 2048 维 · 123 ms")).toBeInTheDocument();
    const [payload] = vi.mocked(testModelConnection).mock.calls[0];
    expect(payload).toEqual({
      kind: "llm",
      provider: "custom",
      model: "test-model",
      base_url: "http://localhost:9999/v1",
      api_key: "test-key",
    });
  });

  it("restores a saved conversation", async () => {
    renderAt("/?conversation=conversation-1");

    expect(await screen.findByText("历史回答")).toBeInTheDocument();
  });

  it("shows the escalation card when the answer suggests human service", async () => {
    vi.mocked(sendChatStream).mockImplementationOnce(
      async (_message: string, onEvent: (event: ChatStreamEvent) => void) => {
        onEvent({
          type: "completed",
          conversation_id: "conversation-9",
          knowledge_base_id: null,
          route: "general",
          citations: [],
          suggest_human: true,
        });
      },
    );
    renderAt("/");
    fireEvent.change(screen.getByPlaceholderText(/请输入您的问题/), {
      target: { value: "取现手续费是多少" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));

    expect(await screen.findByText("没有解决您的问题？")).toBeInTheDocument();
    expect(screen.getAllByText(/95558/).length).toBeGreaterThan(0);
  });

  it("shows retry feedback when a stream fails", async () => {
    vi.mocked(sendChatStream).mockImplementationOnce(() =>
      Promise.reject(new TypeError("Failed to fetch")),
    );
    renderAt("/");
    fireEvent.change(screen.getByPlaceholderText(/请输入您的问题/), {
      target: { value: "test question" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));

    expect(await screen.findByText(/回答没有完成/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重试" })).toBeInTheDocument();
  });

  it("focuses chat with Ctrl+K and submits a message", async () => {
    renderAt("/");
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    const input = screen.getByPlaceholderText(/请输入您的问题/);
    expect(input).toHaveFocus();
    fireEvent.change(input, { target: { value: "What is Python?" } });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));

    expect(await screen.findByText("依据业务资料回答")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "查看引用 1" }));
    expect(await screen.findByText("引用原文内容")).toBeInTheDocument();
  });
});




