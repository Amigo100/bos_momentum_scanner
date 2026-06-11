import { getSignals, getWeeks, getCurrentISOWeek } from "@/lib/data";
import { ScannerDashboard } from "@/components/ScannerDashboard";

export const dynamic = "force-dynamic";

export default function ScannerPage() {
  const signals = getSignals();
  const weeks = getWeeks();
  const currentWeek = getCurrentISOWeek();

  return <ScannerDashboard initialSignals={signals} weeks={weeks} currentWeek={currentWeek} />;
}
