import { NextResponse } from "next/server";
import { getTweets, getAllAccountTweets, getFailedTweets } from "@/lib/data";

export const dynamic = "force-dynamic";

export async function GET() {
  const { weekly, daily, live } = getTweets();
  const accounts = getAllAccountTweets();
  const failed = getFailedTweets();

  const all = [...weekly, ...daily, ...live];
  const posted = all.filter((t) => t.status === "posted" || t.posted);
  const pending = all.filter((t) => t.status === "pending" && !t.posted);
  const failedCount = all.filter((t) => t.status === "failed");

  return NextResponse.json({
    weekly,
    daily,
    live,
    accounts,
    failed,
    stats: {
      total: all.length,
      posted: posted.length,
      pending: pending.length,
      failed: failedCount.length + failed.length,
    },
  });
}
