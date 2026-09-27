import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BarChart3, Loader2, Play } from "lucide-react";

import { getLatestEvalReport, runEval } from "@/api/eval";
import { getUsageSummary } from "@/api/usage";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

function formatTokens(value: number) {
  if (value >= 10000) return `${(value / 10000).toFixed(1)} 万`;
  return value.toLocaleString();
}

const sourceLabels: Record<string, string> = {
  chat: "聊天",
  eval: "评估",
};

function UsageSection() {
  const usageQuery = useQuery({
    queryKey: ["usage-summary"],
    queryFn: ({ signal }) => getUsageSummary(signal),
  });
  const usage = usageQuery.data;

  if (usageQuery.isPending) {
    return (
      <Card className="p-5 text-sm text-muted-foreground">正在加载用量统计……</Card>
    );
  }
  if (!usage) {
    return (
      <Card className="p-5 text-sm text-muted-foreground">
        用量统计暂不可用，请确认后端已启动。
      </Card>
    );
  }

  const stats = [
    { label: "今日 Token", value: formatTokens(usage.today.total_tokens) },
    { label: "今日费用", value: `¥${usage.today.cost_cny.toFixed(4)}` },
    { label: "累计 Token", value: formatTokens(usage.total.total_tokens) },
    { label: "累计费用", value: `¥${usage.total.cost_cny.toFixed(4)}` },
  ];

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-medium">Token 用量与费用</h2>
        <span className="text-xs text-muted-foreground">
          单价：输入 ¥{usage.pricing.input_per_million}/百万 · 输出 ¥
          {usage.pricing.output_per_million}/百万（模型设置中可调整）
        </span>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-4">
        {stats.map((stat) => (
          <div key={stat.label} className="rounded-xl bg-muted/50 px-4 py-3">
            <p className="text-xs text-muted-foreground">{stat.label}</p>
            <p className="mt-1 text-xl font-semibold">{stat.value}</p>
          </div>
        ))}
      </div>
      {usage.recent.length ? (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-xs text-muted-foreground">
                <th className="py-2 pr-4 font-medium">时间</th>
                <th className="py-2 pr-4 font-medium">来源</th>
                <th className="py-2 pr-4 font-medium">模型</th>
                <th className="py-2 pr-4 text-right font-medium">输入</th>
                <th className="py-2 pr-4 text-right font-medium">输出</th>
                <th className="py-2 text-right font-medium">费用</th>
              </tr>
            </thead>
            <tbody>
              {usage.recent.slice(0, 10).map((record, index) => (
                <tr key={index} className="border-b last:border-0">
                  <td className="py-2 pr-4 text-muted-foreground">
                    {new Date(record.created_at).toLocaleString("zh-CN")}
                  </td>
                  <td className="py-2 pr-4">
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-xs",
                        record.source === "eval"
                          ? "bg-[#C8A45D]/15 text-[#8a6d3b]"
                          : "bg-primary/10 text-primary",
                      )}
                    >
                      {sourceLabels[record.source] ?? record.source}
                    </span>
                  </td>
                  <td className="py-2 pr-4 text-muted-foreground">{record.model || "-"}</td>
                  <td className="py-2 pr-4 text-right">
                    {record.prompt_tokens.toLocaleString()}
                  </td>
                  <td className="py-2 pr-4 text-right">
                    {record.completion_tokens.toLocaleString()}
                  </td>
                  <td className="py-2 text-right">¥{record.cost_cny.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="mt-4 text-xs text-muted-foreground">
          还没有计费记录。模型问答或运行评估后，这里会展示每次调用的 token 消耗。
        </p>
      )}
    </Card>
  );
}

export function EvalPage() {
  const queryClient = useQueryClient();
  const reportQuery = useQuery({
    queryKey: ["eval-latest-report"],
    queryFn: () => getLatestEvalReport(),
  });
  const runMutation = useMutation({
    mutationFn: runEval,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["eval-latest-report"] });
      void queryClient.invalidateQueries({ queryKey: ["usage-summary"] });
    },
  });

  const runButton = (
    <Button
      size="sm"
      disabled={runMutation.isPending}
      onClick={() => runMutation.mutate()}
    >
      {runMutation.isPending ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <Play className="h-4 w-4" />
      )}
      {runMutation.isPending ? "评估运行中……" : "运行评估"}
    </Button>
  );

  if (reportQuery.isLoading) {
    return <div className="p-8 text-sm text-muted-foreground">正在加载评估报告……</div>;
  }

  const report = reportQuery.data;
  if (!report) {
    return (
      <div className="h-full overflow-y-auto p-6 sm:p-8">
        <div className="mx-auto max-w-4xl space-y-6">
          <UsageSection />
          <Card className="p-8 text-center">
            <BarChart3 className="mx-auto h-10 w-10 text-muted-foreground" />
            <h1 className="mt-4 text-lg font-semibold">还没有评估报告</h1>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              评估报告用于离线检验问答质量：用固定的测试题集跑完整问答链路，
              统计准确率与缺失要点。它不会随日常聊天变化，点击"运行评估"才会生成新报告。
            </p>
            <div className="mt-5">{runButton}</div>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-6 sm:p-8">
      <div className="mx-auto max-w-4xl space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold">评估报告</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              数据集 {report.dataset} · {new Date(report.created_at).toLocaleString()}
              ，离线评测结果，不随聊天变化
            </p>
          </div>
          {runButton}
        </div>

        <UsageSection />

        <div className="grid gap-4 sm:grid-cols-3">
          <Card className="p-5">
            <p className="text-sm text-muted-foreground">准确率</p>
            <p className="mt-1 text-3xl font-semibold">{(report.accuracy * 100).toFixed(1)}%</p>
          </Card>
          <Card className="p-5">
            <p className="text-sm text-muted-foreground">回答正确</p>
            <p className="mt-1 text-3xl font-semibold">
              {report.correct} / {report.total}
            </p>
          </Card>
          <Card className="p-5">
            <p className="text-sm text-muted-foreground">平均延迟</p>
            <p className="mt-1 text-3xl font-semibold">
              {Math.round(
                report.results.reduce((sum, item) => sum + item.latency_ms, 0) /
                  Math.max(report.results.length, 1),
              )}
              <span className="text-base font-normal text-muted-foreground"> ms</span>
            </p>
          </Card>
        </div>

        <Card className="overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50 text-left text-xs text-muted-foreground">
                <th className="px-4 py-3 font-medium">测试问题</th>
                <th className="px-4 py-3 font-medium">结果</th>
                <th className="px-4 py-3 font-medium">路由</th>
                <th className="px-4 py-3 font-medium">引用</th>
                <th className="px-4 py-3 font-medium">缺失关键词</th>
              </tr>
            </thead>
            <tbody>
              {report.results.map((item, index) => (
                <tr key={index} className="border-b last:border-0">
                  <td className="max-w-[280px] px-4 py-3">
                    <p className="truncate font-medium" title={item.question}>
                      {item.question}
                    </p>
                    {item.error ? (
                      <p className="mt-1 text-xs text-destructive">{item.error}</p>
                    ) : null}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        "rounded-full px-2.5 py-1 text-xs font-medium",
                        item.correct
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-red-100 text-red-700",
                      )}
                    >
                      {item.correct ? "正确" : "错误"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{item.route ?? "-"}</td>
                  <td className="px-4 py-3 text-muted-foreground">{item.citations_count}</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {item.missing_keywords.length ? item.missing_keywords.join("、") : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </div>
  );
}
