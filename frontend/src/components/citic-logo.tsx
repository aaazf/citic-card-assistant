import { cn } from "@/lib/utils";

export function CiticLogo({ className }: { className?: string }) {
  return (
    <img
      src="/citic-logo.png"
      alt="中信银行标志"
      className={cn("shrink-0 object-contain drop-shadow-sm", className)}
    />
  );
}
