import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronRight, FlaskConical, MessageSquareText, Trash2, Users } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { deleteConversation, listConversations } from "@/api/conversations";
import type { ConversationSummary } from "@/api/types";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type Channel = "customer" | "staff";

const channelTabs: { key: Channel; label: string; hint: string; icon: typeof Users }[] = [
  { key: "customer", label: "客户会话", hint: "客户端页面的真实咨询记录", icon: Users },
  { key: "staff", label: "测试会话", hint: "后台测试问答与评估运行产生的记录", icon: FlaskConical },
];

function groupConversations(conversations: ConversationSummary[]) {
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const startOfYesterday = startOfToday - 24 * 60 * 60 * 1000;
  return {
    today: conversations.filter(
      (item) => new Date(item.updated_at).getTime() >= startOfToday,
    ),
    yesterday: conversations.filter((item) => {
      const time = new Date(item.updated_at).getTime();
      return time >= startOfYesterday && time < startOfToday;
    }),
    earlier: conversations.filter(
      (item) => new Date(item.updated_at).getTime() < startOfYesterday,
    ),
  };
}

function ConversationGroup({
  title,
  items,
  channel,
}: {
  title: string;
  items: ConversationSummary[];
  channel: Channel;
}) {
  if (items.length === 0) return null;
  const basePath = channel === "staff" ? "/admin/chat" : "/";
  return (
    <section className="space-y-2">
      <h2 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</h2>
      {items.map((conversation) => (
        <Card
          key={conversation.id}
          className="group relative flex items-center justify-between gap-3 overflow-hidden p-4 transition-all hover:-translate-y-0.5 hover:shadow-md"
        >
          <Link
            to={
              conversation.knowledge_base_id
                ? `${basePath}?conversation=${encodeURIComponent(conversation.id)}&knowledge_base_id=${encodeURIComponent(conversation.knowledge_base_id)}`
                : `${basePath}?conversation=${encodeURIComponent(conversation.id)}`
            }
            className="absolute inset-0 z-0"
            aria-label={`打开会话：${conversation.title}`}
          />
          <div className="pointer-events-none relative z-10 flex min-w-0 flex-1 items-center gap-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <MessageSquareText className="h-4 w-4" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium">{conversation.title}</span>
              <span className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <span>{new Date(conversation.updated_at).toLocaleString("zh-CN")}</span>
                {conversation.knowledge_base_id ? (
                  <span className="rounded-full bg-primary/10 px-2 py-0.5 text-primary">
                    知识库问答
                  </span>
                ) : null}
              </span>
            </span>
            <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground/50 transition-transform group-hover:translate-x-0.5" />
          </div>
          <div className="relative z-20">
            <DeleteConversationButton id={conversation.id} />
          </div>
        </Card>
      ))}
    </section>
  );
}

function DeleteConversationButton({ id }: { id: string }) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => deleteConversation(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["conversations"] }),
  });
  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label="删除会话"
      disabled={mutation.isPending}
      onClick={() => mutation.mutate()}
    >
      <Trash2 className="h-4 w-4" />
    </Button>
  );
}

export function ConversationsPage() {
  const query = useQuery({
    queryKey: ["conversations"],
    queryFn: ({ signal }) => listConversations(signal),
  });
  const [channel, setChannel] = useState<Channel>("customer");
  const activeTab = channelTabs.find((tab) => tab.key === channel) ?? channelTabs[0];
  const filtered = (query.data ?? []).filter(
    (item) => (item.channel ?? "customer") === channel,
  );
  const groups = groupConversations(filtered);

  return (
    <section className="animate-fade-in mx-auto h-full max-w-4xl overflow-y-auto px-4 py-6 sm:px-8 sm:py-10">
      <h1 className="text-2xl font-semibold tracking-tight">会话记录</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        客户咨询与内部测试分开归档，点击记录可回到对应页面继续对话。
      </p>
      <div className="mt-5 flex gap-2">
        {channelTabs.map(({ key, label, hint, icon: Icon }) => (
          <button
            key={key}
            type="button"
            onClick={() => setChannel(key)}
            className={cn(
              "flex items-center gap-2 rounded-full border px-4 py-2 text-sm transition-all",
              channel === key
                ? "border-primary/50 bg-primary/10 font-medium text-primary shadow-sm"
                : "border-border bg-white/70 text-muted-foreground hover:border-primary/30 hover:text-foreground",
            )}
            title={hint}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>
      {query.isPending ? <p className="mt-6 text-sm text-muted-foreground">正在加载……</p> : null}
      {query.error ? <p className="mt-6 text-sm text-red-600">{query.error.message}</p> : null}
      {!query.isPending && filtered.length === 0 ? (
        <Card className="mt-6 border-dashed p-8 text-center">
          <activeTab.icon className="mx-auto h-6 w-6 text-muted-foreground" />
          <p className="mt-2 text-sm text-muted-foreground">
            {channel === "customer" ? "还没有客户会话。" : "还没有测试会话。"}
          </p>
          <p className="mt-1 text-xs text-muted-foreground/80">{activeTab.hint}</p>
        </Card>
      ) : null}
      <div className="mt-6 space-y-7">
        <ConversationGroup title="今天" items={groups.today} channel={channel} />
        <ConversationGroup title="昨天" items={groups.yesterday} channel={channel} />
        <ConversationGroup title="更早" items={groups.earlier} channel={channel} />
      </div>
    </section>
  );
}
