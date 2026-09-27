import {
  ArrowRight,
  BookOpenCheck,
  FileText,
  Search,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { CiticLogo } from "@/components/citic-logo";

type KnowledgeWelcomeProps = {
  onEnter: () => void;
};

export function KnowledgeWelcome({ onEnter }: KnowledgeWelcomeProps) {
  const [showInfo, setShowInfo] = useState(false);

  return (
    <section className="relative flex h-screen min-h-screen w-full overflow-x-hidden overflow-y-auto bg-[#fdf7f3] px-6 py-8 lg:px-12">
      <div className="pointer-events-none absolute -left-24 top-12 h-80 w-80 rounded-full bg-red-200/30 blur-3xl animate-gradient-drift" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-96 w-96 rounded-full bg-red-300/20 blur-3xl animate-gradient-drift [animation-delay:2s]" />

      <div className="relative mx-auto grid w-full max-w-7xl items-center gap-10 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="animate-slide-up">
          <div className="inline-flex items-center gap-2 rounded-full border border-red-200 bg-white/80 px-3 py-1.5 text-xs font-medium text-[#b3000e]">
            <Sparkles className="h-3.5 w-3.5" />
            中信银行信用卡 · 智能咨询
          </div>
          <h1 className="mt-6 text-4xl font-bold leading-tight tracking-tight text-slate-900 lg:text-5xl">
            中信银行
            <br />
            <span className="text-[#E60012]">信用卡智能咨询助手</span>
          </h1>
          <p className="mt-5 max-w-xl text-base leading-8 text-slate-600">
            年费、额度、还款、积分、账单……关于信用卡的疑问，我会依据官方业务资料为您解答，回答附带来源引用。
          </p>

          <div className="animate-slide-up mt-7 flex flex-wrap gap-3">
            <Button size="lg" className="shine-button" onClick={onEnter}>
              开始咨询
              <ArrowRight className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="lg" onClick={() => setShowInfo(true)}>
              查看功能
            </Button>
          </div>

          <div className="mt-9 grid gap-3 sm:grid-cols-3">
            <Feature icon={Search} title="业务资料作答" text="基于官方信用卡业务资料" />
            <Feature icon={BookOpenCheck} title="引用可追溯" text="回答附来源，可核对原文" />
            <Feature icon={ShieldCheck} title="答不上不硬答" text="依据不足时明确说明" />
          </div>
        </div>

        <div className="animate-fade-in relative hidden min-h-[520px] lg:block">
          <div className="animate-float-soft absolute left-4 top-10 z-10 [--float-rotate:-4deg]">
            <FloatingCard icon={FileText} title="快速检索" text="精准定位业务条款" />
          </div>
          <div className="animate-float-delayed absolute right-0 top-4 z-10 [--float-rotate:4deg]">
            <FloatingCard icon={Sparkles} title="智能回答" text="基于业务资料与引用" />
          </div>

          <Card className="animate-fade-in absolute inset-x-8 bottom-8 top-24 overflow-hidden rounded-[2rem] border-red-100 bg-white shadow-2xl shadow-red-950/10">
            <div className="flex items-center justify-between border-b px-5 py-4">
              <div className="flex items-center gap-2">
                <CiticLogo className="h-8 w-8" />
                <div>
                  <p className="text-sm font-semibold">信用卡智能咨询</p>
                  <p className="text-[11px] text-muted-foreground">业务资料已就绪</p>
                </div>
              </div>
              <span className="h-2.5 w-2.5 rounded-full bg-[#E60012]" />
            </div>
            <div className="space-y-4 p-5">
              <div className="ml-auto max-w-[75%] rounded-2xl rounded-tr-md bg-[#fdeeee] px-4 py-3 text-sm">
                忘记还款了怎么办？
              </div>
              <div className="flex gap-3">
                <CiticLogo className="mt-1 h-8 w-8" />
                <div className="rounded-2xl rounded-tl-md border bg-[#fbfaf5] p-4 text-sm leading-7">
                  我会先检索信用卡业务资料，再基于命中的条款为您解答，并标注来源引用。
                  <div className="mt-3 flex gap-2 text-[11px] text-[#b3000e]">
                    <span className="rounded-full bg-[#fdeeee] px-2 py-0.5">引用 1</span>
                    <span className="rounded-full bg-[#fdeeee] px-2 py-0.5">引用 2</span>
                  </div>
                </div>
              </div>
            </div>
            <div className="absolute inset-x-5 bottom-5 flex items-center rounded-2xl border bg-white p-2 pl-4 text-xs text-muted-foreground">
              请输入您的信用卡问题……
              <span className="ml-auto flex h-8 w-8 items-center justify-center rounded-xl bg-[#E60012] text-white">
                ↑
              </span>
            </div>
          </Card>
        </div>
      </div>

      {showInfo ? (
        <div className="fixed inset-0 z-[80] flex items-center justify-center p-4">
          <button
            type="button"
            className="absolute inset-0 bg-black/25"
            onClick={() => setShowInfo(false)}
            aria-label="关闭功能介绍"
          />
          <Card className="animate-slide-up relative z-10 w-full max-w-lg p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold">我能为您解答什么？</h2>
                <p className="mt-1 text-sm text-muted-foreground">只依据官方业务资料回答，不确定时会明说。</p>
              </div>
              <Button variant="ghost" size="icon" onClick={() => setShowInfo(false)} aria-label="关闭">
                <X className="h-4 w-4" />
              </Button>
            </div>
            <ul className="mt-5 space-y-3 text-sm text-muted-foreground">
              <li>• 申请、激活、额度、账单、还款、积分、费用规则等常见问题。</li>
              <li>• 回答附带来源引用，可打开业务资料原文核对。</li>
              <li>• 资料中没有依据时会明确告知，不编造规则。</li>
              <li>• 涉及资金与合约的重要事项，请以银行官方解释为准。</li>
            </ul>
          </Card>
        </div>
      ) : null}
    </section>
  );
}

function Feature({
  icon: Icon,
  title,
  text,
}: {
  icon: typeof Search;
  title: string;
  text: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border bg-white/70 p-3 transition-all hover:-translate-y-0.5 hover:shadow-md">
      <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#fdeeee] text-[#b3000e]">
        <Icon className="h-5 w-5" />
      </span>
      <span>
        <span className="block text-sm font-medium">{title}</span>
        <span className="mt-0.5 block text-xs text-muted-foreground">{text}</span>
      </span>
    </div>
  );
}

function FloatingCard({
  icon: Icon,
  title,
  text,
}: {
  icon: typeof FileText;
  title: string;
  text: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border bg-white/90 p-4 shadow-xl shadow-red-950/5 backdrop-blur">
      <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#fdeeee] text-[#b3000e]">
        <Icon className="h-5 w-5" />
      </span>
      <span>
        <span className="block text-sm font-semibold">{title}</span>
        <span className="text-xs text-muted-foreground">{text}</span>
      </span>
    </div>
  );
}
