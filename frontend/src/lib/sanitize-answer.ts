export function sanitizeAnswerContent(content: string): string {
  return content.replace(/<br\s*\/?>/gi, " ");
}
