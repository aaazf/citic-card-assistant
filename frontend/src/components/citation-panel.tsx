import { useQuery } from "@tanstack/react-query";
import { FileText, Loader2, X } from "lucide-react";

import { getDocumentChunk } from "@/api/documents";
import type { Citation } from "@/api/types";
import { Button } from "@/components/ui/button";

type CitationPanelProps = {
  citation: Citation;
  onClose: () => void;
};

export function CitationPanel({ citation, onClose }: CitationPanelProps) {
  const chunkQuery = useQuery({
    queryKey: ["chunk", citation.document_id, citation.chunk_id],
    queryFn: ({ signal }) => getDocumentChunk(citation.document_id, citation.chunk_id, signal),
  });

  return (
    <aside className="animate-slide-up fixed inset-y-0 right-0 z-40 w-full max-w-[380px] shrink-0 overflow-y-auto border-l bg-[#fbfaf5] px-5 py-6 shadow-xl md:static md:z-auto md:shadow-none">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">资料原文</p>
          <h2 className="mt-2 break-words text-sm font-semibold">{citation.filename}</h2>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
            {citation.page ? (
              <span className="rounded-full bg-muted px-2 py-0.5 text-muted-foreground">
                第 {citation.page} 页
              </span>
            ) : null}
            <span
              className="rounded-full bg-primary/10 px-2 py-0.5 font-medium text-primary"
              title="语义相关度不是答案正确率或模型置信度"
            >
              {relevanceLabel(citation.score)} · {Math.round(citation.score * 100)}%
            </span>
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} aria-label="关闭引用面板">
          <X className="h-4 w-4" />
        </Button>
      </div>

      <p className="mt-3 text-xs leading-5 text-muted-foreground">
        相关度表示问题与原文的语义接近程度，不代表答案一定正确。
      </p>

      <div className="mt-3 rounded-2xl border bg-white p-5 shadow-sm">
        {chunkQuery.isPending ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            正在读取原文……
          </div>
        ) : null}
        {chunkQuery.error ? (
          <p className="text-sm text-red-600">{chunkQuery.error.message}</p>
        ) : null}
        {chunkQuery.data ? (
          <>
            <div className="mb-3 flex items-center gap-2 text-xs text-muted-foreground">
              <FileText className="h-3.5 w-3.5" />
              {String(chunkQuery.data.metadata.filename ?? citation.filename)}
            </div>
            <p className="whitespace-pre-wrap text-sm leading-6">{chunkQuery.data.content}</p>
          </>
        ) : null}
      </div>
    </aside>
  );
}


function relevanceLabel(score: number) {
  if (score >= 0.5) return "强相关";
  if (score >= 0.25) return "部分相关";
  return "弱相关";
}
