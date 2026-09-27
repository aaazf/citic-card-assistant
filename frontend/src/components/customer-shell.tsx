import { Phone } from "lucide-react";
import { Link, Outlet } from "react-router-dom";

import { CiticLogo } from "@/components/citic-logo";

export function CustomerShell() {
  return (
    <div className="flex h-screen flex-col overflow-hidden bg-muted/30">
      <header className="relative flex h-16 shrink-0 items-center justify-between bg-background/85 px-4 backdrop-blur sm:px-8">
        <span
          className="pointer-events-none absolute inset-x-0 bottom-0 h-[2px] bg-gradient-to-r from-[#E60012]/70 via-[#C8A45D]/80 to-[#C8A45D]/15"
          aria-hidden="true"
        />
        <div className="flex items-center gap-3">
          <CiticLogo className="h-9 w-9 drop-shadow-sm" />
          <div>
            <p className="text-sm font-semibold leading-tight">中信银行信用卡</p>
            <p className="text-xs leading-tight text-muted-foreground">客户服务</p>
          </div>
        </div>
        <a
          href="tel:95558"
          className="flex items-center gap-1.5 rounded-full border border-[#C8A45D]/50 bg-[#C8A45D]/10 px-3 py-1.5 text-xs font-medium text-[#8a6d3b] transition-all hover:-translate-y-px hover:bg-[#C8A45D]/20 hover:shadow-sm"
        >
          <Phone className="h-3.5 w-3.5" />
          人工服务 95558
        </a>
      </header>
      <main className="min-h-0 flex-1 overflow-hidden">
        <Outlet />
      </main>
      <footer className="flex h-9 shrink-0 items-center justify-center gap-4 border-t bg-background/80 px-4 text-xs text-muted-foreground">
        <span className="truncate">回答依据信用卡业务资料生成，重要事项请以官方解释为准</span>
        <Link
          to="/admin"
          className="shrink-0 underline-offset-2 hover:text-foreground hover:underline"
        >
          工作人员入口
        </Link>
      </footer>
    </div>
  );
}
