# Sterling Signals Documentation

## System Overview

**BoS Momentum Scanner** — Weekly + daily momentum trading scanner for US stocks with automated content generation and multi-account X/Twitter distribution.

**Key capabilities:**
- **Weekly scanner** — 1,800 stocks → 5-gate filter → 3-5 actionable signals (Friday after close)
- **Daily scanner** — Daily BoS signals on daily bars, max 5 signals/day (Mon-Fri after close)
- **Unified tweet voice** — Single consistent brand voice across 3 accounts (replaces old 3-persona system)
- **7-slot posting system** — Slots 1/6/7 daily content, slots 2-5 weekly content, EST/EDT aware
- **Sell signal notifications** — Real-time email + WhatsApp alerts on bearish pivots and trailing stops
- **7-step validation pipeline** — Category check, ticker/price check, banned phrases, winners-only, internal terminology, character count, chart flag

## Quick Reference

| Document | Location | Description |
|----------|----------|-------------|
| [CLAUDE.md](../CLAUDE.md) | Root | AI assistant context (primary reference) |
| [SETUP.md](SETUP.md) | docs/ | Setup instructions |

---

## Technical Documentation

| Document | Description |
|----------|-------------|
| [STYLE_GUIDE.md](STYLE_GUIDE.md) | Python coding standards |
| [STERLING_SIGNALS_MASTER_PROMPTS.md](STERLING_SIGNALS_MASTER_PROMPTS.md) | LLM prompt reference |

---

## Audit Reports

Comprehensive system audits (January 2026):

| Audit | Focus Area |
|-------|------------|
| [audit/AUDIT_REPORT.md](audit/AUDIT_REPORT.md) | Summary report |
| [audit/01-scanner-logic.md](audit/01-scanner-logic.md) | Scanner pipeline |
| [audit/02-signal-detection.md](audit/02-signal-detection.md) | Signal detection rules |
| [audit/03-portfolio-tracking.md](audit/03-portfolio-tracking.md) | Portfolio management |
| [audit/04-pnl-calculation.md](audit/04-pnl-calculation.md) | P&L calculations |
| [audit/05-twitter-automation.md](audit/05-twitter-automation.md) | Twitter/X automation |
| [audit/06-newsletter-generation.md](audit/06-newsletter-generation.md) | Newsletter system |
| [audit/07-marketing-compliance.md](audit/07-marketing-compliance.md) | Marketing safeguards |

---

## Planning Documents

| Document | Description |
|----------|-------------|
| [planning/OPTIMISATION_PLAN.md](planning/OPTIMISATION_PLAN.md) | Refactoring roadmap |
| [planning/MIGRATION_GUIDE.md](planning/MIGRATION_GUIDE.md) | Code migration guide |
| [planning/PORTFOLIO_DASHBOARD_SPEC.md](planning/PORTFOLIO_DASHBOARD_SPEC.md) | Dashboard specification |

---

## Archive

Historical documents preserved for reference: [archive/](archive/)

These include completed implementation plans, verification prompts, and superseded documentation.
