import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { activateIndex, listIndexVersions, rebuildIndex } from "@/api/indexes";
import { getSettings, testModelConnection, updateSettings } from "@/api/settings";
import type {
  IndexVersionRead,
  ModelTestResponse,
  SettingsRead,
  SettingsUpdate,
} from "@/api/types";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

type ProviderForm = {
  provider: string;
  model: string;
  base_url: string;
  api_key: string;
  enabled: boolean;
};

type SettingsForm = {
  llm: ProviderForm;
  embedding: ProviderForm;
  retrieval: {
    top_k: number;
    similarity_threshold: number;
    reranker_enabled: boolean;
  };
  pricing: {
    input_per_million: number;
    output_per_million: number;
  };
};

const emptyProvider: ProviderForm = {
  provider: "",
  model: "",
  base_url: "",
  api_key: "",
  enabled: false,
};

function toForm(settings: SettingsRead): SettingsForm {
  return {
    llm: {
      provider: settings.llm.provider ?? "",
      model: settings.llm.model ?? "",
      base_url: settings.llm.base_url ?? "",
      api_key: "",
      enabled: settings.llm.enabled,
    },
    embedding: {
      provider: settings.embedding.provider ?? "",
      model: settings.embedding.model ?? "",
      base_url: settings.embedding.base_url ?? "",
      api_key: "",
      enabled: settings.embedding.enabled,
    },
    retrieval: settings.retrieval,
    pricing: settings.pricing,
  };
}

function indexStatusLabel(version: IndexVersionRead) {
  if (version.status === "ready") return version.is_active ? "当前使用" : "构建完成";
  if (version.status === "failed") return "构建失败";
  return "正在构建";
}

export function SettingsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const settingsQuery = useQuery({
    queryKey: ["settings"],
    queryFn: ({ signal }) => getSettings(signal),
  });
  const indexesQuery = useQuery({
    queryKey: ["indexes"],
    queryFn: ({ signal }) => listIndexVersions(signal),
    refetchInterval: (query) =>
      query.state.data?.versions.some((version) => version.status === "building")
        ? 2000
        : false,
  });
  const [testResults, setTestResults] = useState<
    Partial<Record<"llm" | "embedding", ModelTestResponse>>
  >({});
  const [form, setForm] = useState<SettingsForm>({
    llm: emptyProvider,
    embedding: emptyProvider,
    retrieval: { top_k: 5, similarity_threshold: 0.5, reranker_enabled: false },
    pricing: { input_per_million: 2, output_per_million: 8 },
  });

  useEffect(() => {
    if (settingsQuery.data) {
      setForm(toForm(settingsQuery.data));
    }
  }, [settingsQuery.data]);

  const testMutation = useMutation({
    mutationFn: testModelConnection,
    onSuccess: (result, variables) => {
      setTestResults((current) => ({ ...current, [variables.kind]: result }));
    },
  });

  const updateMutation = useMutation({
    mutationFn: updateSettings,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["settings"] }),
        queryClient.invalidateQueries({ queryKey: ["model-status"] }),
      ]);
    },
  });

  const rebuildMutation = useMutation({
    mutationFn: rebuildIndex,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["indexes"] });
    },
  });

  const activateMutation = useMutation({
    mutationFn: activateIndex,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["indexes"] }),
        queryClient.invalidateQueries({ queryKey: ["knowledge"] }),
        queryClient.invalidateQueries({ queryKey: ["documents"] }),
      ]);
    },
  });

  function testProvider(kind: "llm" | "embedding") {
    const provider = form[kind];
    setTestResults((current) => ({ ...current, [kind]: undefined }));
    testMutation.mutate({
      kind,
      provider: provider.provider,
      model: provider.model,
      base_url: provider.base_url,
      api_key: provider.api_key || undefined,
    });
  }

  function submit() {
    function providerPayload(provider: ProviderForm) {
      return {
        provider: provider.provider,
        model: provider.model,
        base_url: provider.base_url || null,
        enabled: provider.enabled,
        ...(provider.api_key ? { api_key: provider.api_key } : {}),
      };
    }

    const payload: SettingsUpdate = {
      llm: providerPayload(form.llm),
      embedding: providerPayload(form.embedding),
      retrieval: form.retrieval,
      pricing: form.pricing,
    };
    updateMutation.mutate(payload);
  }

  const activeIndex = indexesQuery.data?.versions.find((version) => version.is_active);
  const buildingIndex = indexesQuery.data?.versions.find(
    (version) => version.status === "building",
  );

  if (settingsQuery.isPending) {
    return <p className="px-8 py-10 text-sm text-muted-foreground">正在加载设置……</p>;
  }
  if (settingsQuery.error) {
    return <p className="px-8 py-10 text-sm text-red-600">{settingsQuery.error.message}</p>;
  }

  return (
    <section className="animate-fade-in mx-auto h-full max-w-4xl space-y-6 overflow-y-auto px-4 py-6 sm:px-8 sm:py-10">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">设置</h1>
        <p className="mt-2 text-sm text-muted-foreground">模型与检索参数保存在本地 SQLite 数据库。</p>
      </div>

      <ProviderFields
        title="AI 服务（LLM）"
        value={form.llm}
        hasStoredKey={settingsQuery.data.llm.api_key_configured}
        testing={testMutation.isPending && testMutation.variables?.kind === "llm"}
        result={testResults.llm}
        onChange={(llm) => {
          setForm((current) => ({ ...current, llm }));
          setTestResults((current) => ({ ...current, llm: undefined }));
        }}
        onTest={() => testProvider("llm")}
      />
      <ProviderFields
        title="Embedding"
        value={form.embedding}
        hasStoredKey={settingsQuery.data.embedding.api_key_configured}
        testing={testMutation.isPending && testMutation.variables?.kind === "embedding"}
        result={testResults.embedding}
        onChange={(embedding) => {
          setForm((current) => ({ ...current, embedding }));
          setTestResults((current) => ({ ...current, embedding: undefined }));
        }}
        onTest={() => testProvider("embedding")}
      />

      <Card className="p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="font-medium">索引管理</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              更换 Embedding 模型时，先构建新索引，验证完成后再切换。旧索引会保留用于回滚。
            </p>
          </div>
          <Button
            type="button"
            variant="outline"
            disabled={Boolean(buildingIndex) || rebuildMutation.isPending}
            onClick={() => rebuildMutation.mutate()}
          >
            {buildingIndex || rebuildMutation.isPending ? "正在重建……" : "重建索引"}
          </Button>
        </div>

        {indexesQuery.isPending ? (
          <p className="mt-4 text-sm text-muted-foreground">正在读取索引状态……</p>
        ) : null}
        {indexesQuery.error ? (
          <p className="mt-4 text-sm text-red-600">{indexesQuery.error.message}</p>
        ) : null}
        {rebuildMutation.error ? (
          <p className="mt-4 text-sm text-red-600">{rebuildMutation.error.message}</p>
        ) : null}
        {activateMutation.error ? (
          <p className="mt-4 text-sm text-red-600">{activateMutation.error.message}</p>
        ) : null}

        {activeIndex ? (
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl bg-muted/50 p-3">
              <p className="text-xs text-muted-foreground">当前索引模型</p>
              <p className="mt-1 break-all text-sm font-medium">
                {activeIndex.model === "unknown" ? "历史索引" : activeIndex.model}
              </p>
            </div>
            <div className="rounded-xl bg-muted/50 p-3">
              <p className="text-xs text-muted-foreground">向量维度</p>
              <p className="mt-1 text-sm font-medium">
                {activeIndex.dimension ? `${activeIndex.dimension} 维` : "待检测"}
              </p>
            </div>
            <div className="rounded-xl bg-muted/50 p-3">
              <p className="text-xs text-muted-foreground">知识片段</p>
              <p className="mt-1 text-sm font-medium">{activeIndex.total_chunks}</p>
            </div>
          </div>
        ) : null}

        {indexesQuery.data && indexesQuery.data.versions.length > 0 ? (
          <div className="mt-4 space-y-2">
            {indexesQuery.data.versions.slice(0, 5).map((version) => (
              <div
                key={version.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border p-3"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium">
                      {version.model === "unknown" ? "历史索引" : version.model}
                    </span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs ${
                        version.status === "failed"
                          ? "bg-red-100 text-red-700"
                          : version.is_active
                            ? "bg-emerald-100 text-emerald-700"
                            : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {indexStatusLabel(version)}
                    </span>
                  </div>
                  <p className="mt-1 truncate text-xs text-muted-foreground">
                    {version.collection_name} · {version.dimension || "待检测"} 维 · {" "}
                    {version.total_chunks} 个片段
                  </p>
                  {version.status === "building" ? (
                    <p className="mt-1 text-xs text-amber-700">
                      已处理 {version.processed_documents}/{version.total_documents} 份资料
                    </p>
                  ) : null}
                  {version.error_message ? (
                    <p className="mt-1 text-xs text-red-600">{version.error_message}</p>
                  ) : null}
                </div>
                {version.status === "ready" && !version.is_active ? (
                  <Button
                    type="button"
                    size="sm"
                    disabled={activateMutation.isPending}
                    onClick={() => activateMutation.mutate(version.id)}
                  >
                    切换到此索引
                  </Button>
                ) : null}
              </div>
            ))}
          </div>
        ) : null}
      </Card>

      <details className="rounded-xl border bg-background shadow-sm">
        <summary className="cursor-pointer select-none px-5 py-4 text-sm font-medium">
          高级设置：检索参数
        </summary>
        <div className="border-t px-5 pb-5 pt-4">
        <div className="grid gap-4 md:grid-cols-2">
          <label className="grid gap-2 text-sm">
            <span>Top K</span>
            <input
              type="number"
              min={1}
              max={50}
              value={form.retrieval.top_k}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  retrieval: { ...current.retrieval, top_k: Number(event.target.value) },
                }))
              }
              className="h-10 rounded-md border bg-background px-3 outline-none focus:ring-2 focus:ring-ring"
            />
          </label>
          <label className="grid gap-2 text-sm">
            <span>相似度阈值</span>
            <input
              type="number"
              min={0}
              max={1}
              step={0.05}
              value={form.retrieval.similarity_threshold}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  retrieval: {
                    ...current.retrieval,
                    similarity_threshold: Number(event.target.value),
                  },
                }))
              }
              className="h-10 rounded-md border bg-background px-3 outline-none focus:ring-2 focus:ring-ring"
            />
          </label>
        </div>
        <label className="mt-4 flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.retrieval.reranker_enabled}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                retrieval: { ...current.retrieval, reranker_enabled: event.target.checked },
              }))
            }
          />
          启用 Reranker
        </label>
        </div>
      </details>

      <details className="rounded-xl border bg-background shadow-sm">
        <summary className="cursor-pointer select-none px-5 py-4 text-sm font-medium">
          高级设置：计费单价（元 / 百万 tokens）
        </summary>
        <div className="border-t px-5 pb-5 pt-4">
          <p className="mb-4 text-xs text-muted-foreground">
            用于评估报告页的费用估算，修改后历史记录按新单价重新计算。
          </p>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="grid gap-2 text-sm">
              <span>输入单价</span>
              <input
                type="number"
                min={0}
                step={0.1}
                value={form.pricing.input_per_million}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    pricing: {
                      ...current.pricing,
                      input_per_million: Number(event.target.value),
                    },
                  }))
                }
                className="h-10 rounded-md border bg-background px-3 outline-none focus:ring-2 focus:ring-ring"
              />
            </label>
            <label className="grid gap-2 text-sm">
              <span>输出单价</span>
              <input
                type="number"
                min={0}
                step={0.1}
                value={form.pricing.output_per_million}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    pricing: {
                      ...current.pricing,
                      output_per_million: Number(event.target.value),
                    },
                  }))
                }
                className="h-10 rounded-md border bg-background px-3 outline-none focus:ring-2 focus:ring-ring"
              />
            </label>
          </div>
        </div>
      </details>

      <Card className="p-5">
        <h2 className="font-medium">系统</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          数据目录：{settingsQuery.data.system.data_dir}
        </p>
        <Button
          variant="outline"
          className="mt-4"
          onClick={() => navigate("/welcome")}
        >
          查看引导页
        </Button>
      </Card>

      <div className="flex items-center gap-4">
        <Button onClick={submit} disabled={updateMutation.isPending}>
          {updateMutation.isPending ? "保存中……" : "保存设置"}
        </Button>
        {updateMutation.isSuccess ? (
          <span className="text-sm text-emerald-600">设置已保存</span>
        ) : null}
        {updateMutation.error ? (
          <span className="text-sm text-red-600">{updateMutation.error.message}</span>
        ) : null}
      </div>
    </section>
  );
}

type ProviderFieldsProps = {
  title: string;
  value: ProviderForm;
  hasStoredKey: boolean;
  testing: boolean;
  result?: ModelTestResponse;
  onChange: (value: ProviderForm) => void;
  onTest: () => void;
};

function ProviderFields({
  title,
  value,
  hasStoredKey,
  testing,
  result,
  onChange,
  onTest,
}: ProviderFieldsProps) {
  const inputClass =
    "h-10 rounded-md border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring";
  const canTest = Boolean(
    value.provider.trim() &&
      value.model.trim() &&
      value.base_url.trim() &&
      (value.api_key.trim() || hasStoredKey),
  );

  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <h2 className="font-medium">{title}</h2>
        <div className="flex items-center gap-4">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={!canTest || testing}
            onClick={onTest}
          >
            {testing ? "测试中……" : "测试连接"}
          </Button>
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <input
              type="checkbox"
              checked={value.enabled}
              onChange={(event) => onChange({ ...value, enabled: event.target.checked })}
            />
            启用
          </label>
        </div>
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <label className="grid gap-2 text-sm">
          <span>Provider</span>
          <input
            value={value.provider}
            onChange={(event) => onChange({ ...value, provider: event.target.value })}
            placeholder="openai / qwen / deepseek / custom"
            className={inputClass}
          />
        </label>
        <label className="grid gap-2 text-sm">
          <span>Model</span>
          <input
            value={value.model}
            onChange={(event) => onChange({ ...value, model: event.target.value })}
            className={inputClass}
          />
        </label>
        <label className="grid gap-2 text-sm">
          <span>Base URL</span>
          <input
            value={value.base_url}
            onChange={(event) => onChange({ ...value, base_url: event.target.value })}
            className={inputClass}
          />
        </label>
        <label className="grid gap-2 text-sm">
          <span>API Key</span>
          <input
            type="password"
            value={value.api_key}
            onChange={(event) => onChange({ ...value, api_key: event.target.value })}
            placeholder={hasStoredKey ? "已保存，留空则使用原 Key" : "请输入 API Key"}
            className={inputClass}
          />
        </label>
      </div>
      {!canTest && !testing ? (
        <p className="mt-3 text-xs text-muted-foreground">
          请填写 Provider、Model、Base URL 和 API Key 后再测试。
        </p>
      ) : null}
      {result ? (
        <p
          className={`mt-3 text-sm ${
            result.connected ? "text-emerald-600" : "text-red-600"
          }`}
        >
          {result.connected
            ? `连接成功${
                result.dimension ? ` · ${result.dimension} 维` : ""
              } · ${result.latency_ms ?? 0} ms`
            : result.message}
        </p>
      ) : null}
    </Card>
  );
}
