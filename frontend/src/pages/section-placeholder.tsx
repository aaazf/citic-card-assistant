import { Card } from "@/components/ui/card";

type SectionPlaceholderProps = {
  title: string;
  description: string;
  phase: string;
};

export function SectionPlaceholder({ title, description, phase }: SectionPlaceholderProps) {
  return (
    <section className="mx-auto max-w-4xl px-8 py-10">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{description}</p>
      <Card className="mt-6 border-dashed p-8">
        <p className="text-sm text-muted-foreground">页面边界已建立，业务功能将在 {phase} 实现。</p>
      </Card>
    </section>
  );
}
