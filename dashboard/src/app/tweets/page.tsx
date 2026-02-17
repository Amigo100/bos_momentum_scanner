import { getEnrichedTweets, getLiveWorkflowSummary } from "@/lib/data";
import { TweetDashboard } from "@/components/TweetDashboard";

export const dynamic = "force-dynamic";

export default function TweetsPage() {
  const data = getEnrichedTweets();
  const workflowSummary = getLiveWorkflowSummary();
  return <TweetDashboard data={data} workflowSummary={workflowSummary} />;
}
