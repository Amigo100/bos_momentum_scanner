import { getEnrichedTweets } from "@/lib/data";
import { TweetDashboard } from "@/components/TweetDashboard";

export const dynamic = "force-dynamic";

export default function TweetsPage() {
  const data = getEnrichedTweets();
  return <TweetDashboard data={data} />;
}
