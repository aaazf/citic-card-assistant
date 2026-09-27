import { describe, expect, it } from "vitest";

import { extractKeyFacts } from "@/lib/key-facts";

describe("extractKeyFacts", () => {
  it("提取账单日、还款日、宽限期等关键信息", () => {
    const facts = extractKeyFacts(
      "您的账单日为每月 5 日，还款日为每月 25 日，宽限期为 3 天。" +
        "年费为 200 元，刷满 5 次可减免。",
    );

    expect(facts).toEqual([
      { label: "账单日", value: "5 日" },
      { label: "还款日", value: "25 日" },
      { label: "宽限期", value: "3 天" },
      { label: "年费", value: "200 元" },
    ]);
  });

  it("最多返回 4 条且同一标签去重", () => {
    const facts = extractKeyFacts(
      "账单日是 5 号，账单日也可能调整。还款日为 25 日，宽限期 3 天，免息期 20 天，年费 200 元。",
    );

    expect(facts).toHaveLength(4);
    expect(facts.filter((fact) => fact.label === "账单日")).toHaveLength(1);
  });

  it("普通回答不提取", () => {
    expect(extractKeyFacts("您好，请问有什么可以帮您？")).toEqual([]);
  });
});
