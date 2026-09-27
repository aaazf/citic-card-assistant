import { describe, expect, it } from "vitest";

import { sanitizeAnswerContent } from "./sanitize-answer";

describe("sanitizeAnswerContent", () => {
  it("strips br tags emitted inside table cells", () => {
    expect(sanitizeAnswerContent("15%（指定商户）<br>1%（普通渠道）")).toBe(
      "15%（指定商户） 1%（普通渠道）",
    );
  });

  it("handles self-closing and uppercase variants", () => {
    expect(sanitizeAnswerContent("a<br/>b<BR />c")).toBe("a b c");
  });

  it("leaves normal markdown untouched", () => {
    expect(sanitizeAnswerContent("| 列 | 值 |\n| - | - |\n| a | b |")).toContain("| a | b |");
  });
});
