# Sterling Signals - External Setup Guide

This document covers all external accounts, credentials, and systems you need to configure **before** running the automated pipeline. Complete these steps in order.

---

## 1. X (Twitter) Developer Account

**Priority: P0 - Do Immediately (approval can take 1-3 days)**

### Steps

1. Go to [developer.x.com](https://developer.x.com)
2. Sign in with your @SterlingSignals account
3. Click "Sign up for Free Account" or apply for Basic tier
4. Complete the use case questionnaire:
   - **Use case:** "Building an automated posting system for my financial newsletter"
   - **Will you make Twitter content available to a government entity?** No
   - **Will you analyze Twitter data?** No (you're posting, not analyzing)

### What You'll Get

After approval, create a Project and App to get:

| Credential | Where to Find |
|------------|---------------|
| API Key | Project → App → Keys and Tokens |
| API Secret | Project → App → Keys and Tokens |
| Access Token | Project → App → Keys and Tokens → Generate |
| Access Token Secret | Project → App → Keys and Tokens → Generate |

### Important Settings

1. Go to your App settings
2. Set **User authentication settings**:
   - App permissions: **Read and Write**
   - Type of App: **Web App, Automated App or Bot**
   - Callback URL: `https://localhost` (placeholder)
   - Website URL: `https://sterlingsignals.substack.com`

### Free Tier Limits

- 17 posts per 24 hours per app
- 500 posts per month
- **This is sufficient for 3-4 posts/day**

---

## 2. GitHub Private Repository

**Priority: P0**

### Create Repository

1. Go to [github.com/new](https://github.com/new)
2. **Repository name:** `sterling-signals-automation`
3. **Visibility:** Private
4. **Initialize:** Add README
5. Click "Create repository"

### Add Secrets

Go to: `Settings → Secrets and variables → Actions → New repository secret`

| Secret Name | Value | Required For |
|-------------|-------|--------------|
| `ANTHROPIC_API_KEY` | Your Claude API key | Scanner, DD, Market Analysis |
| `X_API_KEY` | From X Developer Portal | X posting |
| `X_API_SECRET` | From X Developer Portal | X posting |
| `X_ACCESS_TOKEN` | From X Developer Portal | X posting |
| `X_ACCESS_SECRET` | From X Developer Portal | X posting |
| `CHART_IMG_API_KEY` | From chart-img.com (optional) | Chart capture |
| `EMAIL_SENDER` | Your Gmail address | Failure alerts |
| `EMAIL_PASSWORD` | Gmail app password | Failure alerts |
| `EMAIL_RECIPIENTS` | Comma-separated emails | Failure alerts |

### Clone to Local

```bash
git clone https://github.com/YOUR_USERNAME/sterling-signals-automation.git
cd sterling-signals-automation

# Copy your existing scanner files
cp ~/path/to/scanner.py .
cp ~/path/to/thematic_analyzer.py .
cp ~/path/to/gatekeeper.py .
cp ~/path/to/grok_prompts_generator.py .
# ... etc
```

---

## 3. Substack Session Credentials

**Priority: P1**

### Extract Session Token

1. Open Chrome/Safari
2. Go to your Substack dashboard (logged in)
3. Open DevTools: `F12` or `Right-click → Inspect`
4. Go to **Network** tab
5. Filter by `Fetch/XHR`
6. Click any API call (e.g., something with `/api/v1/`)
7. In **Headers** tab, find the `Cookie` header
8. Look for `substack.sid=` or `connect.sid=` value

**Save this value securely - it's your session token.**

### Extract User ID

1. In the same Network tab
2. Look for a call to `publication_user` or `me`
3. Click it, go to **Preview** tab
4. Find the `id` field under `user` object

**Example:**
```json
{
  "user": {
    "id": 12345678,
    "email": "you@example.com"
  }
}
```

### Important Notes

- Session tokens remain valid for months if you don't sign out
- **Never sign out of Substack in this browser** - it invalidates the token
- Consider using a dedicated browser profile for automation

---

## 4. TradingView Session (For Playwright Chart Capture)

**Priority: P1 (if using Playwright, otherwise skip)**

### Extract Session Cookies

1. Open Chrome
2. Go to TradingView (logged in to your Pro account)
3. Open DevTools (`F12`)
4. Go to **Application** tab → **Cookies** → `https://www.tradingview.com`
5. Find and copy:

| Cookie Name | What It Is |
|-------------|------------|
| `sessionid` | Your session ID |
| `sessionid_sign` | Session signature |

### Find Your Chart Layout ID

1. Open TradingView with your saved BoS/Banker indicator layout
2. Look at the URL: `https://www.tradingview.com/chart/XXXXXXX/?symbol=...`
3. The `XXXXXXX` part is your layout ID

**Save this - you'll use it in `chart_capture.py`**

### Chrome Profile Path (for Playwright)

Playwright can use your logged-in Chrome session:

| OS | Path |
|----|------|
| macOS | `~/Library/Application Support/Google/Chrome/` |
| Windows | `%APPDATA%\Google\Chrome\User Data` |
| Linux | `~/.config/google-chrome/` |

---

## 5. CHART-IMG API (Optional Alternative)

**Priority: P2 (if not using Playwright)**

If you want simpler chart capture without custom indicators:

1. Go to [chart-img.com](https://chart-img.com)
2. Sign up for free tier
3. Generate API key from dashboard
4. Add to GitHub Secrets as `CHART_IMG_API_KEY`

**Free tier limitations:**
- Limited requests per day (check current limits)
- No custom indicators (uses TradingView's default)

---

## 6. Gmail App Password (For Alerts)

**Priority: P2**

For email notifications on pipeline failures:

1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Security → 2-Step Verification (enable if not already)
3. At bottom: **App passwords**
4. Generate a new app password for "Mail"
5. Save the 16-character password

Add to GitHub Secrets:
- `EMAIL_SENDER`: your.email@gmail.com
- `EMAIL_PASSWORD`: the 16-character app password

---

## 7. Claude Desktop MCP Configuration (Optional)

**Priority: P2**

If you want to use MCP servers with Claude Desktop:

### Config File Location

| OS | Path |
|----|------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

### Example Configuration

```json
{
  "mcpServers": {
    "substack-api": {
      "command": "npx",
      "args": ["-y", "substack-mcp@latest"],
      "env": {
        "SUBSTACK_PUBLICATION_URL": "https://sterlingsignals.substack.com",
        "SUBSTACK_SESSION_TOKEN": "YOUR_SESSION_TOKEN_HERE",
        "SUBSTACK_USER_ID": "YOUR_USER_ID_HERE"
      }
    }
  }
}
```

### Restart Claude Desktop

After editing the config, fully restart Claude Desktop for changes to take effect.

---

## 8. Local Environment Setup

### Python Dependencies

```bash
# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install anthropic yfinance pandas numpy tweepy playwright

# Install Playwright browsers (for chart capture)
playwright install chromium
```

### Environment Variables (Local Development)

Create `.env` file in project root (add to `.gitignore`!):

```bash
ANTHROPIC_API_KEY=sk-ant-...
X_API_KEY=...
X_API_SECRET=...
X_ACCESS_TOKEN=...
X_ACCESS_SECRET=...
CHART_IMG_API_KEY=...

# Email
EMAIL_SENDER=your.email@gmail.com
EMAIL_PASSWORD=your-app-password

# Substack
SUBSTACK_SESSION_TOKEN=...
SUBSTACK_USER_ID=...

# TradingView
TRADINGVIEW_SESSION_ID=...
TRADINGVIEW_SESSION_ID_SIGN=...
TRADINGVIEW_LAYOUT_ID=...
```

---

## Verification Checklist

### Before Starting Development

- [ ] X Developer account approved
- [ ] X API credentials generated and tested
- [ ] GitHub private repo created
- [ ] GitHub Secrets configured
- [ ] Substack session token extracted
- [ ] Substack user ID extracted
- [ ] TradingView cookies extracted (if using Playwright)
- [ ] TradingView layout ID noted

### Before Going Live

- [ ] Test X posting manually with Tweepy
- [ ] Test Substack draft creation via MCP
- [ ] Test chart capture with one ticker
- [ ] Run full Friday pipeline in test mode
- [ ] Verify GitHub Actions workflow triggers
- [ ] Confirm email alerts working

---

## Troubleshooting

### X API "403 Forbidden"

- Check app permissions are set to "Read and Write"
- Regenerate Access Token after changing permissions
- Verify all 4 credentials are correct

### Substack Session Expired

- Session tokens last months unless you sign out
- If expired: log in again, extract new token
- Don't sign out of Substack in your automation browser

### TradingView Charts Not Loading

- Session cookies may have expired (1-2 week lifespan)
- Re-extract `sessionid` and `sessionid_sign`
- Make sure you're logged into TradingView Pro

### GitHub Actions Not Running

- Check workflow file syntax (YAML is whitespace-sensitive)
- Verify cron schedule is in UTC
- Scheduled workflows disabled after 60 days of inactivity
- Push a commit to re-enable

---

## Support Resources

| Resource | URL |
|----------|-----|
| X API Documentation | https://developer.x.com/en/docs |
| Tweepy Documentation | https://docs.tweepy.org |
| GitHub Actions Docs | https://docs.github.com/actions |
| Playwright Python Docs | https://playwright.dev/python |
| Substack MCP Server | https://github.com/marcomoauro/substack-mcp |
| CHART-IMG API | https://chart-img.com/docs |
| Anthropic API | https://docs.anthropic.com |

---

*Complete the P0 items immediately, then proceed to Claude Code for implementation.*
