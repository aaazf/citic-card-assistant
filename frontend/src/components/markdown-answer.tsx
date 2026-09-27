import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import type { Citation } from "@/api/types";
import { sanitizeAnswerContent } from "@/lib/sanitize-answer";

type MarkdownAnswerProps = {
  content: string;
  citations?: Citation[];
  onCitation: (citation: Citation) => void;
};

export function MarkdownAnswer({ content, citations = [], onCitation }: MarkdownAnswerProps) {
  const linkedContent = sanitizeAnswerContent(content).replace(/\[(\d+)]/g, (marker, indexText) => {
    const index = Number(indexText) - 1;
    return citations[index] ? `[${marker}](#citation-${index + 1})` : marker;
  });

  return (
    <div className="markdown-body">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => {
            const match = /^#citation-(\d+)$/.exec(href ?? "");
            if (match) {
              const citation = citations[Number(match[1]) - 1];
              if (citation) {
                return (
                  <button
                    type="button"
                    className="citation-marker"
                    onClick={() => onCitation(citation)}
                    aria-label={`查看引用 ${match[1]}`}
                  >
                    {children}
                  </button>
                );
              }
            }
            return (
              <a href={href} target="_blank" rel="noreferrer">
                {children}
              </a>
            );
          },
        }}
      >
        {linkedContent}
      </ReactMarkdown>
    </div>
  );
}
