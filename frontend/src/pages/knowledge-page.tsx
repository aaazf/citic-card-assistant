import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BookOpen,
  FileText,
  Loader2,
  MessageCircleQuestion,
  Plus,
  Search,
  Trash2,
  UploadCloud,
  X,
} from "lucide-react";
import { type DragEvent, type FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { deleteDocument, listDocuments, uploadDocument } from "@/api/documents";
import {
  createKnowledgeBase,
  deleteKnowledgeBase,
  listKnowledgeBases,
} from "@/api/knowledge";
import type { Document, DocumentStatus } from "@/api/types";
import { DocumentDetailDrawer } from "@/components/document-detail-drawer";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const statusLabels: Record<DocumentStatus, string> = {
  pending: "等待处理",
  processing: "正在解析并建立索引",
  ready: "已完成",
  failed: "处理失败",
};

const statusStyles: Record<DocumentStatus, string> = {
  pending: "bg-amber-100 text-amber-800",
  processing: "bg-sky-100 text-sky-800",
  ready: "bg-emerald-100 text-emerald-800",
  failed: "bg-red-100 text-red-700",
};

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function indexStatus(documents: Document[]) {
  if (documents.length === 0) {
    return { label: "尚未添加资料", tone: "bg-muted-foreground/40" };
  }
  if (documents.some((document) => document.status === "failed")) {
    return { label: "部分资料处理失败", tone: "bg-red-500" };
  }
  if (documents.some((document) => document.status === "pending" || document.status === "processing")) {
    return { label: "正在建立索引", tone: "animate-pulse bg-amber-500" };
  }
  return { label: "已建立索引", tone: "bg-emerald-500" };
}

function fileTypeStyle(fileType: string) {
  if (fileType === "pdf") return "bg-red-500";
  if (fileType === "md" || fileType === "markdown") return "bg-emerald-600";
  if (fileType === "docx") return "bg-blue-600";
  if (fileType === "epub") return "bg-orange-500";
  if (["png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"].includes(fileType)) {
    return "bg-violet-600";
  }
  return "bg-slate-600";
}

export function KnowledgePage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selectedKnowledgeBaseId, setSelectedKnowledgeBaseId] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);

  const knowledgeQuery = useQuery({
    queryKey: ["knowledge-bases"],
    queryFn: ({ signal }) => listKnowledgeBases(signal),
  });
  const documentsQuery = useQuery({
    queryKey: ["documents"],
    queryFn: ({ signal }) => listDocuments(undefined, signal),
    refetchInterval: (query) =>
      query.state.data?.some(
        (document) => document.status === "pending" || document.status === "processing",
      )
        ? 1500
        : false,
  });

  useEffect(() => {
    const items = knowledgeQuery.data ?? [];
    if (items.length === 0) {
      setSelectedKnowledgeBaseId(null);
      return;
    }
    if (!items.some((item) => item.id === selectedKnowledgeBaseId)) {
      setSelectedKnowledgeBaseId(items[0].id);
    }
  }, [knowledgeQuery.data, selectedKnowledgeBaseId]);

  const filteredKnowledgeBases =
    knowledgeQuery.data?.filter((item) =>
      item.name.toLowerCase().includes(search.trim().toLowerCase()),
    ) ?? [];
  const selectedKnowledgeBase =
    knowledgeQuery.data?.find((item) => item.id === selectedKnowledgeBaseId) ?? null;
  const selectedDocuments =
    documentsQuery.data?.filter(
      (document) => document.knowledge_base_id === selectedKnowledgeBaseId,
    ) ?? [];
  const chunkTotal = selectedDocuments.reduce(
    (total, document) => total + document.chunk_count,
    0,
  );
  const index = indexStatus(selectedDocuments);

  const createMutation = useMutation({
    mutationFn: () => createKnowledgeBase({ name, description }),
    onSuccess: async (created) => {
      setName("");
      setDescription("");
      setCreateOpen(false);
      setSelectedKnowledgeBaseId(created.id);
      await queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] });
    },
  });

  const deleteKnowledgeMutation = useMutation({
    mutationFn: deleteKnowledgeBase,
    onSuccess: async (_, deletedId) => {
      if (selectedKnowledgeBaseId === deletedId) setSelectedKnowledgeBaseId(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] }),
        queryClient.invalidateQueries({ queryKey: ["documents"] }),
      ]);
    },
  });

  const [uploadProgress, setUploadProgress] = useState<{
    done: number;
    total: number;
    name: string;
  } | null>(null);
  const [uploadErrors, setUploadErrors] = useState<string[]>([]);

  const deleteDocumentMutation = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
  });

  function closeCreateDialog() {
    setCreateOpen(false);
    setName("");
    setDescription("");
    createMutation.reset();
  }

  function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (name.trim()) createMutation.mutate();
  }

  async function uploadFiles(files: File[]) {
    if (!selectedKnowledgeBaseId || files.length === 0 || uploadProgress) return;
    const knowledgeBaseId = selectedKnowledgeBaseId;
    setUploadErrors([]);
    for (let index = 0; index < files.length; index += 1) {
      const file = files[index];
      setUploadProgress({ done: index, total: files.length, name: file.name });
      try {
        await uploadDocument(knowledgeBaseId, file);
      } catch (error) {
        const reason = error instanceof Error ? error.message : "上传失败";
        setUploadErrors((previous) => [...previous, `${file.name}：${reason}`]);
      }
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
    }
    setUploadProgress(null);
    await queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] });
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    const files = Array.from(event.dataTransfer.files);
    if (files.length > 0) void uploadFiles(files);
  }

  return (
    <>
      <section className="animate-fade-in flex h-full min-h-0">
        <aside className="flex w-[300px] shrink-0 flex-col border-r bg-background">
          <div className="border-b px-4 py-4">
            <h1 className="text-xl font-semibold tracking-tight">知识库</h1>
            <p className="mt-1 text-xs text-muted-foreground">先选择现有知识库，再管理资料</p>

            <label className="relative mt-4 block">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="搜索知识库"
                className="h-10 w-full rounded-xl border bg-background pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-ring"
              />
            </label>
          </div>

          <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-3">
            <button
              type="button"
              onClick={() => setCreateOpen(true)}
              className="flex w-full items-center gap-3 rounded-xl border border-dashed px-3 py-3 text-left text-sm font-medium text-primary transition-colors hover:bg-primary/5"
            >
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
                <Plus className="h-4 w-4" />
              </span>
              新建知识库
            </button>

            <div className="my-3 h-px bg-border" />

            {knowledgeQuery.isPending ? (
              <p className="px-2 py-3 text-sm text-muted-foreground">正在加载……</p>
            ) : null}
            {knowledgeQuery.error ? (
              <p className="px-2 py-3 text-sm text-red-600">{knowledgeQuery.error.message}</p>
            ) : null}
            {!knowledgeQuery.isPending && knowledgeQuery.data?.length === 0 ? (
              <p className="px-2 py-4 text-sm text-muted-foreground">
                还没有知识库，点击上方按钮新建。
              </p>
            ) : null}
            {knowledgeQuery.data?.length && filteredKnowledgeBases.length === 0 ? (
              <p className="px-2 py-3 text-sm text-muted-foreground">没有匹配的知识库。</p>
            ) : null}

            {filteredKnowledgeBases.map((knowledgeBase) => {
              const count =
                documentsQuery.data?.filter(
                  (document) => document.knowledge_base_id === knowledgeBase.id,
                ).length ?? 0;
              const active = knowledgeBase.id === selectedKnowledgeBaseId;
              return (
                <button
                  key={knowledgeBase.id}
                  type="button"
                  onClick={() => setSelectedKnowledgeBaseId(knowledgeBase.id)}
                  className={cn(
                    "w-full rounded-xl border px-3 py-3 text-left transition-colors",
                    active
                      ? "border-primary/25 bg-primary/10 text-primary"
                      : "border-transparent hover:bg-muted",
                  )}
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={cn(
                        "flex h-9 w-9 items-center justify-center rounded-lg",
                        active ? "bg-primary text-primary-foreground" : "bg-muted",
                      )}
                    >
                      <BookOpen className="h-4 w-4" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium">{knowledgeBase.name}</span>
                      <span className="mt-0.5 block text-xs text-muted-foreground">
                        {count} 份资料
                      </span>
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </aside>

        <div className="min-w-0 flex-1 overflow-y-auto bg-[#faf9f4] p-5 lg:p-8">
          {!selectedKnowledgeBase ? (
            <div className="flex h-full items-center justify-center">
              <Card className="border-dashed p-10 text-center">
                <BookOpen className="mx-auto h-7 w-7 text-muted-foreground" />
                <p className="mt-3 text-sm text-muted-foreground">
                  选择或新建一个知识库后，可在这里管理资料。
                </p>
              </Card>
            </div>
          ) : (
            <div className="mx-auto max-w-4xl">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">
                    当前知识库
                  </p>
                  <h2 className="mt-2 text-2xl font-semibold tracking-tight">
                    {selectedKnowledgeBase.name}
                  </h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {selectedKnowledgeBase.description || "尚未填写知识库说明"}
                  </p>
                  <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground">
                    <span>{selectedDocuments.length} 份资料</span>
                    <span>{chunkTotal} 个知识片段</span>
                    <span className="inline-flex items-center gap-2">
                      <span className={cn("h-2 w-2 rounded-full", index.tone)} />
                      {index.label}
                    </span>
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Button
                    size="sm"
                    onClick={() =>
                      navigate(
                        `/admin/chat?knowledge_base_id=${encodeURIComponent(selectedKnowledgeBase.id)}`,
                      )
                    }
                  >
                    <MessageCircleQuestion className="h-4 w-4" />
                    问答
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={deleteKnowledgeMutation.isPending}
                    onClick={() => deleteKnowledgeMutation.mutate(selectedKnowledgeBase.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                    删除知识库
                  </Button>
                </div>
              </div>

              <div
                className={cn(
                  "mt-6 flex min-h-[132px] items-center justify-between gap-5 rounded-2xl border border-dashed bg-white/75 px-6 py-5 transition-colors",
                  dragging && "border-primary bg-primary/5",
                )}
                onDragEnter={(event) => {
                  event.preventDefault();
                  setDragging(true);
                }}
                onDragOver={(event) => event.preventDefault()}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
              >
                <div className="flex min-w-0 items-center gap-4">
                  <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                    <UploadCloud className="h-5 w-5" />
                  </span>
                  <div>
                    <p className="text-sm font-medium">添加资料</p>
                    <p className="mt-1 text-xs leading-5 text-muted-foreground">
                      将 PDF、Word、EPUB、Markdown、图片等资料拖到这里（支持多选批量上传），或点击右侧按钮
                    </p>
                  </div>
                </div>
                <label className="shrink-0 cursor-pointer">
                  <span className="inline-flex h-10 items-center gap-2 rounded-xl bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90">
                    {uploadProgress ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        {uploadProgress.done + 1}/{uploadProgress.total}
                      </>
                    ) : (
                      <Plus className="h-4 w-4" />
                    )}
                    {uploadProgress ? "上传中" : "添加资料"}
                  </span>
                  <input
                    type="file"
                    multiple
                    accept=".pdf,.txt,.md,.markdown,.docx,.epub,.png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff"
                    className="sr-only"
                    onChange={(event) => {
                      const files = Array.from(event.target.files ?? []);
                      if (files.length > 0) void uploadFiles(files);
                      event.target.value = "";
                    }}
                  />
                </label>
              </div>

              {uploadProgress ? (
                <p className="mt-3 text-xs text-muted-foreground">
                  正在上传 {uploadProgress.name}（{uploadProgress.done + 1}/{uploadProgress.total}），解析与索引会在后台自动进行
                </p>
              ) : null}
              {uploadErrors.length > 0 ? (
                <div className="mt-3 space-y-1">
                  {uploadErrors.map((message) => (
                    <p key={message} className="text-sm text-red-600">
                      {message}
                    </p>
                  ))}
                </div>
              ) : null}
              {documentsQuery.error ? (
                <p className="mt-3 text-sm text-red-600">{documentsQuery.error.message}</p>
              ) : null}

              <div className="mt-6">
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="text-sm font-semibold">资料</h3>
                  <span className="text-xs text-muted-foreground">{selectedDocuments.length} 项</span>
                </div>

                {selectedDocuments.length === 0 ? (
                  <Card className="border-dashed p-7 text-center text-sm text-muted-foreground">
                    还没有资料，先添加一份吧。
                  </Card>
                ) : null}

                <div className="space-y-2">
                  {selectedDocuments.map((document) => (
                    <Card
                      key={document.id}
                      className="group flex cursor-pointer items-center justify-between gap-4 p-4 transition-all hover:-translate-y-0.5 hover:shadow-md"
                      onClick={() => setSelectedDocument(document)}
                    >
                      <div className="flex min-w-0 items-center gap-3">
                        <span
                          className={cn(
                            "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-[10px] font-bold uppercase text-white",
                            fileTypeStyle(document.file_type),
                          )}
                        >
                          {document.file_type}
                        </span>
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium">{document.filename}</p>
                          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                            <span className={cn("rounded-full px-2 py-0.5 font-medium", statusStyles[document.status])}>
                              {statusLabels[document.status]}
                            </span>
                            <span>{formatFileSize(document.file_size)}</span>
                            <span>{document.chunk_count} 个知识片段</span>
                          </div>
                          {document.error_message ? (
                            <p className="mt-1 text-xs text-red-600">{document.error_message}</p>
                          ) : null}
                        </div>
                      </div>
                      <div className="flex shrink-0 items-center gap-1">
                        <span className="hidden text-xs text-muted-foreground group-hover:block">
                          查看
                        </span>
                        <Button
                          variant="ghost"
                          size="icon"
                          aria-label={`删除 ${document.filename}`}
                        disabled={deleteDocumentMutation.isPending}
                          onClick={(event) => {
                            event.stopPropagation();
                            deleteDocumentMutation.mutate(document.id);
                          }}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </Card>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      {selectedDocument ? (
        <>
          <button
            type="button"
            className="fixed inset-0 z-40 bg-black/20"
            onClick={() => setSelectedDocument(null)}
            aria-label="关闭文档详情遮罩"
          />
          <DocumentDetailDrawer
            document={selectedDocument}
            deleting={deleteDocumentMutation.isPending}
            onClose={() => setSelectedDocument(null)}
            onDelete={() =>
              deleteDocumentMutation.mutate(selectedDocument.id, {
                onSuccess: () => setSelectedDocument(null),
              })
            }
          />
        </>
      ) : null}

      {createOpen ? (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4">
          <button
            type="button"
            className="absolute inset-0 bg-black/25 backdrop-blur-[2px]"
            onClick={closeCreateDialog}
            aria-label="关闭新建知识库弹窗"
          />
          <Card
            role="dialog"
            aria-modal="true"
            aria-label="新建知识库"
            className="animate-slide-up relative z-10 w-full max-w-md p-6 shadow-2xl"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold">新建知识库</h2>
                <p className="mt-1 text-sm text-muted-foreground">给知识库起个容易找到的名字</p>
              </div>
              <Button variant="ghost" size="icon" onClick={closeCreateDialog} aria-label="关闭">
                <X className="h-4 w-4" />
              </Button>
            </div>
            <form className="mt-6 space-y-4" onSubmit={handleCreate}>
              <label className="grid gap-2 text-sm">
                <span>名称</span>
                <input
                  required
                  autoFocus
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="例如：AI 技术"
                  className="h-10 rounded-xl border bg-background px-3 outline-none focus:ring-2 focus:ring-ring"
                />
              </label>
              <label className="grid gap-2 text-sm">
                <span>描述</span>
                <textarea
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  placeholder="例如：我的 AI 学习资料"
                  rows={3}
                  className="resize-none rounded-xl border bg-background px-3 py-2 outline-none focus:ring-2 focus:ring-ring"
                />
              </label>
              {createMutation.error ? (
                <p className="text-sm text-red-600">{createMutation.error.message}</p>
              ) : null}
              <div className="flex justify-end gap-2">
                <Button type="button" variant="ghost" onClick={closeCreateDialog}>
                  取消
                </Button>
                <Button type="submit" disabled={createMutation.isPending || !name.trim()}>
                  {createMutation.isPending ? "创建中……" : "创建"}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      ) : null}
    </>
  );
}
