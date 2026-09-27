import {
  BarChart3,
  Bot,
  LibraryBig,
  Menu,
  MessagesSquare,
  PanelLeftClose,
  PanelLeftOpen,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";

import { HealthBadge } from "@/components/health-badge";
import { CiticLogo } from "@/components/citic-logo";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/admin/knowledge", label: "知识库管理", icon: LibraryBig },
  { to: "/admin/conversations", label: "会话记录", icon: MessagesSquare },
  { to: "/admin/chat", label: "测试问答", icon: Bot },
  { to: "/admin/eval", label: "评估报告", icon: BarChart3 },
  { to: "/admin/settings", label: "模型设置", icon: SlidersHorizontal },
];

export function AdminShell() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    function handleShortcut(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "b") {
        event.preventDefault();
        setCollapsed((current) => !current);
      }
      if (event.key === "Escape") setMobileOpen(false);
    }
    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-muted/30">
      {mobileOpen ? (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-black/30 md:hidden"
          onClick={() => setMobileOpen(false)}
          aria-label="关闭导航遮罩"
        />
      ) : null}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-[280px] flex-col border-r bg-background px-4 py-5 transition-[width,transform] duration-200 md:static md:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
          collapsed ? "md:w-20" : "md:w-[280px]",
        )}
      >
        <div className={cn("mb-8 flex items-center gap-2 px-1", collapsed && "md:justify-center")}>
          <CiticLogo className="h-10 w-10 rounded-2xl" />
          <div className={cn("min-w-0 flex-1", collapsed && "md:hidden")}>
            <p className="truncate text-base font-semibold">中信信用卡</p>
            <p className="mt-0.5 truncate text-xs text-muted-foreground">智能咨询工作台</p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setMobileOpen(false)}
            aria-label="关闭侧栏"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        <nav className="space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              title={collapsed ? label : undefined}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-xl px-4 py-3 text-[15px] text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                  isActive && "bg-primary/10 font-medium text-primary",
                  collapsed && "md:justify-center md:px-2",
                )
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className={cn(collapsed && "md:hidden")}>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto hidden space-y-2 md:block">
          <div className={cn(collapsed && "md:hidden")}>
            <Link
              to="/"
              className="block rounded-xl px-4 py-2 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              返回客户端
            </Link>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-center"
            onClick={() => setCollapsed((current) => !current)}
            aria-label={collapsed ? "展开侧栏" : "收起侧栏"}
          >
            {collapsed ? (
              <PanelLeftOpen className="h-4 w-4" />
            ) : (
              <>
                <PanelLeftClose className="h-4 w-4" />
                收起侧栏
              </>
            )}
          </Button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-[72px] items-center justify-between border-b bg-background px-4 sm:px-7">
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setMobileOpen(true)}
            aria-label="打开侧栏"
          >
            <Menu className="h-5 w-5" />
          </Button>
          <div className="hidden text-sm font-medium text-muted-foreground md:block">
            信用卡智能咨询 · 工作台
          </div>
          <HealthBadge />
        </header>
        <main className="min-h-0 flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
