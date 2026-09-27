import { useQuery } from "@tanstack/react-query";

import { getModelStatus } from "@/api/health";
import { cn } from "@/lib/utils";

export function HealthBadge() {
  const query = useQuery({
    queryKey: ["model-status"],
    queryFn: ({ signal }) => getModelStatus(signal),
    retry: false,
    refetchInterval: 30_000,
  });

  const llmConnected =
    query.data?.providers.some((provider) => provider.kind === "llm" && provider.connected) ?? false;
  const label = query.isPending
    ? "检查接入状态"
    : llmConnected
      ? "模型已接入"
      : "模型未接入";

  return (
    <div className="flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs text-muted-foreground">
      <span
        className={cn(
          "h-2 w-2 rounded-full bg-red-500",
          llmConnected && "bg-emerald-500 animate-ring-pulse",
          query.isPending && "bg-amber-400",
        )}
      />
      {label}
    </div>
  );
}
