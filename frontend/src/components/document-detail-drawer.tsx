import { useQuery } from "@tanstack/react-query";
import { FileText, Loader2, Trash2, X } from "lucide-react";

import {
  documentContentUrl,
  getDocument,
  getDocumentText,
  listDocumentChunks,
} from "@/api/documents";
import type { Document, DocumentStatus } from "@/api/types";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const statusLabels: Record<DocumentStatus, string> = {
  pending: "等待处理",
  processing: "正在解析并建立索引",
  ready: "已建立索引",
  failed: "处理失败",
};

const IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"];

type DocumentDetailDrawerProps = {
  document: Document;
  deleting?: boolean;
  onClose: () => void;
  onDelete: () => void;
};

export function DocumentDetailDrawer({
  document,
  deleting,
  onClose,
  onDelete,
}: DocumentDetailDrawerProps) {
  const detailQuery = useQuery({
    queryKey: ["document", document.id],
    queryFn: ({ signal }) => getDocument(document.id, signal),
  });
  const chunksQuery = useQuery({
    queryKey: ["document", document.id, "chunks"],
    queryFn: ({ signal }) => listDocumentChunks(document.id, signal),
  });
  const current = detailQuery.data ?? document;
  const textPreview = ["txt", "md", "markdown"].includes(current.file_type.toLowerCase());
  const textQuery = useQuery({
    queryKey: ["document", document.id, "text"],
    queryFn: ({ signal }) => getDocumentText(document.id, signal),
    enabled: textPreview,
  });

  return (
    <aside className="fixed inset-y-0 right-0 z-50 flex w-full max-w-[560px] flex-col overflow-hidden border-l bg-[#fbfaf5] shadow-2xl">
      <div className="flex items-start justify-between gap-4 border-b px-5 py-5">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-primary">文档详情</p>
          <h2 className="mt-2 break-words text-base font-semibold">{current.filename}</h2>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span className={cn("rounded-full px-2 py-0.5 font-medium", statusTone(current.status))}>
              {statusLabels[current.status]}
            </span>
            <span className="uppercase">{current.file_type}</span>
            <span>{formatFileSize(current.file_size)}</span>
            <span>{current.chunk_count} 个知识片段</span>
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} aria-label="关闭文档详情">
          <X className="h-4 w-4" />
        </Button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-5">
        <section>
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold">原文预览</h3>
            <a
              href={documentContentUrl(current.id)}
              target="_blank"
              rel="noreferrer"
              className="text-xs font-medium text-primary hover:underline"
            >
              在新窗口打开
            </a>
          </div>
          <div className="mt-3 overflow-hidden rounded-2xl border bg-white">
            {current.file_type.toLowerCase() === "pdf" ? (
              <iframe
                title={`${current.filename} 预览`}
                src={documentContentUrl(current.id)}
                className="h-[340px] w-full"
              />
            ) : IMAGE_EXTENSIONS.includes(current.file_type.toLowerCase()) ? (
              <img
                src={documentContentUrl(current.id)}
                alt={current.filename}
                className="max-h-[420px] w-full object-contain"
              />
            ) : ["docx", "epub"].includes(current.file_type.toLowerCase()) ? (
              <div className="p-6 text-center text-sm text-muted-foreground">
                {current.file_type.toLowerCase() === "docx" ? "Word" : "EPUB"}{" "}
                文档的文字已提取并建立索引。可以查看下方知识片段，或在新窗口打开原始文件。
              </div>
            ) : textQuery.isPending ? (
              <div className="flex h-48 items-center justify-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                正在读取原文……
              </div>
            ) : textQuery.error ? (
              <p className="p-4 text-sm text-red-600">{textQuery.error.message}</p>
            ) : (
              <pre className="max-h-[420px] overflow-auto whitespace-pre-wrap p-4 text-sm leading-6">
                {textQuery.data}
              </pre>
            )}
          </div>
        </section>

        <section className="mt-6">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold">知识片段</h3>
            <span className="text-xs text-muted-foreground">
              {chunksQuery.data?.length ?? current.chunk_count} 个
            </span>
          </div>
          <div className="mt-3 space-y-2">
            {chunksQuery.isPending ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                正在读取片段……
              </div>
            ) : null}
            {chunksQuery.error ? (
              <p className="text-sm text-red-600">{chunksQuery.error.message}</p>
            ) : null}
            {chunksQuery.data?.map((chunk) => (
              <details key={chunk.chunk_id} className="rounded-xl border bg-white p-3">
                <summary className="cursor-pointer text-sm font-medium">
                  片段 {Number(chunk.metadata.chunk_index ?? 0) + 1}
                  {chunk.metadata.page ? ` · 第 ${chunk.metadata.page} 页` : ""}
                </summary>
                <p className="mt-3 whitespace-pre-wrap border-t pt-3 text-sm leading-6 text-muted-foreground">
                  {chunk.content}
                </p>
              </details>
            ))}
          </div>
        </section>
      </div>

      <div className="border-t bg-white/70 p-5">
        <Button variant="outline" className="w-full" disabled={deleting} onClick={onDelete}>
          <Trash2 className="h-4 w-4" />
          删除资料
        </Button>
      </div>
    </aside>
  );
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function statusTone(status: DocumentStatus) {
  if (status === "ready") return "bg-emerald-100 text-emerald-800";
  if (status === "failed") return "bg-red-100 text-red-700";
  if (status === "processing") return "bg-sky-100 text-sky-800";
  return "bg-amber-100 text-amber-800";
}
