import path from "path";
import fs from "fs";
import Papa from "papaparse";

// ─── Data Resolution ───
// Local dev: reads from ../trades/ (live data)
// Vercel: reads from dashboard/data/ (bundled at build time)

function resolveTradesDir(): string {
  const bundledDir = path.join(process.cwd(), "data");
  const localDir = path.resolve(process.cwd(), "..", "trades");

  // Prefer bundled data (Vercel deployment)
  if (fs.existsSync(path.join(bundledDir, "manifest.json"))) {
    return bundledDir;
  }

  // Fallback to local trades/ (development)
  if (fs.existsSync(localDir)) {
    return localDir;
  }

  // Last resort: bundled dir even without manifest
  return bundledDir;
}

const TRADES_DIR = resolveTradesDir();

function readJSON(filePath: string): unknown | null {
  try {
    const full = path.isAbsolute(filePath) ? filePath : path.join(TRADES_DIR, filePath);
    const raw = fs.readFileSync(full, "utf-8");
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function readCSV(filePath: string): Record<string, string>[] {
  try {
    const full = path.isAbsolute(filePath) ? filePath : path.join(TRADES_DIR, filePath);
    const raw = fs.readFileSync(full, "utf-8");
    const result = Papa.parse(raw, { header: true, skipEmptyLines: true });
    return result.data as Record<string, string>[];
  } catch {
    return [];
  }
}

function readFile(filePath: string): string | null {
  try {
    const full = path.isAbsolute(filePath) ? filePath : path.join(TRADES_DIR, filePath);
    return fs.readFileSync(full, "utf-8");
  } catch {
    return null;
  }
}

// ─── Utilities ───

/** Returns the current ISO week string, e.g. "2026-W07" */
export function getCurrentISOWeek(): string {
  const now = new Date();
  const jan4 = new Date(now.getFullYear(), 0, 4);
  const dayOfWeek = jan4.getDay() || 7;
  const monday = new Date(jan4);
  monday.setDate(jan4.getDate() - dayOfWeek + 1);
  const diff = now.getTime() - monday.getTime();
  const weekNum = Math.floor(diff / (7 * 24 * 60 * 60 * 1000)) + 1;
  return `${now.getFullYear()}-W${String(weekNum).padStart(2, "0")}`;
}

// ─── Constants ───

const ALLOC_PER_POSITION = 5000; // £5,000 per position

// ─── Portfolio ───

export interface Position {
  ticker: string;
  status: string;
  entry_date: string;
  entry_price: number;
  exit_date: string;
  exit_price: number;
  highest_close: number;
  theme: string;
  tier: string;
  conviction: number;
  current_price: number;
  pnl_pct: number;
  pnl_usd: number;
  stop_level: number;
  days_held: number;
  distance_to_stop: number;
  stop_alert: boolean;
  position_dollars: number;
}

export interface LockStatus {
  active: boolean;
  trail?: string;       // "15%", "20%", "25%"
  lockLevel?: number;   // Actual stop price
  neededPct?: number;    // Distance to +50% threshold
  exitType?: string;     // "ExD" for underwater positions
}

export interface EnrichedPosition extends Position {
  invested: number;        // £5,000 per position
  currentValue: number;    // invested × (current / entry)
  pnlDollars: number;      // currentValue - invested
  lockStatus: LockStatus;
}

function calculateLockStatus(p: Position): LockStatus {
  const pnl = p.pnl_pct;
  const hc = p.highest_close;

  if (pnl >= 200) {
    return { active: true, trail: "15%", lockLevel: hc * 0.85 };
  }
  if (pnl >= 100) {
    return { active: true, trail: "20%", lockLevel: hc * 0.80 };
  }
  if (pnl >= 50) {
    return { active: true, trail: "25%", lockLevel: hc * 0.75 };
  }
  if (pnl >= 0) {
    return { active: false, neededPct: Math.round((50 - pnl) * 10) / 10 };
  }
  return { active: false, exitType: "ExD" };
}

export function getPortfolio(): Position[] {
  const rows = readCSV("portfolio_google_sheets.csv");
  if (rows.length === 0) {
    return readCSV("portfolio.csv").map((r) => ({
      ticker: r.ticker || "",
      status: r.status || "OPEN",
      entry_date: r.entry_date || "",
      entry_price: parseFloat(r.entry_price) || 0,
      exit_date: r.exit_date || "",
      exit_price: parseFloat(r.exit_price) || 0,
      highest_close: parseFloat(r.highest_close) || 0,
      theme: r.theme || "",
      tier: r.tier || "",
      conviction: parseInt(r.conviction) || 0,
      current_price: 0,
      pnl_pct: 0,
      pnl_usd: 0,
      stop_level: 0,
      days_held: 0,
      distance_to_stop: 0,
      stop_alert: false,
      position_dollars: parseFloat(r.position_dollars) || 0,
    }));
  }
  return rows.map((r) => ({
    ticker: r.ticker || "",
    status: r.status || "OPEN",
    entry_date: r.entry_date || "",
    entry_price: parseFloat(r.entry_price) || 0,
    exit_date: r.exit_date || "",
    exit_price: parseFloat(r.exit_price) || 0,
    highest_close: parseFloat(r.highest_close) || 0,
    theme: r.theme || "",
    tier: r.tier || "",
    conviction: parseInt(r.conviction) || 0,
    current_price: parseFloat(r.current_price) || 0,
    pnl_pct: parseFloat(r.pnl_pct) || 0,
    pnl_usd: parseFloat(r.pnl_usd) || 0,
    stop_level: parseFloat(r.stop_level) || 0,
    days_held: parseInt(r.days_held) || 0,
    distance_to_stop: parseFloat(r.distance_to_stop) || 0,
    stop_alert: r.stop_alert === "True" || r.stop_alert === "true",
    position_dollars: parseFloat(r.position_dollars) || 0,
  }));
}

export function enrichPositions(positions: Position[]): EnrichedPosition[] {
  return positions.map((p) => {
    const invested = ALLOC_PER_POSITION;
    const currentValue =
      p.status === "OPEN" && p.current_price > 0 && p.entry_price > 0
        ? invested * (p.current_price / p.entry_price)
        : p.status !== "OPEN" && p.exit_price > 0 && p.entry_price > 0
          ? invested * (p.exit_price / p.entry_price)
          : invested;
    const pnlDollars = currentValue - invested;

    return {
      ...p,
      invested,
      currentValue,
      pnlDollars,
      lockStatus: calculateLockStatus(p),
    };
  });
}

// ─── Equity Curve ───

export interface EquityPoint {
  date: string;
  nav: number;
  total_return_pct: number;
  spy_return_pct: number;
  qqq_return_pct: number;
  alpha_pct: number;
  open_count: number;
  spy_value: number;
  qqq_value: number;
}

export function getEquityCurve(): EquityPoint[] {
  return readCSV("equity_curve.csv").map((r) => ({
    date: r.date || "",
    nav: parseFloat(r.nav) || 0,
    total_return_pct: parseFloat(r.total_return_pct) || 0,
    spy_return_pct: parseFloat(r.spy_return_pct) || 0,
    qqq_return_pct: parseFloat(r.qqq_return_pct) || 0,
    alpha_pct: parseFloat(r.alpha_pct) || 0,
    open_count: parseInt(r.open_count) || 0,
    spy_value: parseFloat(r.spy_value) || 0,
    qqq_value: parseFloat(r.qqq_value) || 0,
  }));
}

// ─── Tweets ───

export interface Tweet {
  id: string;
  day: string;
  slot: number;
  time: string;
  text: string;
  category: string;
  scheduled_date: string;
  status: string;
  posted: boolean;
  char_count: number;
  mentioned_tickers: string[];
  chart_required: boolean;
  chart_path: string | null;
  timestamp: string;
  posted_at?: string;
  tweet_id?: string;
  account?: string;
  primary_ticker?: string;
  cost_usd?: number;
}

export interface EnrichedTweet extends Tweet {
  source: "weekly" | "daily" | "live";
  displayStatus: "upcoming" | "posted" | "expired" | "skipped" | "failed";
  sortKey: string;
}

// Slot time mapping for generating sortKey
const SLOT_TIMES: Record<number, string> = {
  1: "07:30", 2: "10:00", 3: "12:30", 4: "15:30", 5: "18:00", 6: "17:00", 7: "18:30",
};

function enrichTweet(tweet: Tweet, source: "weekly" | "daily" | "live"): EnrichedTweet {
  const today = new Date().toISOString().slice(0, 10);
  const isPosted = tweet.posted === true || tweet.status === "posted";

  let displayStatus: EnrichedTweet["displayStatus"];
  if (isPosted) {
    displayStatus = "posted";
  } else if (tweet.status === "skipped") {
    displayStatus = "skipped";
  } else if (tweet.status === "failed") {
    displayStatus = "failed";
  } else if (tweet.scheduled_date && tweet.scheduled_date >= today) {
    displayStatus = "upcoming";
  } else {
    displayStatus = "expired";
  }

  // Build sortKey from scheduled_date + time
  const time = tweet.time || SLOT_TIMES[tweet.slot] || "12:00";
  const date = tweet.scheduled_date || tweet.timestamp?.slice(0, 10) || "9999-99-99";
  const sortKey = `${date}T${time}`;

  return { ...tweet, source, displayStatus, sortKey };
}

function mapLiveAccountToNumber(account: string): "account1" | "account2" | "account3" {
  if (account === "variant_1") return "account1";
  if (account === "variant_2") return "account2";
  if (account === "variant_3") return "account3";
  return "account1";
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function normalizeLiveTweet(raw: any): Tweet {
  return {
    id: raw.id || "",
    day: "",
    slot: 0,
    time: raw.scheduled_time ? new Date(raw.scheduled_time).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false }) : "",
    text: raw.text || "",
    category: raw.category || "LIVE",
    scheduled_date: raw.scheduled_time ? raw.scheduled_time.slice(0, 10) : "",
    status: raw.status || "pending",
    posted: raw.status === "posted",
    char_count: (raw.text || "").length,
    mentioned_tickers: raw.primary_ticker ? [raw.primary_ticker] : [],
    chart_required: raw.chart_recommended || false,
    chart_path: raw.chart_path || null,
    timestamp: raw.generated_at || "",
    posted_at: raw.posted_at,
    tweet_id: raw.tweet_id,
    account: raw.account,
    primary_ticker: raw.primary_ticker,
    cost_usd: raw.cost_usd,
  };
}

export interface DailyStats {
  date: string;
  scheduled: number;
  posted: number;
  failed: number;
  expired: number;
  pending: number;
}

export interface RollingStats {
  account: string;
  posted: number;
  failed: number;
  expired: number;
  total: number;
  successRate: number;
}

export interface EnrichedTweetData {
  accounts: {
    account1: EnrichedTweet[];
    account2: EnrichedTweet[];
    account3: EnrichedTweet[];
  };
  nextTweet: EnrichedTweet | null;
  nextTweetByAccount: {
    account1: EnrichedTweet | null;
    account2: EnrichedTweet | null;
    account3: EnrichedTweet | null;
  };
  failed: FailedTweet[];
  stats: {
    posted: number;
    upcoming: number;
    expired: number;
    total: number;
  };
  dailyStats: Record<string, DailyStats>;
  rollingStats: Record<string, RollingStats>;
}

export function getEnrichedTweets(): EnrichedTweetData {
  // Load all queues
  const a1w = ((readJSON("content_queue.json") as Tweet[]) || []).map((t) => enrichTweet(t, "weekly"));
  const a1d = ((readJSON("daily_content_queue.json") as Tweet[]) || []).map((t) => enrichTweet(t, "daily"));
  const a2w = ((readJSON("content_queue_account2.json") as Tweet[]) || []).map((t) => enrichTweet(t, "weekly"));
  const a2d = ((readJSON("daily_content_queue_account2.json") as Tweet[]) || []).map((t) => enrichTweet(t, "daily"));
  const a3w = ((readJSON("content_queue_account3.json") as Tweet[]) || []).map((t) => enrichTweet(t, "weekly"));
  const a3d = ((readJSON("daily_content_queue_account3.json") as Tweet[]) || []).map((t) => enrichTweet(t, "daily"));

  // Live tweets - split by account
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const liveRaw = (readJSON("live_content_queue.json") as any[]) || [];
  const liveByAccount: { account1: EnrichedTweet[]; account2: EnrichedTweet[]; account3: EnrichedTweet[] } = {
    account1: [], account2: [], account3: [],
  };
  for (const raw of liveRaw) {
    const normalized = normalizeLiveTweet(raw);
    const enriched = enrichTweet(normalized, "live");
    const acct = mapLiveAccountToNumber(raw.account || "variant_1");
    liveByAccount[acct].push(enriched);
  }

  const accounts = {
    account1: [...a1w, ...a1d, ...liveByAccount.account1].sort((a, b) => b.sortKey.localeCompare(a.sortKey)),
    account2: [...a2w, ...a2d, ...liveByAccount.account2].sort((a, b) => b.sortKey.localeCompare(a.sortKey)),
    account3: [...a3w, ...a3d, ...liveByAccount.account3].sort((a, b) => b.sortKey.localeCompare(a.sortKey)),
  };

  // Find the next tweet to post — globally and per-account
  function findNextUpcoming(tweets: EnrichedTweet[]): EnrichedTweet | null {
    const upcoming = tweets
      .filter((t) => t.displayStatus === "upcoming")
      .sort((a, b) => a.sortKey.localeCompare(b.sortKey));
    return upcoming.length > 0 ? upcoming[0] : null;
  }

  const nextTweetByAccount = {
    account1: findNextUpcoming(accounts.account1),
    account2: findNextUpcoming(accounts.account2),
    account3: findNextUpcoming(accounts.account3),
  };

  const allUpcoming = [...accounts.account1, ...accounts.account2, ...accounts.account3]
    .filter((t) => t.displayStatus === "upcoming")
    .sort((a, b) => a.sortKey.localeCompare(b.sortKey));
  const nextTweet = allUpcoming.length > 0 ? allUpcoming[0] : null;

  // Stats
  const all = [...accounts.account1, ...accounts.account2, ...accounts.account3];
  const stats = {
    posted: all.filter((t) => t.displayStatus === "posted").length,
    upcoming: all.filter((t) => t.displayStatus === "upcoming").length,
    expired: all.filter((t) => t.displayStatus === "expired").length,
    total: all.length,
  };

  const failed = getFailedTweets();

  // ─── Daily Stats ───
  const dailyStats: Record<string, DailyStats> = {};
  for (const t of all) {
    const dateKey = t.scheduled_date || t.timestamp?.slice(0, 10) || "";
    if (!dateKey) continue;
    if (!dailyStats[dateKey]) {
      dailyStats[dateKey] = { date: dateKey, scheduled: 0, posted: 0, failed: 0, expired: 0, pending: 0 };
    }
    dailyStats[dateKey].scheduled++;
    if (t.displayStatus === "posted") dailyStats[dateKey].posted++;
    else if (t.displayStatus === "failed") dailyStats[dateKey].failed++;
    else if (t.displayStatus === "expired") dailyStats[dateKey].expired++;
    else dailyStats[dateKey].pending++;
  }

  // ─── 7-Day Rolling Stats per Account ───
  const today = new Date().toISOString().slice(0, 10);
  const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);

  function computeRolling(tweets: EnrichedTweet[], accountName: string): RollingStats {
    const recent = tweets.filter((t) => {
      const d = t.scheduled_date || "";
      return d >= sevenDaysAgo && d <= today;
    });
    const posted = recent.filter((t) => t.displayStatus === "posted").length;
    const failedCount = recent.filter((t) => t.displayStatus === "failed").length;
    const expired = recent.filter((t) => t.displayStatus === "expired").length;
    const total = recent.length;
    return {
      account: accountName,
      posted,
      failed: failedCount,
      expired,
      total,
      successRate: total > 0 ? Math.round((posted / total) * 100) : 0,
    };
  }

  const rollingStats: Record<string, RollingStats> = {
    account1: computeRolling(accounts.account1, "Account 1"),
    account2: computeRolling(accounts.account2, "Account 2"),
    account3: computeRolling(accounts.account3, "Account 3"),
  };

  return { accounts, nextTweet, nextTweetByAccount, failed, stats, dailyStats, rollingStats };
}

// Keep legacy functions for backward compatibility
export function getTweets(): { weekly: Tweet[]; daily: Tweet[]; live: Tweet[] } {
  const weekly = (readJSON("content_queue.json") as Tweet[]) || [];
  const daily = (readJSON("daily_content_queue.json") as Tweet[]) || [];
  const live = (readJSON("live_content_queue.json") as Tweet[]) || [];
  return { weekly, daily, live };
}

export function getAllAccountTweets(): { account1: Tweet[]; account2: Tweet[]; account3: Tweet[] } {
  const a1w = (readJSON("content_queue.json") as Tweet[]) || [];
  const a1d = (readJSON("daily_content_queue.json") as Tweet[]) || [];
  const a2w = (readJSON("content_queue_account2.json") as Tweet[]) || [];
  const a2d = (readJSON("daily_content_queue_account2.json") as Tweet[]) || [];
  const a3w = (readJSON("content_queue_account3.json") as Tweet[]) || [];
  const a3d = (readJSON("daily_content_queue_account3.json") as Tweet[]) || [];
  return {
    account1: [...a1w, ...a1d],
    account2: [...a2w, ...a2d],
    account3: [...a3w, ...a3d],
  };
}

// ─── Signals ───

export interface Signal {
  symbol: string;
  tier: string;
  price: number;
  beta: number;
  theme: string;
  theme_score: number;
  theme_verdict: string;
  final_decision: string;
  conviction: number;
  catalyst_summary: string;
  red_flag_level: string;
  bullish_factors: string[];
  risk_factors: string[];
  reasoning: string;
  // Optional fields present in various formats
  banker?: number;
  return_20d?: number;
  pure_play_score?: number;
  sector_status?: string;
  upside_potential?: string;
  action?: string;
  dd_verdict?: string;
  dd_conviction?: number;
  dd_position_size?: string;
  dd_key_catalyst?: string;
  dd_fatal_flaw?: string;
  momentum_4w?: number;
}

export interface ThemeData {
  name: string;
  rank: number;
  classification: string;
  composite_score: number;
  thesis_summary: string;
  key_catalysts: string[];
  theme_type?: string;
  momentum_score?: number;
  catalyst_score?: number;
  crowding_score?: number;
  runway_score?: number;
  valuation_regime?: string;
}

export interface HistoricalWinner {
  ticker: string;
  entry_price: number;
  current_price: number;
  pnl_pct: number;
  signal_date: string;
  theme: string;
}

export interface SignalsData {
  timestamp: string;
  timeframe?: string;
  entry_criteria?: string;
  exit_criteria?: string;
  stats: Record<string, number>;
  themes: ThemeData[];
  buy_signals: Signal[];
  sell_signals: Array<{ symbol: string; reason: string; price?: number; pnl_pct?: number }>;
  // Optional arrays present in various week formats
  pass_signals?: Signal[];
  consider_signals?: Signal[];
  assessed_signals?: Signal[];
  historical_winners?: HistoricalWinner[];
  big_wins?: HistoricalWinner[];
}

export function getSignals(): SignalsData | null {
  return readJSON("signals.json") as SignalsData | null;
}

export function getDailySignals(): unknown | null {
  return readJSON("daily_signals.json");
}

// ─── Substack ───

export interface SubstackPost {
  filename: string;
  title: string;
  html: string;
  week: string;
  size: number;
}

export interface Newsletter {
  html: string;
  week: string;
  size: number;
}

export interface SubstackNote {
  filename: string;
  title: string;
  content: string;
  week: string;
}

export interface SubstackContent {
  newsletters: Newsletter[];
  posts: SubstackPost[];
  notes: SubstackNote[];
}

const NOTE_TITLES: Record<string, string> = {
  tuesday_note: "Portfolio Pulse",
  thursday_note: "Trade Spotlight",
};

export interface SubstackContentResult extends SubstackContent {
  currentISOWeek: string;
}

export function getSubstackContent(week?: string): SubstackContentResult {
  const newsletters: Newsletter[] = [];
  const posts: SubstackPost[] = [];
  const notes: SubstackNote[] = [];
  const currentISOWeek = getCurrentISOWeek();

  // ─── Current week ───
  // Newsletter
  const currentNewsletter = path.join(TRADES_DIR, "current", "newsletter.html");
  if (fs.existsSync(currentNewsletter)) {
    const html = readFile(currentNewsletter) || "";
    const stat = fs.statSync(currentNewsletter);
    newsletters.push({ html, week: "current", size: stat.size });
  }

  // Posts
  const currentPostsDir = path.join(TRADES_DIR, "current", "substack_posts");
  if (fs.existsSync(currentPostsDir)) {
    for (const file of fs.readdirSync(currentPostsDir)) {
      if (file.endsWith(".html")) {
        const filePath = path.join(currentPostsDir, file);
        const html = readFile(filePath) || "";
        const stat = fs.statSync(filePath);
        posts.push({
          filename: file,
          title: file.replace(/_/g, " ").replace(".html", ""),
          html,
          week: "current",
          size: stat.size,
        });
      }
    }
  }

  // Notes
  const currentNotesDir = path.join(TRADES_DIR, "current", "substack_notes");
  if (fs.existsSync(currentNotesDir)) {
    for (const file of fs.readdirSync(currentNotesDir)) {
      if (file.endsWith(".md")) {
        const filePath = path.join(currentNotesDir, file);
        const content = readFile(filePath) || "";
        const baseName = file.replace(".md", "");
        notes.push({
          filename: file,
          title: NOTE_TITLES[baseName] || baseName.replace(/_/g, " "),
          content,
          week: "current",
        });
      }
    }
  }

  // ─── Week archives ───
  const weeksDir = path.join(TRADES_DIR, "weeks");
  if (fs.existsSync(weeksDir)) {
    const weeks = fs.readdirSync(weeksDir).filter((d) => d.startsWith("2026-W")).sort().reverse();
    for (const w of weeks) {
      if (week && w !== week && week !== "all") continue;
      // Skip current ISO week from archives to avoid duplication with current/ folder
      if (w === currentISOWeek && (!week || week === "all")) continue;

      // Newsletter
      const nPath = path.join(weeksDir, w, "newsletter.html");
      if (fs.existsSync(nPath)) {
        const html = readFile(nPath) || "";
        const stat = fs.statSync(nPath);
        newsletters.push({ html, week: w, size: stat.size });
      }

      // Posts
      const postsDir = path.join(weeksDir, w, "substack_posts");
      if (fs.existsSync(postsDir)) {
        for (const file of fs.readdirSync(postsDir)) {
          if (file.endsWith(".html")) {
            const filePath = path.join(postsDir, file);
            const html = readFile(filePath) || "";
            const stat = fs.statSync(filePath);
            posts.push({
              filename: file,
              title: file.replace(/_/g, " ").replace(".html", ""),
              html,
              week: w,
              size: stat.size,
            });
          }
        }
      }

      // Notes
      const notesDir = path.join(weeksDir, w, "substack_notes");
      if (fs.existsSync(notesDir)) {
        for (const file of fs.readdirSync(notesDir)) {
          if (file.endsWith(".md")) {
            const filePath = path.join(notesDir, file);
            const content = readFile(filePath) || "";
            const baseName = file.replace(".md", "");
            notes.push({
              filename: file,
              title: NOTE_TITLES[baseName] || baseName.replace(/_/g, " "),
              content,
              week: w,
            });
          }
        }
      }
    }
  }

  return { newsletters, posts, notes, currentISOWeek };
}

// Keep legacy function for backward compat
export function getSubstackPosts(week?: string): SubstackPost[] {
  return getSubstackContent(week).posts;
}

// ─── Weeks ───

export interface WeekSummary {
  week: string;
  hasSignals: boolean;
  hasNewsletter: boolean;
  hasSubstackPosts: boolean;
  hasNotes: boolean;
  fileCount: number;
}

export function getWeeks(): WeekSummary[] {
  const weeksDir = path.join(TRADES_DIR, "weeks");
  if (!fs.existsSync(weeksDir)) return [];

  return fs
    .readdirSync(weeksDir)
    .filter((d) => d.startsWith("2026-W"))
    .sort()
    .reverse()
    .map((w) => {
      const wDir = path.join(weeksDir, w);
      const files = fs.readdirSync(wDir);
      return {
        week: w,
        hasSignals: files.includes("signals.json"),
        hasNewsletter: files.includes("newsletter.html"),
        hasSubstackPosts: fs.existsSync(path.join(wDir, "substack_posts")),
        hasNotes: fs.existsSync(path.join(wDir, "substack_notes")),
        fileCount: files.length,
      };
    });
}

export function getWeekSignals(week: string): SignalsData | null {
  return readJSON(path.join(TRADES_DIR, "weeks", week, "signals.json")) as SignalsData | null;
}

// ─── Failed tweets ───

export interface FailedTweet {
  text: string;
  category: string;
  failures: string[];
  timestamp: string;
}

export function getFailedTweets(): FailedTweet[] {
  return (readJSON("failed_tweets.json") as FailedTweet[]) || [];
}

// ─── Workflow Status ───

export interface WorkflowRun {
  workflow: string;
  run_id: number;
  status: "success" | "failure" | "cancelled";
  started_at: string;
  completed_at: string;
  duration_seconds: number;
  error: string | null;
  trigger: string;
}

export interface WorkflowHealth {
  workflow: string;
  displayName: string;
  lastRun: WorkflowRun | null;
  lastSuccess: WorkflowRun | null;
  runsLast7Days: number;
  successesLast7Days: number;
  failuresLast7Days: number;
  successRate: number;
  expectedPerWeek: number;
  currentStreak: number;
  status: "healthy" | "degraded" | "failing" | "unknown";
}

export interface SystemHealth {
  overall: "operational" | "degraded" | "failing" | "unknown";
  message: string;
  workflows: WorkflowHealth[];
  lastUpdated: string | null;
}

const WORKFLOW_CONFIG: Record<string, { displayName: string; expectedPerWeek: number }> = {
  friday_scan: { displayName: "Friday Scan", expectedPerWeek: 1 },
  daily_scan: { displayName: "Daily Scan", expectedPerWeek: 5 },
  live_tweet: { displayName: "Live Tweets", expectedPerWeek: 35 },
  daily_post: { displayName: "Daily Posting", expectedPerWeek: 0 },
};

export function getWorkflowStatus(): SystemHealth {
  const runs = (readJSON("workflow_status.json") as WorkflowRun[]) || [];

  if (runs.length === 0) {
    return {
      overall: "unknown",
      message: "No workflow data available",
      workflows: Object.entries(WORKFLOW_CONFIG).map(([key, cfg]) => ({
        workflow: key,
        displayName: cfg.displayName,
        lastRun: null,
        lastSuccess: null,
        runsLast7Days: 0,
        successesLast7Days: 0,
        failuresLast7Days: 0,
        successRate: 0,
        expectedPerWeek: cfg.expectedPerWeek,
        currentStreak: 0,
        status: "unknown" as const,
      })),
      lastUpdated: null,
    };
  }

  const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();

  const workflows: WorkflowHealth[] = Object.entries(WORKFLOW_CONFIG).map(([key, cfg]) => {
    const workflowRuns = runs
      .filter((r) => r.workflow === key)
      .sort((a, b) => (b.completed_at || "").localeCompare(a.completed_at || ""));

    const lastRun = workflowRuns[0] || null;
    const lastSuccess = workflowRuns.find((r) => r.status === "success") || null;

    const recent = workflowRuns.filter((r) => (r.completed_at || "") >= sevenDaysAgo);
    const successes = recent.filter((r) => r.status === "success").length;
    const failures = recent.filter((r) => r.status === "failure").length;
    const successRate = recent.length > 0 ? Math.round((successes / recent.length) * 100) : 0;

    // Calculate streak
    let streak = 0;
    if (workflowRuns.length > 0) {
      const firstStatus = workflowRuns[0].status;
      for (const r of workflowRuns) {
        if (r.status === firstStatus) {
          streak += firstStatus === "success" ? 1 : -1;
        } else break;
      }
    }

    // Determine status
    let status: WorkflowHealth["status"] = "unknown";
    if (recent.length === 0) {
      status = cfg.expectedPerWeek > 0 ? "failing" : "unknown";
    } else if (failures === 0) {
      status = "healthy";
    } else if (successes > failures) {
      status = "degraded";
    } else {
      status = "failing";
    }

    return {
      workflow: key,
      displayName: cfg.displayName,
      lastRun,
      lastSuccess,
      runsLast7Days: recent.length,
      successesLast7Days: successes,
      failuresLast7Days: failures,
      successRate,
      expectedPerWeek: cfg.expectedPerWeek,
      currentStreak: streak,
      status,
    };
  });

  // Overall status
  const activeWorkflows = workflows.filter((w) => w.expectedPerWeek > 0);
  const failingCount = activeWorkflows.filter((w) => w.status === "failing").length;
  const degradedCount = activeWorkflows.filter((w) => w.status === "degraded").length;

  let overall: SystemHealth["overall"];
  let message: string;
  if (failingCount === 0 && degradedCount === 0) {
    overall = "operational";
    message = "All Systems Operational";
  } else if (failingCount > 0) {
    overall = "failing";
    message = `${failingCount} workflow${failingCount > 1 ? "s" : ""} failing`;
  } else {
    overall = "degraded";
    message = `${degradedCount} workflow${degradedCount > 1 ? "s" : ""} degraded`;
  }

  const sorted = [...runs].sort((a, b) => (b.completed_at || "").localeCompare(a.completed_at || ""));
  const lastUpdated = sorted.length > 0 ? sorted[0].completed_at : null;

  return { overall, message, workflows, lastUpdated };
}

// ─── System Log Generator ───

export function generateSystemLog(): string {
  const systemHealth = getWorkflowStatus();
  const portfolio = getPortfolio();
  const enriched = enrichPositions(portfolio);
  const tweetData = getEnrichedTweets();
  const signals = getSignals();
  const failed = getFailedTweets();
  const substack = getSubstackContent();
  const equityCurve = getEquityCurve();
  const latest = equityCurve.length > 0 ? equityCurve[equityCurve.length - 1] : null;

  const open = enriched.filter((p) => p.status === "OPEN");
  const closed = enriched.filter((p) => p.status !== "OPEN");

  const lines: string[] = [];
  lines.push("=== STERLING SIGNALS SYSTEM LOG ===");
  lines.push(`Generated: ${new Date().toISOString()}`);
  lines.push("");

  // Section 1: System Health
  lines.push("--- SYSTEM HEALTH ---");
  lines.push(`Overall: ${systemHealth.overall.toUpperCase()} - ${systemHealth.message}`);
  lines.push(`Last updated: ${systemHealth.lastUpdated || "N/A"}`);
  lines.push("");
  for (const w of systemHealth.workflows) {
    lines.push(`  ${w.displayName}: ${w.status.toUpperCase()}`);
    lines.push(`    Last run: ${w.lastRun?.completed_at || "never"} (${w.lastRun?.status || "N/A"})`);
    lines.push(`    7-day: ${w.successesLast7Days}/${w.runsLast7Days} success (expected ${w.expectedPerWeek}/week)`);
    lines.push(`    Streak: ${w.currentStreak > 0 ? `${w.currentStreak} successes` : w.currentStreak < 0 ? `${Math.abs(w.currentStreak)} failures` : "N/A"}`);
    if (w.lastRun?.error) lines.push(`    Error: ${w.lastRun.error}`);
  }
  lines.push("");

  // Section 2: Tweet Pipeline
  lines.push("--- TWEET PIPELINE ---");
  lines.push(`Total: ${tweetData.stats.total} | Posted: ${tweetData.stats.posted} | Upcoming: ${tweetData.stats.upcoming} | Expired: ${tweetData.stats.expired}`);
  lines.push(`Failed tweets (validation): ${failed.length}`);
  for (const [, stats] of Object.entries(tweetData.rollingStats)) {
    lines.push(`  ${stats.account}: ${stats.posted}/${stats.total} posted (${stats.successRate}% rate, 7-day)`);
  }
  if (failed.length > 0) {
    lines.push("  Recent failures:");
    for (const f of failed.slice(0, 5)) {
      lines.push(`    - [${f.category}] ${f.failures.join(", ")} (${f.timestamp})`);
    }
  }
  lines.push("");

  // Section 3: Scanner
  lines.push("--- SCANNER ---");
  if (signals) {
    lines.push(`Last scan: ${signals.timestamp}`);
    lines.push(`Timeframe: ${signals.timeframe || "WEEKLY"}`);
    lines.push(`Stats: ${JSON.stringify(signals.stats)}`);
    lines.push(`Buy signals: ${signals.buy_signals?.length || 0}`);
    lines.push(`Sell signals: ${signals.sell_signals?.length || 0}`);
    lines.push(`Themes: ${signals.themes?.length || 0}`);
    for (const sig of (signals.buy_signals || []).slice(0, 5)) {
      lines.push(`  ${sig.symbol}: ${sig.final_decision} (conviction ${sig.conviction}) - ${sig.theme}`);
    }
  } else {
    lines.push("No signals data available");
  }
  lines.push("");

  // Section 4: Portfolio
  lines.push("--- PORTFOLIO ---");
  lines.push(`Open: ${open.length} | Closed: ${closed.length}`);
  if (latest) {
    lines.push(`NAV: ${latest.nav} | Return: ${latest.total_return_pct}% | Alpha vs SPY: ${latest.alpha_pct}%`);
  }
  for (const p of open) {
    lines.push(`  ${p.ticker}: entry $${p.entry_price} | current $${p.current_price} | P&L ${p.pnl_pct.toFixed(1)}% | ${p.theme}`);
  }
  lines.push("");

  // Section 5: Substack
  lines.push("--- SUBSTACK CONTENT ---");
  lines.push(`Newsletters: ${substack.newsletters.length} | Posts: ${substack.posts.length} | Notes: ${substack.notes.length}`);
  lines.push(`Current week: ${substack.currentISOWeek}`);
  for (const p of substack.posts.filter((sp) => sp.week === "current")) {
    lines.push(`  [current] ${p.filename} (${(p.size / 1024).toFixed(1)}KB)`);
  }
  lines.push("");

  lines.push("=== END LOG ===");
  return lines.join("\n");
}

// ─── Helpers ───

export function weekToDateRange(isoWeek: string): string {
  // Parse "2026-W07" -> "Feb 10 - 16"
  const parts = isoWeek.split("-W");
  if (parts.length !== 2) return isoWeek;
  const year = parseInt(parts[0]);
  const weekNum = parseInt(parts[1]);
  if (isNaN(year) || isNaN(weekNum)) return isoWeek;

  // ISO week: week 1 contains Jan 4
  const jan4 = new Date(year, 0, 4);
  const dayOfWeek = jan4.getDay() || 7; // Mon=1 ... Sun=7
  const monday = new Date(jan4);
  monday.setDate(jan4.getDate() - dayOfWeek + 1 + (weekNum - 1) * 7);
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);

  const fmt = (d: Date) =>
    d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  return `${fmt(monday)} \u2013 ${fmt(sunday)}`;
}
