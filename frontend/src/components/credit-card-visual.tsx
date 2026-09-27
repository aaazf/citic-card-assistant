import { useRef, useState } from "react";

export function CreditCardVisual() {
  const cardRef = useRef<HTMLDivElement>(null);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });

  function handleMouseMove(event: React.MouseEvent<HTMLDivElement>) {
    const rect = cardRef.current?.getBoundingClientRect();
    if (!rect) return;
    const px = (event.clientX - rect.left) / rect.width - 0.5;
    const py = (event.clientY - rect.top) / rect.height - 0.5;
    setTilt({ x: px * 9, y: -py * 7 });
  }

  return (
    <div className="animate-float-soft">
      <div style={{ perspective: "900px" }}>
        <div
          ref={cardRef}
          onMouseMove={handleMouseMove}
          onMouseLeave={() => setTilt({ x: 0, y: 0 })}
          className="shine-button relative aspect-[8/5] w-full overflow-hidden rounded-3xl text-white shadow-2xl shadow-red-950/30 will-change-transform"
          style={{
            background:
              "linear-gradient(135deg, #f01425 0%, #c40d1c 38%, #8f0713 78%, #6d050e 100%)",
            transform: `rotateY(${tilt.x}deg) rotateX(${tilt.y}deg)`,
            transition: "transform 0.18s ease-out",
          }}
          role="img"
          aria-label="中信银行信用卡"
        >
          <div className="pointer-events-none absolute inset-0 rounded-3xl ring-1 ring-inset ring-white/20" />
          <div
            className="pointer-events-none absolute inset-x-0 top-0 h-1/2 rounded-t-3xl opacity-40"
            style={{
              background:
                "linear-gradient(180deg, rgba(255,255,255,0.22) 0%, transparent 100%)",
            }}
          />
          <div
            className="pointer-events-none absolute -right-16 -top-20 h-56 w-56 rounded-full opacity-30"
            style={{ background: "radial-gradient(circle, #C8A45D 0%, transparent 70%)" }}
          />
          <div
            className="pointer-events-none absolute -bottom-24 -left-10 h-64 w-64 rounded-full opacity-15"
            style={{ background: "radial-gradient(circle, #ffffff 0%, transparent 70%)" }}
          />
          <div
            className="pointer-events-none absolute inset-0 opacity-60"
            style={{
              background:
                "repeating-radial-gradient(circle at 108% -12%, rgba(255,255,255,0.07) 0 1.5px, transparent 1.5px 30px)",
            }}
          />

          <div className="relative flex h-full flex-col justify-between p-5 sm:p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-white/95 shadow-sm">
                  <img
                    src="/citic-logo.png"
                    alt=""
                    className="h-5 w-5 object-contain"
                  />
                </span>
                <div className="leading-tight">
                  <p className="text-sm font-semibold tracking-wide">中信银行</p>
                  <p className="text-[10px] tracking-widest text-white/70">CHINA CITIC BANK</p>
                </div>
              </div>
              <svg
                viewBox="0 0 24 24"
                className="h-5 w-5 text-white/70"
                fill="none"
                stroke="currentColor"
                strokeWidth={1.8}
                strokeLinecap="round"
                aria-hidden="true"
              >
                <path d="M6 8.5a5 5 0 0 1 0 7" />
                <path d="M9.5 6.5a8 8 0 0 1 0 11" />
                <path d="M13 4.5a11 11 0 0 1 0 15" />
              </svg>
            </div>

            <div className="relative h-9 w-12 overflow-hidden rounded-md border border-[#e8cd8f] bg-gradient-to-br from-[#f2ddab] via-[#e0bd76] to-[#C8A45D] shadow-inner">
              <span className="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-[#a8823f]/70" />
              <span className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-[#a8823f]/50" />
            </div>

            <div className="flex items-end justify-between">
              <p
                className="text-sm tracking-[0.3em] text-white/90"
                style={{
                  textShadow:
                    "0 1px 1px rgba(0,0,0,0.45), 0 -1px 1px rgba(255,255,255,0.22)",
                }}
              >
                **** **** **** 2026
              </p>
              <p className="text-[10px] font-medium tracking-[0.25em] text-[#e8cd8f]">
                CREDIT CARD
              </p>
            </div>
          </div>
        </div>
      </div>
      <div
        className="mx-auto mt-2 h-6 w-4/5 rounded-[100%] blur-md"
        style={{
          background:
            "radial-gradient(ellipse at center, rgba(122,6,16,0.35) 0%, transparent 70%)",
        }}
      />
    </div>
  );
}
