import { NextResponse } from "next/server";
import { getSubstackPosts, getWeeks } from "@/lib/data";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const week = searchParams.get("week") || undefined;

  const posts = getSubstackPosts(week);
  const weeks = getWeeks();

  return NextResponse.json({
    posts: posts.map((p) => ({
      ...p,
      html: p.html.substring(0, 100000), // cap for API
    })),
    weeks,
  });
}
