import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowUp,
  BadgePercent,
  BookOpen,
  Bot,
  Check,
  Clock3,
  Copy,
  Gift,
  Globe2,
  Headset,
  Loader2,
  Phone,
  Plus,
  ReceiptText,
  RotateCw,
  ShieldCheck,
  TrendingUp,
} from "lucide-react";
import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { sendChatStream } from "@/api/chat";
import { ApiError } from "@/api/client";
import { getConversation, getHotQuestions } from "@/api/conversations";
import { listKnowledgeBases } from "@/api/knowledge";
import type { Citation, ChatRoute } from "@/api/types";
import { CitationPanel } from "@/components/citation-panel";
import { CiticLogo } from "@/components/citic-logo";
import { CreditCardVisual } from "@/components/credit-card-visual";
import { MarkdownAnswer } from "@/components/markdown-answer";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { extractKeyFacts } from "@/lib/key-facts";

type DisplayMessage = {
  role: "user" | "assistant";
  content: string;
  route?: ChatRoute;
  citations?: Citation[];
  suggestHuman?: boolean;
  followUps?: string[];
  failed?: boolean;
  retryMessage?: string;
};

const routeLabels: Record<ChatRoute, string> = {
  knowledge: "依据业务资料回答",
  hybrid: "依据业务资料回答（部分内容资料未覆盖）",
  general: "通用信息，仅供参考",
  guidance: "",
};

const LAST_CONVERSATION_KEY_PREFIX = "personal-knowledge:last-conversation";

const categories = [
  { icon: ReceiptText, title: "账单还款", text: "忘记还款了怎么办？" },
  { icon: BadgePercent, title: "年费费用", text: "信用卡年费怎么减免？" },
  { icon: TrendingUp, title: "额度管理", text: "额度如何提升？" },
  { icon: Gift, title: "积分权益", text: "积分怎么查询和使用？" },
];

export function ChatPage({ variant = "customer" }: { variant?: "customer" | "staff" }) {
  const lastConversationKey = `${LAST_CONVERSATION_KEY_PREFIX}:${variant}`;
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const conversationId = searchParams.get("conversation");
  const knowledgeBaseId = searchParams.get("knowledge_base_id");
  const initialQuestion = searchParams.get("q");
  const [input, setInput] = useState("");
  const [allowGeneralFallback, setAllowGeneralFallback] = useState(false);
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamStatus, setStreamStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [copiedMessage, setCopiedMessage] = useState<number | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const skipConversationSyncRef = useRef(false);
  const initialQuestionHandledRef = useRef(false);

  useEffect(() => {
    if (conversationId) return;
    const stored = window.localStorage.getItem(lastConversationKey);
    if (!stored) return;
    try {
      const parsed = JSON.parse(stored) as {
        conversationId: string;
        knowledgeBaseId?: string | null;
      };
      setSearchParams(
        {
          conversation: parsed.conversationId,
          ...(parsed.knowledgeBaseId ? { knowledge_base_id: parsed.knowledgeBaseId } : {}),
        },
        { replace: true },
      );
    } catch {
      setSearchParams({ conversation: stored }, { replace: true });
    }
  }, [conversationId, setSearchParams]);

  const conversationQuery = useQuery({
    queryKey: ["conversation", conversationId],
    queryFn: ({ signal }) => getConversation(conversationId!, signal),
    enabled: Boolean(conversationId),
  });

  const knowledgeBasesQuery = useQuery({
    queryKey: ["knowledge-bases"],
    queryFn: ({ signal }) => listKnowledgeBases(signal),
    enabled: Boolean(knowledgeBaseId),
  });
  const hotQuestionsQuery = useQuery({
    queryKey: ["hot-questions"],
    queryFn: ({ signal }) => getHotQuestions(signal),
    enabled: variant === "customer",
    staleTime: 60_000,
  });
  const scopedKnowledgeBase = knowledgeBasesQuery.data?.find(
    (item) => item.id === knowledgeBaseId,
  );

  useEffect(() => {
    if (!conversationId || !conversationQuery.data) return;
    window.localStorage.setItem(
      lastConversationKey,
      JSON.stringify({
        conversationId,
        knowledgeBaseId: conversationQuery.data.knowledge_base_id,
      }),
    );
    if (conversationQuery.data.knowledge_base_id && !knowledgeBaseId) {
      setSearchParams(
        {
          conversation: conversationId,
          knowledge_base_id: conversationQuery.data.knowledge_base_id,
        },
        { replace: true },
      );
    }
  }, [conversationId, conversationQuery.data, knowledgeBaseId, setSearchParams]);

  useEffect(() => {
    if (conversationQuery.error instanceof ApiError && conversationQuery.error.status === 404) {
      window.localStorage.removeItem(lastConversationKey);
      setSearchParams({}, { replace: true });
    }
  }, [conversationQuery.error, setSearchParams]);

  useEffect(() => {
    function handleShortcut(event: globalThis.KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        inputRef.current?.focus();
      }
      if (event.key === "Escape") setSelectedCitation(null);
    }
    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, []);

  useEffect(() => {
    const container = scrollRef.current;
    if (!container) return;
    if (typeof container.scrollTo === "function") {
      container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
    } else {
      container.scrollTop = container.scrollHeight;
    }
  }, [messages, streamStatus]);

  useEffect(() => {
    if (!conversationQuery.data) {
      if (!conversationId) setMessages([]);
      return;
    }
    if (skipConversationSyncRef.current) {
      skipConversationSyncRef.current = false;
      return;
    }
    const loadedMessages = conversationQuery.data.messages
      .filter((message) => message.role !== "system")
      .filter((message) => message.role !== "assistant" || message.content.trim())
      .map((message) => ({
        role: message.role === "assistant" ? ("assistant" as const) : ("user" as const),
        content: message.content,
        citations: message.citations,
      }));
    const normalizedMessages = collapseConsecutiveUserMessages(loadedMessages);
    if (normalizedMessages.at(-1)?.role === "user") {
      const failedQuestion = normalizedMessages.at(-1)!.content;
      normalizedMessages.push({
        role: "assistant",
        content: "上一条问题没有得到完整回答，可以点击重试。",
        failed: true,
        retryMessage: failedQuestion,
      });
    }
    setMessages(normalizedMessages);
  }, [conversationId, conversationQuery.data]);

  function startNewConversation() {
    window.localStorage.removeItem(lastConversationKey);
    setSearchParams(
      knowledgeBaseId ? { knowledge_base_id: knowledgeBaseId } : {},
      { replace: true },
    );
    setMessages([]);
    setSelectedCitation(null);
    setError(null);
    inputRef.current?.focus();
  }

  function switchToGlobalSearch() {
    setSearchParams({}, { replace: true });
    setMessages([]);
    setSelectedCitation(null);
    setError(null);
    inputRef.current?.focus();
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await sendMessage(input.trim());
  }

  async function sendMessage(message: string, appendUserMessage = true) {
    if (!message || isStreaming) return;

    skipConversationSyncRef.current = true;
    setMessages((current) => [
      ...current,
      ...(appendUserMessage ? [{ role: "user" as const, content: message }] : []),
      { role: "assistant", content: "" },
    ]);
    setInput("");
    setError(null);
    setStreamStatus("正在理解您的问题……");
    setIsStreaming(true);
    let completed = false;

    try {
      await sendChatStream(
        message,
        (streamEvent) => {
          if (streamEvent.type === "search_status") {
            setStreamStatus(friendlyStatus(streamEvent.status, streamEvent.message, streamEvent.count));
            return;
          }
          if (streamEvent.type === "answer_delta") {
            setMessages((current) =>
              updateLastMessage(current, (assistant) => ({
                ...assistant,
                content: assistant.content + streamEvent.delta,
              })),
            );
            return;
          }
          if (streamEvent.type === "citation") {
            setMessages((current) =>
              updateLastMessage(current, (assistant) => ({
                ...assistant,
                citations: [...(assistant.citations ?? []), streamEvent.citation],
              })),
            );
            return;
          }
          if (streamEvent.type === "completed") {
            completed = true;
            setMessages((current) =>
              updateLastMessage(current, (assistant) => ({
                ...assistant,
                route: streamEvent.route,
                citations: streamEvent.citations,
                suggestHuman: streamEvent.suggest_human ?? false,
                followUps: streamEvent.follow_ups ?? [],
                failed: false,
              })),
            );
            skipConversationSyncRef.current = true;
            const completedScope = streamEvent.knowledge_base_id ?? knowledgeBaseId;
            window.localStorage.setItem(
              lastConversationKey,
              JSON.stringify({
                conversationId: streamEvent.conversation_id,
                knowledgeBaseId: completedScope,
              }),
            );
            setSearchParams(
              {
                conversation: streamEvent.conversation_id,
                ...(completedScope ? { knowledge_base_id: completedScope } : {}),
              },
              { replace: true },
            );
            void queryClient.invalidateQueries({ queryKey: ["conversations"] });
            setStreamStatus(null);
            return;
          }
          setMessages((current) =>
            markLastAssistantFailed(current, streamEvent.detail, message),
          );
          setError(null);
          setStreamStatus(null);
        },
        {
          conversationId: conversationId ?? undefined,
          knowledgeBaseId: knowledgeBaseId ?? undefined,
          allowGeneralFallback,
          channel: variant,
        },
      );
      if (!completed) {
        setMessages((current) =>
          markLastAssistantFailed(current, "回答未完成，请重试。", message),
        );
        setStreamStatus(null);
      }
    } catch (streamError) {
      setMessages((current) =>
        markLastAssistantFailed(current, formatStreamError(streamError), message),
      );
      setStreamStatus(null);
    } finally {
      setIsStreaming(false);
    }
  }

  async function retryFailedMessage(index: number) {
    const failed = messages[index];
    if (!failed?.retryMessage) return;
    setMessages((current) => current.slice(0, index));
    await sendMessage(failed.retryMessage, false);
  }

  async function copyMessage(content: string, index: number) {
    await navigator.clipboard.writeText(content);
    setCopiedMessage(index);
    window.setTimeout(() => setCopiedMessage(null), 1600);
  }

  useEffect(() => {
    if (!initialQuestion || initialQuestionHandledRef.current) return;
    initialQuestionHandledRef.current = true;
    setSearchParams(
      (current) => {
        const next = new URLSearchParams(current);
        next.delete("q");
        return next;
      },
      { replace: true },
    );
    void sendMessage(initialQuestion);
  }, [initialQuestion, setSearchParams]);

  function handleInputKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  const empty = messages.length === 0;

  return (
    <section
      className="flex h-full bg-[#faf9f4]"
      style={{
        backgroundImage:
          "radial-gradient(1100px 480px at 85% -10%, rgba(200,164,93,0.10), transparent 60%), radial-gradient(900px 420px at 8% 110%, rgba(230,0,18,0.05), transparent 60%)",
      }}
    >
      <div className="flex min-w-0 flex-1 flex-col">
        <div
          className={cn(
            "flex min-h-12 shrink-0 flex-wrap items-center gap-2 border-b border-border/60 px-4 py-1.5 sm:px-8",
            variant === "staff" ? "justify-between" : "justify-end",
          )}
        >
          {variant === "staff" ? (
            knowledgeBaseId ? (
            <div className="flex min-w-0 items-center gap-2 text-xs">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-2.5 py-1 font-medium text-primary">
                <BookOpen className="h-3.5 w-3.5" />
                仅搜索「{scopedKnowledgeBase?.name ?? "当前知识库"}」
              </span>
              <button
                type="button"
                className="text-muted-foreground hover:text-foreground hover:underline"
                onClick={switchToGlobalSearch}
              >
                切回全局
              </button>
            </div>
          ) : (
            <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Globe2 className="h-3.5 w-3.5" />
              {conversationId ? "正在继续一段全局对话" : "全局搜索全部知识库"}
            </p>
          )
          ) : null}
          <div className="flex items-center gap-3">
            {variant === "staff" && knowledgeBaseId ? (
              <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <input
                  type="checkbox"
                  checked={allowGeneralFallback}
                  onChange={(event) => setAllowGeneralFallback(event.target.checked)}
                />
                允许通用补充
              </label>
            ) : null}
            <Button
              variant="ghost"
              size="sm"
              className="h-8 text-xs"
              disabled={isStreaming}
              onClick={startNewConversation}
            >
              <Plus className="h-3.5 w-3.5" />
              新对话
            </Button>
          </div>
        </div>
        <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto px-4 sm:px-8">
          {empty ? (
            <div className="relative flex h-full items-center overflow-hidden">
              <div className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-[#C8A45D]/15 blur-3xl" />
              <div className="pointer-events-none absolute -left-32 bottom-0 h-96 w-96 rounded-full bg-[#E60012]/[0.07] blur-3xl" />
              <div className="relative mx-auto w-full max-w-5xl px-4 sm:px-8">
                <span
                  className="animate-slide-up inline-flex items-center gap-1.5 rounded-full border border-[#C8A45D]/50 bg-[#C8A45D]/10 px-3 py-1 text-xs font-medium text-[#8a6d3b]"
                  style={{ animationDelay: "0ms" }}
                >
                  信用卡业务咨询 · 官方资料解答
                </span>
                <h1
                  className="animate-slide-up mt-4 text-3xl font-semibold tracking-tight sm:text-4xl"
                  style={{ animationDelay: "90ms" }}
                >
                  您好，请问有什么可以帮您？
                </h1>
                <div
                  className="animate-slide-up mt-5 flex items-center gap-3"
                  style={{ animationDelay: "160ms" }}
                  aria-hidden="true"
                >
                  <span className="h-px w-16 bg-gradient-to-r from-transparent to-[#C8A45D]/80" />
                  <span className="h-1.5 w-1.5 rotate-45 bg-[#C8A45D]" />
                  <span className="h-px w-16 bg-gradient-to-l from-transparent to-[#C8A45D]/80" />
                </div>
                <div
                  className="animate-slide-up mt-8 grid items-center gap-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]"
                  style={{ animationDelay: "230ms" }}
                >
                  <CreditCardVisual />
                  <div className="grid gap-3 sm:grid-cols-2">
                    {categories.map(({ icon: Icon, title, text }) => (
                      <button
                        key={title}
                        type="button"
                        onClick={() => {
                          if (isStreaming) return;
                          void sendMessage(text);
                        }}
                        className="group relative flex flex-col gap-2 overflow-hidden rounded-2xl border bg-white/90 p-4 pl-5 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-lg"
                      >
                        <span className="absolute inset-y-0 left-0 w-0.5 bg-gradient-to-b from-[#E60012] to-[#C8A45D] opacity-0 transition-opacity group-hover:opacity-100" />
                        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                          <Icon className="h-4 w-4" />
                        </span>
                        <span className="text-sm font-medium">{title}</span>
                        <span className="text-xs text-muted-foreground">{text}</span>
                      </button>
                    ))}
                  </div>
                </div>
                {hotQuestionsQuery.data?.length ? (
                  <div
                    className="animate-slide-up mt-6 flex flex-wrap items-center gap-2"
                    style={{ animationDelay: "300ms" }}
                  >
                    <span className="text-xs text-muted-foreground">大家都在问：</span>
                    {hotQuestionsQuery.data.map((item) => (
                      <button
                        key={item.text}
                        type="button"
                        disabled={isStreaming}
                        onClick={() => void sendMessage(item.text)}
                        className="rounded-full border border-border bg-white/80 px-3 py-1 text-xs text-foreground/80 transition-all hover:-translate-y-px hover:border-[#C8A45D]/60 hover:text-foreground hover:shadow-sm disabled:opacity-50"
                      >
                        {item.text}
                        {item.count > 1 ? (
                          <span className="ml-1 text-[10px] text-muted-foreground/70">
                            ×{item.count}
                          </span>
                        ) : null}
                      </button>
                    ))}
                  </div>
                ) : null}
                <div
                  className="animate-slide-up mt-10 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-muted-foreground"
                  style={{ animationDelay: "320ms" }}
                >
                  <span className="flex items-center gap-1.5">
                    <ShieldCheck className="h-3.5 w-3.5 text-[#C8A45D]" />
                    官方资料解答
                  </span>
                  <span className="h-3 w-px bg-border" aria-hidden="true" />
                  <span className="flex items-center gap-1.5">
                    <Clock3 className="h-3.5 w-3.5 text-[#C8A45D]" />
                    7×24 全天候在线
                  </span>
                  <span className="h-3 w-px bg-border" aria-hidden="true" />
                  <span className="flex items-center gap-1.5">
                    <Phone className="h-3.5 w-3.5 text-[#C8A45D]" />
                    客服热线 95558
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="mx-auto max-w-5xl space-y-7 py-8">
              {messages.map((message, index) => (
                <div
                  key={`${message.role}-${index}`}
                  className={cn(
                    "animate-slide-up flex gap-3",
                    message.role === "user" ? "justify-end" : "justify-start",
                  )}
                >
                  {message.role === "assistant" ? <AssistantAvatar /> : null}
                  <div className={cn("min-w-0", message.role === "user" ? "max-w-[85%]" : "flex-1")}>
                    {message.role === "assistant" ? (
                      <div className="mb-1.5 flex items-center gap-2 text-xs text-muted-foreground">
                        <span className="font-medium text-foreground">智能顾问</span>
                        {message.route && routeLabels[message.route] ? (
                          <span>
                            {knowledgeBaseId &&
                            message.route === "general" &&
                            !message.citations?.length
                              ? "当前知识库未找到依据"
                              : routeLabels[message.route]}
                          </span>
                        ) : null}
                      </div>
                    ) : null}

                    <div
                      className={cn(
                        message.role === "user"
                          ? "rounded-[1.35rem] rounded-tr-md bg-gradient-to-br from-[#E60012] to-[#a90a16] px-5 py-3.5 text-[15px] leading-7 text-white shadow-md shadow-red-900/20"
                          : "relative rounded-[1.35rem] rounded-tl-md border border-border/70 bg-white/95 px-5 py-5 shadow-sm",
                      )}
                    >
                      {message.role === "assistant" ? (
                        <span
                          className="absolute inset-x-5 top-0 h-px bg-gradient-to-r from-transparent via-[#C8A45D]/70 to-transparent"
                          aria-hidden="true"
                        />
                      ) : null}
                      {message.role === "assistant" ? (
                        message.content ? (
                          <>
                            {renderKeyFacts(message.content, isStreaming && index === messages.length - 1)}
                            <MarkdownAnswer
                              content={message.content}
                              citations={message.citations}
                              onCitation={setSelectedCitation}
                            />
                            {isStreaming && index === messages.length - 1 ? (
                              <span className="stream-caret" />
                            ) : null}
                          </>
                        ) : isStreaming && index === messages.length - 1 ? (
                          <div className="flex items-center gap-3 text-sm text-muted-foreground">
                            <TypingDots />
                            <span>{streamStatus}</span>
                          </div>
                        ) : null
                      ) : (
                        <p className="whitespace-pre-wrap">{message.content}</p>
                      )}
                    </div>

                    {message.role === "assistant" && message.suggestHuman ? (
                      <EscalationCard />
                    ) : null}

                    {message.role === "assistant" && message.content ? (
                      <div className="mt-2 flex flex-wrap items-center gap-1.5">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 text-xs text-muted-foreground"
                          onClick={() => void copyMessage(message.content, index)}
                        >
                          {copiedMessage === index ? (
                            <Check className="h-3.5 w-3.5" />
                          ) : (
                            <Copy className="h-3.5 w-3.5" />
                          )}
                          {copiedMessage === index ? "已复制" : "复制"}
                        </Button>
                        {message.failed && message.retryMessage ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 text-xs text-red-700"
                            onClick={() => void retryFailedMessage(index)}
                          >
                            <RotateCw className="h-3.5 w-3.5" />
                            重试
                          </Button>
                        ) : null}
                        {message.citations?.length ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 text-xs text-muted-foreground"
                            onClick={() => setSelectedCitation(message.citations![0])}
                          >
                            <BookOpen className="h-3.5 w-3.5" />
                            {message.citations.length} 个来源
                          </Button>
                        ) : null}
                        {!message.suggestHuman && !message.failed ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 text-xs text-muted-foreground"
                            onClick={() =>
                              setMessages((current) =>
                                current.map((item, itemIndex) =>
                                  itemIndex === index ? { ...item, suggestHuman: true } : item,
                                ),
                              )
                            }
                          >
                            <Headset className="h-3.5 w-3.5" />
                            没解决
                          </Button>
                        ) : null}
                      </div>
                    ) : null}

                    {message.role === "assistant" &&
                    !message.failed &&
                    message.followUps?.length ? (
                      <div className="mt-2.5 flex flex-wrap items-center gap-2">
                        <span className="text-xs text-muted-foreground">您可能还想问：</span>
                        {message.followUps.map((question) => (
                          <button
                            key={question}
                            type="button"
                            disabled={isStreaming}
                            onClick={() => void sendMessage(question)}
                            className="rounded-full border border-[#C8A45D]/50 bg-[#C8A45D]/10 px-3 py-1 text-xs text-[#8a6d3b] transition-all hover:-translate-y-px hover:bg-[#C8A45D]/25 hover:shadow-sm disabled:opacity-50"
                          >
                            {question}
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </div>
                  {message.role === "user" ? <UserAvatar /> : null}
                </div>
              ))}
              {conversationQuery.error ? (
                <p className="text-sm text-red-600">{conversationQuery.error.message}</p>
              ) : null}
              {error ? <p className="text-sm text-red-600">{error}</p> : null}
            </div>
          )}
        </div>

        <div className="border-t border-border/70 bg-[#faf9f4]/95 px-4 py-4 sm:px-8 sm:py-5">
          <form
            className="mx-auto flex max-w-5xl items-end rounded-2xl border border-border bg-white p-2.5 pl-5 shadow-lg shadow-black/[0.04] transition-all focus-within:border-[#C8A45D]/70 focus-within:shadow-xl focus-within:shadow-[#C8A45D]/10 focus-within:ring-2 focus-within:ring-[#C8A45D]/25"
            onSubmit={handleSubmit}
          >
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleInputKeyDown}
              placeholder={knowledgeBaseId ? `向「${scopedKnowledgeBase?.name ?? "当前知识库"}」提问……` : "请输入您的问题……"}
              className="max-h-40 min-h-14 min-w-0 flex-1 resize-none bg-transparent px-2 py-4 text-[15px] outline-none placeholder:text-muted-foreground/70"
            />
            <Button
              type="submit"
              size="icon"
              className="shine-button h-11 w-11 shrink-0 rounded-xl bg-gradient-to-br from-[#E60012] to-[#a90a16] shadow-md shadow-red-900/25 transition-transform hover:scale-105 hover:bg-gradient-to-br hover:from-[#d60011] hover:to-[#990913]"
              disabled={isStreaming || !input.trim()}
              aria-label="发送"
            >
              {isStreaming ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <ArrowUp className="h-5 w-5" />
              )}
            </Button>
          </form>
          {variant === "staff" ? (
            <p className="mx-auto mt-2 max-w-5xl text-center text-[11px] text-muted-foreground">
              {knowledgeBaseId
                ? "严格模式只使用当前知识库；需要通用补充时请主动勾选。"
                : "回答依据信用卡业务资料生成，不确定时会明确说明。"}
            </p>
          ) : null}
        </div>
      </div>

      {selectedCitation ? (
        <>
          <button
            type="button"
            className="fixed inset-0 z-30 bg-black/20 md:hidden"
            onClick={() => setSelectedCitation(null)}
            aria-label="关闭引用遮罩"
          />
          <CitationPanel citation={selectedCitation} onClose={() => setSelectedCitation(null)} />
        </>
      ) : null}
    </section>
  );
}

function AssistantAvatar() {
  return <CiticLogo className="mt-6 h-9 w-9" />;
}

function renderKeyFacts(content: string, streaming: boolean) {
  if (streaming) return null;
  const facts = extractKeyFacts(content);
  if (facts.length < 2) return null;
  return (
    <div className="mb-3 flex flex-wrap gap-2 rounded-xl border border-[#C8A45D]/40 bg-[#C8A45D]/[0.06] px-3 py-2.5">
      {facts.map((fact) => (
        <span
          key={fact.label}
          className="flex items-baseline gap-1.5 rounded-lg bg-white/90 px-2.5 py-1 text-xs shadow-sm"
        >
          <span className="text-muted-foreground">{fact.label}</span>
          <span className="font-semibold text-[#8a6d3b]">{fact.value}</span>
        </span>
      ))}
    </div>
  );
}

function EscalationCard() {
  return (
    <div className="mt-3 flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      <Headset className="mt-0.5 h-4 w-4 shrink-0" />
      <div>
        <p className="font-medium">没有解决您的问题？</p>
        <p className="mt-1 leading-6">
          建议拨打中信银行信用卡客服热线 95558（7×24 小时），或前往附近网点咨询人工服务。
        </p>
      </div>
    </div>
  );
}

function UserAvatar() {
  return (
    <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-accent text-sm font-semibold text-accent-foreground shadow-sm">
      我
    </div>
  );
}

function TypingDots() {
  return (
    <span className="flex items-center gap-1">
      {[0, 1, 2].map((index) => (
        <span
          key={index}
          className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary/70"
          style={{ animationDelay: `${index * 120}ms` }}
        />
      ))}
    </span>
  );
}

function friendlyStatus(status: string, fallback: string, count: number | null) {
  if (status === "understanding") return "正在理解您的问题……";
  if (status === "searching") return "正在为您查询相关业务资料……";
  if (status === "found") {
    return count ? `已找到 ${count} 条相关资料` : "暂未找到直接相关的业务资料";
  }
  if (status === "evaluating") return "正在核对资料内容……";
  if (status === "generating") return "正在为您整理答复……";
  return fallback;
}

function formatStreamError(error: unknown) {
  if (error instanceof TypeError && error.message.toLowerCase().includes("failed to fetch")) {
    return "与本地后端连接中断。请确认后端窗口仍在运行，然后刷新页面重试。";
  }
  return error instanceof Error ? error.message : "流式请求失败";
}

function collapseConsecutiveUserMessages(messages: DisplayMessage[]) {
  return messages.filter((message, index) => {
    const previous = messages[index - 1];
    return !(
      message.role === "user" &&
      previous?.role === "user" &&
      previous.content === message.content
    );
  });
}

function markLastAssistantFailed(
  messages: DisplayMessage[],
  detail: string,
  retryMessage: string,
) {
  const last = messages.at(-1);
  if (last?.role !== "assistant" || last.failed) return messages;
  const next = [...messages];
  next[next.length - 1] = {
    ...last,
    content: `回答没有完成。\n\n${detail}`,
    failed: true,
    retryMessage,
  };
  return next;
}

function updateLastMessage(
  messages: DisplayMessage[],
  update: (message: DisplayMessage) => DisplayMessage,
) {
  if (messages.length === 0) return messages;
  const next = [...messages];
  next[next.length - 1] = update(next[next.length - 1]);
  return next;
}

