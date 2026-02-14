import {
  getWorkflowStatus,
  getEnrichedTweets,
  getSignals,
  getPortfolio,
  enrichPositions,
  getEquityCurve,
  getSubstackContent,
  getFailedTweets,
  generateSystemLog,
} from "@/lib/data";
import { OverviewDashboard } from "@/components/OverviewDashboard";

export const dynamic = "force-dynamic";

export default function OverviewPage() {
  const health = getWorkflowStatus();
  const tweets = getEnrichedTweets();
  const signals = getSignals();
  const portfolio = getPortfolio();
  const enriched = enrichPositions(portfolio);
  const equityCurve = getEquityCurve();
  const substack = getSubstackContent();
  const failed = getFailedTweets();
  const systemLog = generateSystemLog();

  const open = enriched.filter((p) => p.status === "OPEN");
  const closed = enriched.filter((p) => p.status !== "OPEN");
  const latest = equityCurve.length > 0 ? equityCurve[equityCurve.length - 1] : null;

  return (
    <OverviewDashboard
      health={health}
      tweetStats={tweets.stats}
      rollingStats={tweets.rollingStats}
      dailyStats={tweets.dailyStats}
      failedTweetCount={failed.length}
      signals={signals}
      openPositions={open.length}
      closedPositions={closed.length}
      latestEquity={latest}
      substackContent={{
        newsletters: substack.newsletters.length,
        posts: substack.posts.length,
        notes: substack.notes.length,
        currentWeekPosts: substack.posts.filter((p) => p.week === "current").length,
      }}
      systemLog={systemLog}
    />
  );
}
