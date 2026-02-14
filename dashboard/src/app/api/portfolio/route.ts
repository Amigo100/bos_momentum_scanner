import { NextResponse } from "next/server";
import { getPortfolio, getEquityCurve } from "@/lib/data";

export const dynamic = "force-dynamic";

export async function GET() {
  const positions = getPortfolio();
  const equityCurve = getEquityCurve();

  const open = positions.filter((p) => p.status === "OPEN");
  const closed = positions.filter((p) => p.status !== "OPEN");
  const winners = closed.filter((p) => p.pnl_pct > 0);
  const winRate = closed.length > 0 ? (winners.length / closed.length) * 100 : 0;
  const totalUnrealizedPnl = open.reduce((s, p) => s + p.pnl_pct, 0) / Math.max(open.length, 1);

  return NextResponse.json({
    positions,
    equityCurve,
    stats: {
      openCount: open.length,
      closedCount: closed.length,
      winRate: Math.round(winRate),
      totalUnrealizedPnl: Math.round(totalUnrealizedPnl * 10) / 10,
      nav: equityCurve.length > 0 ? equityCurve[equityCurve.length - 1].nav : 0,
      totalReturn: equityCurve.length > 0 ? equityCurve[equityCurve.length - 1].total_return_pct : 0,
      alpha: equityCurve.length > 0 ? equityCurve[equityCurve.length - 1].alpha_pct : 0,
    },
  });
}
