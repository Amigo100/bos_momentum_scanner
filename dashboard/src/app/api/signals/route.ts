import { NextResponse } from "next/server";
import { getSignals, getDailySignals, getWeeks, getWeekSignals } from "@/lib/data";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const week = searchParams.get("week");

  if (week) {
    const signals = getWeekSignals(week);
    return NextResponse.json({ signals, week });
  }

  const signals = getSignals();
  const dailySignals = getDailySignals();
  const weeks = getWeeks();

  return NextResponse.json({ signals, dailySignals, weeks });
}
