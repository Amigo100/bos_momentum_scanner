import { NextResponse } from "next/server";
import { getWorkflowStatus } from "@/lib/data";

export const dynamic = "force-dynamic";

export async function GET() {
  const health = getWorkflowStatus();
  return NextResponse.json({
    overall: health.overall,
    message: health.message,
  });
}
