export type KeyFact = { label: string; value: string };

const FACT_RULES: { label: string; pattern: RegExp }[] = [
  { label: "账单日", pattern: /账单日[^，。；：\n]{0,12}?(\d{1,2}\s*(?:日|号))/ },
  { label: "还款日", pattern: /还款日[^，。；：\n]{0,14}?(\d{1,2}\s*(?:日|号))/ },
  { label: "宽限期", pattern: /宽限期[^，。；：\n]{0,10}?(\d+\s*天)/ },
  { label: "免息期", pattern: /免息期[^，。；：\n]{0,12}?(\d+\s*天)/ },
  { label: "年费", pattern: /年费[^，。；：\n]{0,14}?(\d+(?:\.\d+)?\s*元)/ },
  { label: "日利率", pattern: /日利率[^，。；：\n]{0,10}?(\d+(?:\.\d+)?\s*%)/ },
  { label: "年利率", pattern: /年利率[^，。；：\n]{0,10}?(\d+(?:\.\d+)?\s*%)/ },
  {
    label: "最低还款",
    pattern: /最低还款[^，。；：\n]{0,14}?(\d+(?:\.\d+)?\s*(?:%|元))/,
  },
  {
    label: "取现手续费",
    pattern: /取现手续费[^，。；：\n]{0,14}?(\d+(?:\.\d+)?\s*(?:%|元))/,
  },
];

export function extractKeyFacts(content: string, limit = 4): KeyFact[] {
  const facts: KeyFact[] = [];
  for (const rule of FACT_RULES) {
    const match = rule.pattern.exec(content);
    if (match?.[1] && !facts.some((fact) => fact.label === rule.label)) {
      facts.push({ label: rule.label, value: match[1].trim() });
    }
    if (facts.length >= limit) break;
  }
  return facts;
}
