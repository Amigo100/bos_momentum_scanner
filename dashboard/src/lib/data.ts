import path from "path";
import fs from "fs";
import Papa from "papaparse";

// ─── Data Resolution ───
// Local dev: reads from section-specific output directories (live data)
//   portfolio/output/  - portfolio.csv, equity_curve.csv
//   scanner/output/    - signals.json, analysis_log.csv, current/, archive/
//   twitter/output/    - tweet queues, charts, tracking, workflow_status
//   substack/output/   - newsletter, posts, notes
// Vercel: reads from dashboard/data/ (bundled at build time)

function isBundled(): boolean {
  const bundledDir = path.join(process.cwd(), "data");
  return fs.existsSync(path.join(bundledDir, "manifest.json"));
}

const BUNDLED_DIR = path.join(process.cwd(), "data");
const PROJECT_ROOT = path.resolve(process.cwd(), "..");

// Section-specific output directories (local development)
const PORTFOLIO_DIR = path.join(PROJECT_ROOT, "portfolio", "output");
const SCANNER_DIR = path.join(PROJECT_ROOT, "scanner", "output");
const TWITTER_DIR = path.join(PROJECT_ROOT, "twitter", "output");
const SUBSTACK_DIR = path.join(PROJECT_ROOT, "substack", "output");

// Legacy fallback: trades/ directory (used if section dirs don't exist yet)
const LEGACY_TRADES_DIR = path.join(PROJECT_ROOT, "trades");

/**
 * Resolve a file path by checking section-specific directories first,
 * then falling back to bundled data (Vercel) or legacy trades/ directory.
 * legacyRelativePath allows mapping to a different legacy path
 * (e.g. "archive/W08/signals.json" maps to "weeks/W08/signals.json" in legacy).
 */
function resolveFile(sectionDir: string, relativePath: string, legacyRelativePath?: string): string {
  // Bundled deployment: everything is in data/
  if (isBundled()) {
    return path.join(BUNDLED_DIR, relativePath);
  }

  // Section-specific directory (new layout)
  const sectionPath = path.join(sectionDir, relativePath);
  if (fs.existsSync(sectionPath)) {
    return sectionPath;
  }

  // Legacy fallback: try the explicit legacy path first, then same relative path
  if (legacyRelativePath) {
    const legacyMapped = path.join(LEGACY_TRADES_DIR, legacyRelativePath);
    if (fs.existsSync(legacyMapped)) {
      return legacyMapped;
    }
  }

  const legacyPath = path.join(LEGACY_TRADES_DIR, relativePath);
  if (fs.existsSync(legacyPath)) {
    return legacyPath;
  }

  // Default to section path (will fail gracefully in read functions)
  return sectionPath;
}

/**
 * Resolve a directory path, checking section-specific first, then legacy.
 * legacyRelativePath allows mapping to a different legacy path
 * (e.g. "archive" in section dirs maps to "weeks" in legacy trades/).
 */
function resolveDir(sectionDir: string, relativePath: string, legacyRelativePath?: string): string {
  if (isBundled()) {
    return path.join(BUNDLED_DIR, relativePath);
  }

  const sectionPath = path.join(sectionDir, relativePath);
  if (fs.existsSync(sectionPath)) {
    return sectionPath;
  }

  // Legacy fallback: try the explicit legacy path first, then same relative path
  if (legacyRelativePath) {
    const legacyMapped = path.join(LEGACY_TRADES_DIR, legacyRelativePath);
    if (fs.existsSync(legacyMapped)) {
      return legacyMapped;
    }
  }

  const legacyPath = path.join(LEGACY_TRADES_DIR, relativePath);
  if (fs.existsSync(legacyPath)) {
    return legacyPath;
  }

  return sectionPath;
}

function readJSON(filePath: string): unknown | null {
  try {
    const raw = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function readCSV(filePath: string): Record<string, string>[] {
  try {
    const raw = fs.readFileSync(filePath, "utf-8");
    const result = Papa.parse(raw, { header: true, skipEmptyLines: true });
    return result.data as Record<string, string>[];
  } catch {
    return [];
  }
}

function readFile(filePath: string): string | null {
  try {
    return fs.readFileSync(filePath, "utf-8");
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
  const rows = readCSV(resolveFile(PORTFOLIO_DIR, "portfolio_google_sheets.csv"));
  if (rows.length === 0) {
    return readCSV(resolveFile(PORTFOLIO_DIR, "portfolio.csv")).map((r) => ({
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
  return readCSV(resolveFile(PORTFOLIO_DIR, "equity_curve.csv")).map((r) => ({
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
  error?: string;
}

export interface EnrichedTweet extends Tweet {
  source: "weekly" | "daily" | "live";
  displayStatus: "upcoming" | "posted" | "expired" | "skipped" | "failed" | "abandoned";
  sortKey: string;
  scheduledTimeET: string;
}

// Slot time mapping for generating sortKey
const SLOT_TIMES: Record<number, string> = {
  1: "07:30", 2: "10:00", 3: "12:30", 4: "15:30", 5: "18:00", 6: "17:00", 7: "18:30",
};

function enrichTweet(tweet: Tweet, source: "weekly" | "daily" | "live"): EnrichedTweet {
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York" }).format(new Date());
  const isPosted = tweet.posted === true || tweet.status === "posted";

  let displayStatus: EnrichedTweet["displayStatus"];
  if (isPosted) {
    displayStatus = "posted";
  } else if (tweet.status === "skipped") {
    displayStatus = "skipped";
  } else if (tweet.status === "failed") {
    displayStatus = "failed";
  } else if (source === "live" && tweet.status === "pending") {
    // Live tweets are reactive: pending items from past cron runs
    // will never be posted — the next cron generates fresh content.
    displayStatus = "abandoned";
  } else if (tweet.scheduled_date && tweet.scheduled_date >= today) {
    displayStatus = "upcoming";
  } else {
    displayStatus = "expired";
  }

  // Build sortKey from scheduled_date + time
  const time = tweet.time || SLOT_TIMES[tweet.slot] || "12:00";
  const date = tweet.scheduled_date || tweet.timestamp?.slice(0, 10) || "9999-99-99";
  const sortKey = `${date}T${time}`;
  const scheduledTimeET = time;

  return { ...tweet, source, displayStatus, sortKey, scheduledTimeET };
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
    time: raw.scheduled_time ? new Date(raw.scheduled_time).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "America/New_York" }) : "",
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
    error: raw.error,
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

export interface AccountHealth {
  lastPosted: string | null;       // ISO timestamp of most recent successful post
  lastFailed: string | null;       // ISO timestamp of most recent failure
  lastError: string | null;        // Error message from most recent failure
  consecutiveFailures: number;     // Count of failures before first posted (recent→old)
  status: "active" | "failing" | "idle";
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
    failed: number;
    abandoned: number;
    total: number;
  };
  dailyStats: Record<string, DailyStats>;
  rollingStats: Record<string, RollingStats>;
  accountHealth: Record<string, AccountHealth>;
}

export function getEnrichedTweets(): EnrichedTweetData {
  // Live tweets only — batch queues (content_queue.json, daily_content_queue.json)
  // are from the disabled daily_post.yml workflow and will never post.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const liveRaw = (readJSON(resolveFile(TWITTER_DIR, "live_content_queue.json")) as any[]) || [];
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
    account1: liveByAccount.account1.sort((a, b) => b.sortKey.localeCompare(a.sortKey)),
    account2: liveByAccount.account2.sort((a, b) => b.sortKey.localeCompare(a.sortKey)),
    account3: liveByAccount.account3.sort((a, b) => b.sortKey.localeCompare(a.sortKey)),
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
    failed: all.filter((t) => t.displayStatus === "failed").length,
    abandoned: all.filter((t) => t.displayStatus === "abandoned").length,
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
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York" }).format(new Date());
  const sevenDaysAgo = new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York" }).format(new Date(Date.now() - 7 * 24 * 60 * 60 * 1000));

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

  // ─── Account Health ───
  function computeHealth(tweets: EnrichedTweet[]): AccountHealth {
    // Sort by generated_at / timestamp descending (most recent first)
    const sorted = [...tweets].sort((a, b) => (b.timestamp || "").localeCompare(a.timestamp || ""));

    let lastPosted: string | null = null;
    let lastFailed: string | null = null;
    let lastError: string | null = null;
    let consecutiveFailures = 0;
    let foundPosted = false;

    for (const t of sorted) {
      if (t.displayStatus === "posted") {
        if (!lastPosted) lastPosted = t.posted_at || t.timestamp || null;
        foundPosted = true;
        break; // stop counting consecutive failures
      } else if (t.displayStatus === "failed") {
        if (!lastFailed) {
          lastFailed = t.timestamp || null;
          lastError = t.error || null;
        }
        consecutiveFailures++;
      }
      // Skip upcoming/abandoned/expired — they don't indicate health
    }

    // Determine status
    let status: AccountHealth["status"] = "idle";
    if (lastPosted) {
      const postedAge = Date.now() - new Date(lastPosted).getTime();
      const hours48 = 48 * 60 * 60 * 1000;
      if (postedAge < hours48 && consecutiveFailures < 2) {
        status = "active";
      } else if (consecutiveFailures >= 2) {
        status = "failing";
      } else if (foundPosted) {
        status = "idle";
      }
    } else if (consecutiveFailures >= 2) {
      status = "failing";
    }

    return { lastPosted, lastFailed, lastError, consecutiveFailures, status };
  }

  const accountHealth: Record<string, AccountHealth> = {
    account1: computeHealth(accounts.account1),
    account2: computeHealth(accounts.account2),
    account3: computeHealth(accounts.account3),
  };

  return { accounts, nextTweet, nextTweetByAccount, failed, stats, dailyStats, rollingStats, accountHealth };
}

// Legacy functions — only load live queue now (batch queues disabled)
export function getTweets(): { weekly: Tweet[]; daily: Tweet[]; live: Tweet[] } {
  const live = (readJSON(resolveFile(TWITTER_DIR, "live_content_queue.json")) as Tweet[]) || [];
  return { weekly: [], daily: [], live };
}

export function getAllAccountTweets(): { account1: Tweet[]; account2: Tweet[]; account3: Tweet[] } {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const liveRaw = (readJSON(resolveFile(TWITTER_DIR, "live_content_queue.json")) as any[]) || [];
  const result: { account1: Tweet[]; account2: Tweet[]; account3: Tweet[] } = {
    account1: [], account2: [], account3: [],
  };
  for (const raw of liveRaw) {
    const normalized = normalizeLiveTweet(raw);
    const acct = mapLiveAccountToNumber(raw.account || "variant_1");
    result[acct].push(normalized);
  }
  return result;
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
  return readJSON(resolveFile(SCANNER_DIR, "signals.json")) as SignalsData | null;
}

export function getDailySignals(): unknown | null {
  return readJSON(resolveFile(SCANNER_DIR, "daily_signals.json"));
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
  format: "md" | "html";
  size?: number;
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
  const currentNewsletter = resolveFile(SUBSTACK_DIR, path.join("current", "newsletter.html"));
  if (fs.existsSync(currentNewsletter)) {
    const html = readFile(currentNewsletter) || "";
    const stat = fs.statSync(currentNewsletter);
    newsletters.push({ html, week: "current", size: stat.size });
  }

  // Posts
  const currentPostsDir = resolveDir(SUBSTACK_DIR, path.join("current", "substack_posts"));
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

  // Notes (md and html)
  const currentNotesDir = resolveDir(SUBSTACK_DIR, path.join("current", "substack_notes"));
  if (fs.existsSync(currentNotesDir)) {
    for (const file of fs.readdirSync(currentNotesDir)) {
      if (file.endsWith(".md") || file.endsWith(".html")) {
        const filePath = path.join(currentNotesDir, file);
        const content = readFile(filePath) || "";
        const isHtml = file.endsWith(".html");
        const baseName = file.replace(/\.(md|html)$/, "");
        const stat = fs.statSync(filePath);
        notes.push({
          filename: file,
          title: NOTE_TITLES[baseName] || baseName.replace(/_/g, " "),
          content,
          week: "current",
          format: isHtml ? "html" : "md",
          size: stat.size,
        });
      }
    }
  }

  // ─── Week archives ───
  const substackArchiveDir = resolveDir(SUBSTACK_DIR, "archive", "weeks");
  if (fs.existsSync(substackArchiveDir)) {
    const weeks = fs.readdirSync(substackArchiveDir).filter((d) => d.startsWith("2026-W")).sort().reverse();
    for (const w of weeks) {
      if (week && w !== week && week !== "all") continue;
      // Skip current ISO week from archives to avoid duplication with current/ folder
      if (w === currentISOWeek && (!week || week === "all")) continue;

      const weekDir = path.join(substackArchiveDir, w);

      // Newsletter
      const nPath = path.join(weekDir, "newsletter.html");
      if (fs.existsSync(nPath)) {
        const html = readFile(nPath) || "";
        const stat = fs.statSync(nPath);
        newsletters.push({ html, week: w, size: stat.size });
      }

      // Posts
      const postsDir = path.join(weekDir, "substack_posts");
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

      // Notes (md and html)
      const notesDir = path.join(weekDir, "substack_notes");
      if (fs.existsSync(notesDir)) {
        for (const file of fs.readdirSync(notesDir)) {
          if (file.endsWith(".md") || file.endsWith(".html")) {
            const filePath = path.join(notesDir, file);
            const content = readFile(filePath) || "";
            const isHtml = file.endsWith(".html");
            const baseName = file.replace(/\.(md|html)$/, "");
            const stat = fs.statSync(filePath);
            notes.push({
              filename: file,
              title: NOTE_TITLES[baseName] || baseName.replace(/_/g, " "),
              content,
              week: w,
              format: isHtml ? "html" : "md",
              size: stat.size,
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
  const scannerArchive = resolveDir(SCANNER_DIR, "archive", "weeks");
  const substackArchive = resolveDir(SUBSTACK_DIR, "archive", "weeks");

  // Collect week names from both scanner and substack archives
  const weekSet = new Set<string>();
  for (const dir of [scannerArchive, substackArchive]) {
    if (fs.existsSync(dir)) {
      for (const d of fs.readdirSync(dir)) {
        if (d.startsWith("2026-W")) weekSet.add(d);
      }
    }
  }

  return Array.from(weekSet)
    .sort()
    .reverse()
    .map((w) => {
      const scannerWeekDir = path.join(scannerArchive, w);
      const substackWeekDir = path.join(substackArchive, w);
      const scannerFiles = fs.existsSync(scannerWeekDir) ? fs.readdirSync(scannerWeekDir) : [];
      const substackFiles = fs.existsSync(substackWeekDir) ? fs.readdirSync(substackWeekDir) : [];
      return {
        week: w,
        hasSignals: scannerFiles.includes("signals.json"),
        hasNewsletter: substackFiles.includes("newsletter.html"),
        hasSubstackPosts: fs.existsSync(path.join(substackWeekDir, "substack_posts")),
        hasNotes: fs.existsSync(path.join(substackWeekDir, "substack_notes")),
        fileCount: scannerFiles.length + substackFiles.length,
      };
    });
}

export function getWeekSignals(week: string): SignalsData | null {
  return readJSON(resolveFile(
    SCANNER_DIR,
    path.join("archive", week, "signals.json"),
    path.join("weeks", week, "signals.json"),
  )) as SignalsData | null;
}

// ─── Failed tweets ───

export interface FailedTweet {
  text: string;
  category: string;
  failures: string[];
  timestamp: string;
}

export function getFailedTweets(): FailedTweet[] {
  return (readJSON(resolveFile(TWITTER_DIR, "failed_tweets.json")) as FailedTweet[]) || [];
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
  const runs = (readJSON(resolveFile(TWITTER_DIR, "workflow_status.json")) as WorkflowRun[]) || [];

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

// ─── Live Workflow Summary ───

export interface LiveWorkflowSummary {
  lastRunAt: string | null;
  lastRunStatus: string;
  runsToday: number;
  accountResults: Record<string, number> | null; // per-account exit codes from latest run
}

export function getLiveWorkflowSummary(): LiveWorkflowSummary {
  const runs = (readJSON(resolveFile(TWITTER_DIR, "workflow_status.json")) as Array<{
    workflow: string;
    status: string;
    completed_at?: string;
    started_at?: string;
    account_results?: Record<string, number>;
  }>) || [];

  const liveRuns = runs
    .filter((r) => r.workflow === "live_tweet")
    .sort((a, b) => (b.completed_at || b.started_at || "").localeCompare(a.completed_at || a.started_at || ""));

  const latest = liveRuns[0] || null;

  // Count today's runs in ET
  const todayET = new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York" }).format(new Date());
  const runsToday = liveRuns.filter((r) => {
    const ts = r.completed_at || r.started_at || "";
    return ts.startsWith(todayET);
  }).length;

  return {
    lastRunAt: latest?.completed_at || latest?.started_at || null,
    lastRunStatus: latest?.status || "unknown",
    runsToday,
    accountResults: latest?.account_results || null,
  };
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

// ─── Content Schedule & Handbook Prompts ───

export interface ScheduleEntry {
  day: string;
  category: string;
  topic: string;
  theme_style: string;
  note_types: string[];
  handbook_prompt: string;
}

export interface ContentSchedule {
  week: string;
  generated: string;
  schedule: ScheduleEntry[];
}

export interface HandbookPrompt {
  id: string;
  title: string;
  type: "post" | "notes" | "trade-alert";
  prompt: string;
}

export function getContentSchedule(): ContentSchedule | null {
  const filePath = resolveFile(SUBSTACK_DIR, path.join("current", "content_schedule.json"));
  return readJSON(filePath) as ContentSchedule | null;
}

export interface ContentProductionGuide {
  markdown: string;
  charCount: number;
  lineCount: number;
  generatedDate: string | null;
  weekNumber: string | null;
}

export function getContentProductionGuide(): ContentProductionGuide | null {
  const filePath = resolveFile(SUBSTACK_DIR, path.join("current", "content_production_guide.md"));
  const content = readFile(filePath);
  if (!content) return null;

  // Parse generation metadata from last line: *Generated: 2026-02-20 19:52:12 | Week 8*
  let generatedDate: string | null = null;
  let weekNumber: string | null = null;
  const metaMatch = content.match(/\*Generated: (.+?) \| Week (\d+)\*/);
  if (metaMatch) {
    generatedDate = metaMatch[1];
    weekNumber = metaMatch[2];
  }

  return {
    markdown: content,
    charCount: content.length,
    lineCount: content.split("\n").length,
    generatedDate,
    weekNumber,
  };
}

export function getHandbookPrompts(): HandbookPrompt[] {
  // Try bundled docs first, then source docs
  let handbookPath: string;
  if (isBundled()) {
    handbookPath = path.join(BUNDLED_DIR, "docs", "content_prompt_handbook_v5.md");
  } else {
    handbookPath = path.join(PROJECT_ROOT, "substack", "docs", "content_prompt_handbook_v5.md");
  }

  const content = readFile(handbookPath);
  if (!content) return [];

  const prompts: HandbookPrompt[] = [];

  // Split by ## sections (level 2 headers)
  const sections = content.split(/^## /m).slice(1); // skip content before first ##

  for (const section of sections) {
    const lines = section.split("\n");
    const sectionTitle = lines[0].trim();

    // Skip non-prompt sections (How to Use, Quick Reference, etc.)
    if (!sectionTitle.startsWith("Category") && !sectionTitle.startsWith("Trade Alert") && !sectionTitle.startsWith("Daily Notes")) {
      continue;
    }

    // Determine type
    let type: HandbookPrompt["type"] = "post";
    if (sectionTitle.startsWith("Trade Alert")) type = "trade-alert";
    if (sectionTitle.startsWith("Daily Notes")) type = "notes";

    // Find all code fences in this section
    const sectionText = section;
    const fenceRegex = /### (?:Post Prompt|Notes Prompt)\s*\n+```\n([\s\S]*?)```/g;
    let match;
    while ((match = fenceRegex.exec(sectionText)) !== null) {
      const promptText = match[1].trim();
      if (promptText.length > 0) {
        const id = sectionTitle
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, "-")
          .replace(/^-|-$/g, "");
        // For the Notes section, use a distinct title
        const isNotes = match[0].includes("Notes Prompt");
        const title = isNotes && type !== "notes" ? `${sectionTitle} (Notes)` : sectionTitle;
        const finalType = isNotes ? "notes" : type;

        prompts.push({
          id: isNotes ? `${id}-notes` : id,
          title,
          type: finalType,
          prompt: promptText,
        });
      }
    }
  }

  return prompts;
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
