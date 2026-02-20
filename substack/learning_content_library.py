#!/usr/bin/env python3
"""
Sterling Signals — Learning Content Library

Static library of educational topics for Notes and posts.
Each topic can generate a note-length (150-250 word) piece
or serve as a seed for a full educational post (800-1200 words).

Topics span five categories: risk management, momentum, fundamentals,
psychology, and strategy. All content uses marketing-safe language
and the Sterling Signals medical-investor voice.

Usage:
    from substack.learning_content_library import (
        LEARNING_TOPICS,
        get_random_topic,
        get_topics_by_category,
        get_all_categories,
    )
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import random


# =============================================================================
# DATA STRUCTURE
# =============================================================================

@dataclass
class LearningTopic:
    """A single educational content topic with note and post variants."""
    id: str                        # Unique slug
    title: str                     # Display title
    category: str                  # risk_management, momentum, fundamentals, psychology, strategy
    hook: str                      # Opening sentence to grab attention (1-2 sentences)
    key_concept: str               # Core teaching point (2-3 sentences)
    example: str                   # Real-world example using Sterling Signals language (2-3 sentences)
    engagement_question: str       # Question to end the note with
    note_template: str             # Complete 150-250 word note ready to post
    post_outline: List[str]        # Section headings for a full post version
    tags: List[str]                # Topic tags for dedup/rotation


# =============================================================================
# TOPIC DEFINITIONS — RISK MANAGEMENT (4)
# =============================================================================

_POSITION_SIZING = LearningTopic(
    id="position_sizing",
    title="Position Sizing: The Variable Nobody Talks About",
    category="risk_management",
    hook=(
        "Most investors obsess over which stock to buy. "
        "The professionals obsess over how much."
    ),
    key_concept=(
        "Position sizing determines whether a single loss bruises your portfolio or breaks it. "
        "A concentrated bet on a stock that drops 40% wipes out gains from three winners. "
        "The prescription is simple: size your positions so that no single outcome can derail the plan."
    ),
    example=(
        "Our screening system grades every signal it clears by conviction level. "
        "Higher conviction means a larger allocation; speculative setups get a smaller dose. "
        "This is not guesswork. It is risk-defined position management baked into the protocol."
    ),
    engagement_question="How do you decide position size — gut feeling, or a system?",
    note_template=(
        "Most investors obsess over which stock to buy. "
        "The professionals obsess over how much.\n\n"
        "In medicine we call it dosing. The right drug at the wrong dose is still a bad outcome. "
        "Investing works the same way. A concentrated bet on a stock that drops 40% wipes out "
        "the gains from three winners. And a position so small it barely moves the needle? "
        "That is wasted conviction.\n\n"
        "Position sizing is the variable that separates the people who survive a drawdown "
        "from the people who blow up during one. The prescription: size every position so "
        "that no single outcome can put the portfolio on life support.\n\n"
        "Our screening system grades every signal it clears by conviction level. "
        "Higher conviction means a larger allocation. Speculative setups get a smaller dose. "
        "This is not guesswork. It is risk-defined position management baked into the protocol.\n\n"
        "Think of it this way: a surgeon does not use the same force on every incision. "
        "Precision matters more than aggression.\n\n"
        "How do you decide position size — gut feeling, or a system?\n\n"
        "Not financial advice. Informational only."
    ),
    post_outline=[
        "Why position sizing matters more than stock selection",
        "The math: how a single bad bet destroys compound returns",
        "Conviction-based sizing: matching allocation to evidence",
        "The dosing analogy: right drug, right dose, right outcome",
        "Building a sizing protocol you can follow without emotion",
    ],
    tags=["risk", "sizing", "portfolio", "discipline"],
)

_TRAILING_STOPS = LearningTopic(
    id="trailing_stops",
    title="Trailing Stops: How Winners Stay Winners",
    category="risk_management",
    hook=(
        "The hardest part of a winning trade is not finding it. "
        "It is keeping the gain."
    ),
    key_concept=(
        "A trailing stop moves upward with price, locking in profit while giving the trade room to breathe. "
        "Without one, a 60% winner can round-trip to breakeven on a single reversal. "
        "Trailing stop discipline means you accept smaller exits in exchange for never giving back an entire move."
    ),
    example=(
        "Every open position in our portfolio has a trailing stop calculated from its highest close. "
        "When that stop is hit, the system exits — no debate, no negotiation. "
        "We have watched positions gap down overnight and walked away with capital intact because the protocol was already set."
    ),
    engagement_question="Do you use trailing stops — or do you rely on instinct to know when to sell?",
    note_template=(
        "The hardest part of a winning trade is not finding it. "
        "It is keeping the gain.\n\n"
        "Every doctor knows that discharging a patient too early invites a relapse. "
        "But keeping them indefinitely is not the answer either. "
        "Trailing stops work the same way. They give a position room to recover from "
        "normal volatility while drawing a hard line against catastrophic reversal.\n\n"
        "A trailing stop rises with price. It never moves down. "
        "When the market takes back enough of the gain, the exit triggers automatically. "
        "No debate, no emotional override, no hoping it comes back.\n\n"
        "Every open position in our portfolio has a trailing stop calculated from its highest close. "
        "We have watched names gap down overnight and walked away with capital intact "
        "because the protocol was already set.\n\n"
        "Without this discipline, a 60% winner can round-trip to breakeven in a single reversal. "
        "We would rather exit early and keep the profit than ride the whole wave and give it all back.\n\n"
        "Do you use trailing stops — or do you rely on instinct to know when to sell?\n\n"
        "Not financial advice. Informational only."
    ),
    post_outline=[
        "Why most investors give back their gains",
        "How trailing stops work: the mechanics",
        "Setting the right distance: too tight vs too loose",
        "The emotional trap: overriding your own stops",
        "Building stop discipline into your routine",
    ],
    tags=["risk", "stops", "exits", "discipline"],
)

_MAX_DRAWDOWN = LearningTopic(
    id="max_drawdown",
    title="The Math of Drawdowns: Why -50% Needs +100%",
    category="risk_management",
    hook=(
        "A 50% loss does not need a 50% gain to recover. "
        "It needs 100%. And that math is the reason most portfolios never come back."
    ),
    key_concept=(
        "Drawdowns are asymmetric. A 33% loss requires a 50% gain just to get back to even. "
        "A 50% loss demands a 100% recovery. "
        "This is why risk management is not optional — it is the single most important variable in long-term compounding."
    ),
    example=(
        "Our screening system uses structural exit signals and trailing stop discipline to limit drawdowns. "
        "We would rather exit a position early and re-enter when the data improves "
        "than sit through a 40% decline waiting for the thesis to play out."
    ),
    engagement_question="What is the worst drawdown you have experienced — and what did it teach you?",
    note_template=(
        "A 50% loss does not need a 50% gain to recover. "
        "It needs 100%. And that math is the reason most portfolios never come back.\n\n"
        "In the emergency room, triage exists because not every patient can be saved with the same urgency. "
        "Drawdowns work the same way. A 10% loss is a bruise — recoverable in a good quarter. "
        "A 33% loss requires a 50% gain. A 50% loss demands a full double. "
        "And a 75% loss? You need a 300% return just to break even.\n\n"
        "This asymmetry is why capital preservation comes before capital appreciation. Always.\n\n"
        "Our screening system uses structural exit signals and trailing stop discipline "
        "specifically to keep drawdowns manageable. "
        "We would rather exit early and re-enter when the data improves "
        "than sit through a 40% decline hoping the thesis eventually plays out.\n\n"
        "Compounding only works if the capital is still there to compound.\n\n"
        "What is the worst drawdown you have experienced — and what did it teach you?\n\n"
        "Not financial advice. Informational only."
    ),
    post_outline=[
        "The asymmetry of losses: why math works against you",
        "A drawdown table every investor should memorize",
        "How professional managers think about maximum drawdown",
        "Techniques to limit drawdown without sacrificing upside",
        "Why the best offense in investing is a good defense",
    ],
    tags=["risk", "drawdown", "math", "compounding"],
)

_CASH_RESERVE = LearningTopic(
    id="cash_reserve",
    title="Cash Is Ammunition, Not Laziness",
    category="risk_management",
    hook=(
        "The market punishes the fully invested and rewards the patient. "
        "Cash is not a drag on performance. It is dry powder."
    ),
    key_concept=(
        "Holding cash means you can act when a high-conviction opportunity appears without selling existing winners to fund it. "
        "It also means a market correction is a shopping trip, not a crisis. "
        "The best traders treat cash as a strategic position, not idle capital."
    ),
    example=(
        "Our portfolio protocol maintains a cash reserve at all times. "
        "When our screening system produces zero signals — which happens regularly — we do not chase. "
        "We wait. And when the next cluster of cleared signals arrives, we deploy with conviction."
    ),
    engagement_question="How much cash do you keep on the sidelines — and how do you decide?",
    note_template=(
        "The market punishes the fully invested and rewards the patient. "
        "Cash is not a drag on performance. It is dry powder.\n\n"
        "In medicine, we always keep reserves. Blood banks do not run at zero inventory. "
        "Hospitals stock emergency supplies before the emergency arrives. "
        "Your portfolio deserves the same discipline.\n\n"
        "Holding cash means you can act when a high-conviction setup clears your screening system "
        "without liquidating existing winners to fund it. "
        "It means a market correction is a shopping trip, not a crisis. "
        "It means you never have to chase a name at the top just because you feel underinvested.\n\n"
        "Our portfolio protocol maintains a cash reserve at all times. "
        "When the system produces zero signals — which happens regularly — we do not chase. "
        "We wait. And when the next cluster of cleared signals arrives, we deploy with full conviction.\n\n"
        "Patience is not passive. It is the most aggressive thing you can do when the data says wait.\n\n"
        "How much cash do you keep on the sidelines — and how do you decide?\n\n"
        "Not financial advice. Informational only."
    ),
    post_outline=[
        "The myth of being 'fully invested'",
        "Cash as a strategic allocation, not dead money",
        "When to deploy cash: conviction vs FOMO",
        "How much is enough: the reserve ratio",
        "The compounding advantage of dry powder during corrections",
    ],
    tags=["risk", "cash", "patience", "allocation"],
)


# =============================================================================
# TOPIC DEFINITIONS — MOMENTUM (4)
# =============================================================================

_STRUCTURAL_MOMENTUM = LearningTopic(
    id="structural_momentum",
    title="What Structural Momentum Actually Means",
    category="momentum",
    hook=(
        "A stock going up is not the same as a stock in structural momentum. "
        "One is noise. The other is a diagnosis."
    ),
    key_concept=(
        "Structural momentum means the underlying trend architecture has shifted — not just the price. "
        "It is the difference between a fever spike and a chronic condition. "
        "When structure confirms, the probability of continuation rises dramatically because the market's internal framework is aligned."
    ),
    example=(
        "Our screening system does not trigger on price alone. "
        "It waits for structural confirmation across multiple independent indicators before clearing a signal. "
        "That confirmation is what separates a fleeting rally from a tradeable trend."
    ),
    engagement_question="How do you distinguish between real momentum and a dead-cat bounce?",
    note_template=(
        "A stock going up is not the same as a stock in structural momentum. "
        "One is noise. The other is a diagnosis.\n\n"
        "In medicine, a single elevated lab value does not confirm a disease. "
        "You need pattern recognition across multiple data points — history, imaging, bloodwork — before you commit to treatment. "
        "Markets work the same way.\n\n"
        "Structural momentum means the underlying trend architecture has shifted. "
        "Not just price. Not just volume. The framework beneath the candles has reorganized "
        "in a way that favors continuation over reversal.\n\n"
        "Our screening system does not trigger on price alone. "
        "It waits for structural confirmation across multiple independent indicators "
        "before clearing any signal. That confirmation is what separates a one-day rally "
        "from a move worth committing capital to.\n\n"
        "Chasing green candles is easy. Diagnosing real structural momentum takes patience and a system.\n\n"
        "How do you distinguish between real momentum and a dead-cat bounce?\n\n"
        "Not financial advice. Informational only."
    ),
    post_outline=[
        "Price movement vs structural momentum: what is the difference",
        "The medical analogy: diagnosis requires multiple data points",
        "How structural confirmation improves trade probability",
        "Why most retail traders get faked out by noise",
        "Building a momentum framework you can trust",
    ],
    tags=["momentum", "structure", "trends", "signals"],
)

_INSTITUTIONAL_ACCUMULATION = LearningTopic(
    id="institutional_accumulation",
    title="Reading Institutional Accumulation Before the Crowd",
    category="momentum",
    hook=(
        "By the time a stock makes headlines, the institutions are already in. "
        "The question is whether you can spot the accumulation before the press release."
    ),
    key_concept=(
        "Institutional accumulation leaves footprints in price and volume data long before it shows up in 13F filings. "
        "These patterns — subtle divergences between price and underlying flow — are invisible to casual observers "
        "but systematic screening can detect them early."
    ),
    example=(
        "Our screening system looks for institutional accumulation divergence as one of its core signals. "
        "When the data shows quiet, persistent buying beneath a flat or declining price, "
        "that is the market equivalent of a patient whose vitals are improving before they look better."
    ),
    engagement_question="Have you ever noticed accumulation in a stock before it broke out — what tipped you off?",
    note_template=(
        "By the time a stock makes headlines, the institutions are already in. "
        "The question is whether you can spot the accumulation before the press release.\n\n"
        "Think of institutional buying like internal bleeding — invisible on the surface, "
        "but the instruments pick it up immediately. "
        "Large funds do not buy in a single day. They accumulate over weeks, "
        "carefully absorbing supply without spiking the price. "
        "The chart looks quiet. The volume looks normal. But underneath, the ownership structure is shifting.\n\n"
        "Our screening system looks for this exact divergence — institutional accumulation patterns "
        "that appear long before the stock makes anyone's watchlist. "
        "When the data shows quiet, persistent buying beneath a flat or declining price, "
        "that is the market equivalent of improving vitals before the patient looks better.\n\n"
        "By the time the breakout is obvious, the smart money has been positioned for weeks.\n\n"
        "Have you ever noticed accumulation in a stock before it broke out — what tipped you off?\n\n"
        "Not financial advice. Informational only."
    ),
    post_outline=[
        "What institutional accumulation looks like in price data",
        "Why 13F filings are always 45 days too late",
        "The divergence signal: quiet buying beneath a flat chart",
        "How systematic screening catches what human eyes miss",
        "Case study: accumulation detected before the breakout",
    ],
    tags=["momentum", "institutions", "accumulation", "flow"],
)

_SECTOR_ROTATION = LearningTopic(
    id="sector_rotation",
    title="Sector Rotation: Follow the Money, Not the Headlines",
    category="momentum",
    hook=(
        "Capital does not disappear during selloffs. "
        "It rotates. And if you know where it is going, you can be there first."
    ),
    key_concept=(
        "Sector rotation is the institutional habit of moving capital from overvalued or decelerating sectors into undervalued or accelerating ones. "
        "It creates a predictable rhythm of leadership changes that systematic screening can identify. "
        "Following the rotation is more reliable than trying to predict which individual stock will move next."
    ),
    example=(
        "Our sector flow analysis identifies which themes are attracting institutional capital "
        "and which are seeing outflows. "
        "When a sector shifts from cold to warming, the stocks within it tend to move together — "
        "and the best-positioned names in that group are where multibagger potential lives."
    ),
    engagement_question="What sector rotation are you seeing right now — and how are you positioning for it?",
    note_template=(
        "Capital does not disappear during selloffs. "
        "It rotates. And if you know where it is going, you can be there first.\n\n"
        "Doctors study referral patterns to understand where patients flow through a health system. "
        "Investors should study capital flows the same way. "
        "Sector rotation is the institutional habit of moving money from overvalued or decelerating themes "
        "into undervalued or accelerating ones.\n\n"
        "This creates a rhythm. Energy leads for a quarter, then capital rotates into technology. "
        "Infrastructure heats up while biotech cools off. "
        "The individual stocks change, but the pattern repeats.\n\n"
        "Our sector flow analysis identifies which themes are attracting institutional capital "
        "and which are seeing outflows. "
        "When a sector shifts from cold to warming, the stocks within it tend to move together. "
        "The best-positioned names in that group are where the asymmetric upside lives.\n\n"
        "Do not fight the flow. Diagnose it, then position accordingly.\n\n"
        "What sector rotation are you seeing right now — and how are you positioning for it?\n\n"
        "Not financial advice. Informational only."
    ),
    post_outline=[
        "What sector rotation is and why it matters for stock pickers",
        "The institutional flow cycle: how capital moves between themes",
        "Identifying rotation early with sector flow analysis",
        "Why individual stock selection improves inside a hot sector",
        "Positioning for the next rotation before it becomes consensus",
    ],
    tags=["momentum", "sectors", "rotation", "flow", "themes"],
)

_BREADTH_SIGNALS = LearningTopic(
    id="breadth_signals",
    title="Market Breadth: The Rally's Hidden Vital Sign",
    category="momentum",
    hook=(
        "A market index can make new highs while most stocks are falling. "
        "Breadth tells you whether the rally has a pulse or is running on life support."
    ),
    key_concept=(
        "Market breadth measures how many stocks are participating in a move. "
        "A narrow rally led by five mega-caps is fragile; a broad rally where hundreds of names are advancing is durable. "
        "Breadth deterioration is one of the earliest warning signs that a trend is about to fail."
    ),
    example=(
        "When our screening system is producing a high number of signals across multiple sectors, "
        "that is a breadth confirmation — the rally has broad participation. "
        "When signals dry up even as indices climb, we treat it as a warning sign and tighten our approach."
    ),
    engagement_question="Are you watching breadth — or just the headline index number?",
    note_template=(
        "A market index can make new highs while most stocks are falling. "
        "Breadth tells you whether the rally has a pulse or is running on life support.\n\n"
        "A doctor does not diagnose cardiac health by checking one ventricle. "
        "You look at the whole system — valves, rhythm, output. "
        "Market breadth works the same way. "
        "A narrow rally led by five mega-caps is fragile. "
        "A broad rally where hundreds of names are advancing across sectors is durable.\n\n"
        "Breadth deterioration is one of the earliest warning signs that a trend is running out of oxygen. "
        "The index can keep climbing on the back of a few heavyweights, "
        "but underneath, the majority of stocks are already rolling over.\n\n"
        "When our screening system produces a high number of signals across multiple sectors, "
        "that is a breadth confirmation. "
        "When signals dry up even as indices climb, we treat it as a warning and tighten our criteria.\n\n"
        "The headline number can lie. Breadth does not.\n\n"
        "Are you watching breadth — or just the headline index number?\n\n"
        "Not financial advice. Informational only."
    ),
    post_outline=[
        "What market breadth is and why most retail traders ignore it",
        "Narrow vs broad rallies: a fragility diagnosis",
        "How breadth deterioration precedes market tops",
        "Using your screening system as a breadth indicator",
        "Adjusting strategy based on breadth conditions",
    ],
    tags=["momentum", "breadth", "market", "health", "participation"],
)


# =============================================================================
# TOPIC DEFINITIONS — FUNDAMENTALS (4)
# =============================================================================

_CATALYST_INVESTING = LearningTopic(
    id="catalyst_investing",
    title="Catalysts Over Valuations: What Moves Growth Stocks",
    category="fundamentals",
    hook=(
        "Cheap stocks can stay cheap forever. "
        "Stocks with upcoming catalysts move — and they move fast."
    ),
    key_concept=(
        "For growth stocks, the next event matters more than the current price-to-earnings ratio. "
        "Earnings reports, FDA approvals, contract wins, and macro policy shifts create inflection points. "
        "Identifying these catalysts before the market fully prices them is the edge."
    ),
    example=(
        "Our screening system evaluates upcoming catalysts as part of its fundamental screening process. "
        "A stock with structural momentum and a catalyst within 90 days "
        "is a higher-probability setup than momentum alone. "
        "The catalyst is the spark. The momentum is the fuel."
    ),
    engagement_question="What upcoming catalyst are you most excited about in your portfolio?",
    note_template=(
        "Cheap stocks can stay cheap forever. "
        "Stocks with upcoming catalysts move — and they move fast.\n\n"
        "A patient can have textbook-perfect bloodwork and still be deteriorating. "
        "The lab results are backward-looking. What matters is what happens next — "
        "the upcoming surgery, the new treatment protocol, the environmental change.\n\n"
        "Growth stocks work the same way. Valuation ratios tell you where a company has been. "
        "Catalysts tell you where it is going. "
        "Earnings reports, regulatory approvals, contract announcements, policy shifts — "
        "these are the inflection points that create sudden repricing.\n\n"
        "Our screening system evaluates upcoming catalysts as part of its fundamental analysis. "
        "A stock with structural momentum and a catalyst within 90 days "
        "is a meaningfully higher-probability setup than momentum alone. "
        "The catalyst is the spark. The momentum is the fuel.\n\n"
        "Stop asking what a stock is worth today. Start asking what event could change its worth tomorrow.\n\n"
        "What upcoming catalyst are you most excited about in your portfolio?\n\n"
        "Not financial advice. Informational only."
    ),
    post_outline=[
        "Why valuation alone is a poor timing tool for growth stocks",
        "The anatomy of a catalyst: types and impact",
        "How to identify catalysts before the market prices them",
        "Combining momentum with catalyst analysis",
        "The danger of catalyst investing without risk management",
    ],
    tags=["fundamentals", "catalysts", "growth", "events"],
)

_REVENUE_ACCELERATION = LearningTopic(
    id="revenue_acceleration",
    title="Revenue Acceleration: The Inflection Point Signal",
    category="fundamentals",
    hook=(
        "Revenue growth is good. Revenue growth that is accelerating is a completely different animal. "
        "That inflection is where multibaggers are born."
    ),
    key_concept=(
        "Revenue acceleration means the rate of growth is increasing — not just growing, but growing faster. "
        "This inflection attracts institutional capital because it signals an expanding addressable market or improving competitive position. "
        "Stocks that show sequential acceleration in revenue growth are disproportionately represented among multibaggers."
    ),
    example=(
        "When our fundamental screening process identifies a company whose revenue growth has accelerated "
        "for two or more consecutive quarters, that name gets elevated in our analysis. "
        "It is the difference between a patient who is stable and a patient who is actively recovering."
    ),
    engagement_question="What is a stock you own where revenue growth is actually accelerating — not just growing?",
    note_template=(
        "Revenue growth is good. Revenue growth that is accelerating is a completely different animal. "
        "That inflection is where multibaggers are born.\n\n"
        "In medicine, we do not just check whether a patient is alive. "
        "We check whether they are improving — and whether the rate of improvement is increasing. "
        "A patient whose recovery is accelerating is on a fundamentally different trajectory "
        "than one who is stable but flat.\n\n"
        "Revenue acceleration means the growth rate itself is growing. "
        "Quarter over quarter, the company is expanding its market share faster than before. "
        "This inflection attracts institutional capital because it signals something structural has changed — "
        "a larger addressable market, a competitive moat widening, or a product cycle taking hold.\n\n"
        "When our fundamental screening identifies a company whose revenue growth has accelerated "
        "for consecutive quarters, that name gets elevated. "
        "Stocks showing this pattern are disproportionately represented among the biggest winners.\n\n"
        "What is a stock you own where revenue growth is actually accelerating — not just growing?\n\n"
        "Not financial advice. Informational only."
    ),
    post_outline=[
        "Revenue growth vs revenue acceleration: the critical distinction",
        "Why institutional money follows accelerating fundamentals",
        "Identifying inflection points in quarterly reports",
        "The multibagger connection: acceleration as a leading indicator",
        "Combining revenue acceleration with momentum screening",
    ],
    tags=["fundamentals", "revenue", "growth", "inflection", "multibagger"],
)

_THEME_ALIGNMENT = LearningTopic(
    id="theme_alignment",
    title="Theme Alignment: How Sectors Amplify Individual Stocks",
    category="fundamentals",
    hook=(
        "A great stock in a dead sector is a lonely trade. "
        "A great stock inside a sector with institutional tailwinds is a force multiplier."
    ),
    key_concept=(
        "Sector themes act as amplifiers. When institutional capital is flowing into a theme — "
        "infrastructure, energy transition, defense modernization — every well-positioned stock in that theme benefits. "
        "Aligning individual stock picks with active sector themes increases both the probability of success and the magnitude of the move."
    ),
    example=(
        "Our screening system does not evaluate stocks in isolation. "
        "It maps every signal to an active sector theme and scores the alignment. "
        "A stock that passes all technical and fundamental criteria but sits in a cold theme "
        "gets treated differently than one riding a sector with strong institutional flows."
    ),
    engagement_question="What sector theme do you think is most underappreciated right now?",
    note_template=(
        "A great stock in a dead sector is a lonely trade. "
        "A great stock inside a sector with institutional tailwinds is a force multiplier.\n\n"
        "A surgeon can be world-class, but without the right team, the right equipment, "
        "and the right environment, outcomes suffer. Context matters. "
        "Sector themes are the operating environment for your stock picks.\n\n"
        "When institutional capital is flowing into a theme — infrastructure, defense modernization, "
        "energy transition — every well-positioned stock in that group benefits from the rising tide. "
        "Flows lift the entire sector. The best-positioned names within it get lifted the most.\n\n"
        "Our screening system maps every signal to an active sector theme and scores the alignment. "
        "A stock that passes all criteria but sits in a cold theme gets treated differently "
        "than one riding a sector with strong institutional flows. "
        "Theme alignment is the difference between swimming with the current and swimming against it.\n\n"
        "What sector theme do you think is most underappreciated right now?\n\n"
        "Not financial advice. Informational only."
    ),
    post_outline=[
        "Why individual stock analysis is incomplete without sector context",
        "How institutional theme flows amplify stock-level moves",
        "Identifying hot vs cold themes in real time",
        "Scoring theme alignment: what our system looks for",
        "When to avoid a great stock because the sector is against it",
    ],
    tags=["fundamentals", "themes", "sectors", "alignment", "flow"],
)

_SMALL_CAP_EDGE = LearningTopic(
    id="small_cap_edge",
    title="The Small-Cap Edge: Asymmetric Upside the Index Cannot Offer",
    category="fundamentals",
    hook=(
        "You will never find a 10x return in a mega-cap. "
        "That math only works below a certain market capitalization."
    ),
    key_concept=(
        "Small-cap stocks offer asymmetric upside because they start from a lower base and can grow into their potential. "
        "A $500M company doubling its revenue is a different event than Apple doubling its revenue. "
        "The tradeoff is higher volatility and less analyst coverage, which is exactly why systematic screening provides an edge."
    ),
    example=(
        "Our screening system filters 1,800 stocks specifically to find names with multibagger potential. "
        "These are not household brands. They are companies where institutional accumulation is building "
        "before the broader market has noticed. "
        "The inefficiency in small-cap coverage is the opportunity."
    ),
    engagement_question="What is your best small-cap find that the market was ignoring?",
    note_template=(
        "You will never find a 10x return in a mega-cap. "
        "That math only works below a certain market capitalization.\n\n"
        "In medicine, the biggest breakthroughs do not come from tweaking established treatments. "
        "They come from early-stage research that nobody is paying attention to yet. "
        "Small-cap stocks are the early-stage pipeline of the market.\n\n"
        "A $500M company doubling its revenue is a company-altering event that reprices the stock. "
        "A mega-cap doubling revenue is a rounding error on its existing valuation. "
        "The asymmetry is mathematical. Smaller base, bigger potential percentage move.\n\n"
        "The tradeoff is real — higher volatility, less analyst coverage, wider spreads. "
        "But that is exactly why systematic screening provides an edge. "
        "Our system filters 1,800 stocks specifically to find names where institutional accumulation "
        "is building before the broader market has noticed.\n\n"
        "The inefficiency in small-cap coverage is not a bug. It is the opportunity.\n\n"
        "What is your best small-cap find that the market was ignoring?\n\n"
        "Not financial advice. Informational only."
    ),
    post_outline=[
        "The math of multibaggers: why size matters",
        "Small-cap volatility as opportunity, not risk",
        "The coverage gap: why fewer analysts means more mispricing",
        "Systematic screening in the small-cap universe",
        "Risk management considerations for smaller names",
    ],
    tags=["fundamentals", "small-cap", "multibagger", "asymmetry", "growth"],
)


# =============================================================================
# TOPIC DEFINITIONS — PSYCHOLOGY (4)
# =============================================================================

_PATIENCE_OVER_FOMO = LearningTopic(
    id="patience_over_fomo",
    title="Why the Best Traders Do Nothing Most of the Time",
    category="psychology",
    hook=(
        "The most profitable action in the market is often no action at all. "
        "Doing nothing when the data says wait is the hardest skill in investing."
    ),
    key_concept=(
        "Overtrading is the silent killer of retail portfolios. "
        "Professional traders spend most of their time waiting for setups that match their criteria. "
        "Every trade that does not meet your system's requirements is a leak in your compound returns."
    ),
    example=(
        "Our screening system regularly produces zero signals in a given week. "
        "That is not a failure — it is the system working as designed. "
        "We would rather miss ten mediocre setups than take one bad one that damages the portfolio."
    ),
    engagement_question="When was the last time you made money by doing absolutely nothing?",
    note_template=(
        "The most profitable action in the market is often no action at all. "
        "Doing nothing when the data says wait is the hardest skill in investing.\n\n"
        "A surgeon who operates on every patient who walks in is not a good surgeon. "
        "They are a liability. The discipline to say 'this patient does not need surgery today' "
        "is what separates competence from recklessness.\n\n"
        "Overtrading is the silent killer of retail portfolios. "
        "Every position that does not meet your criteria is a leak in your compound returns. "
        "Commission, spread, mental bandwidth, opportunity cost — it all adds up.\n\n"
        "Our screening system regularly produces zero signals in a given week. "
        "We scan 1,800 stocks and sometimes none of them clear all the criteria. "
        "That is not a failure. That is the system working as designed.\n\n"
        "The amateur feels anxious with cash on the sidelines. "
        "The professional feels anxious with capital in a trade that does not meet the standard.\n\n"
        "When was the last time you made money by doing absolutely nothing?\n\n"
        "Not financial advice. Informational only."
    ),
    post_outline=[
        "The overtrading epidemic: why retail investors trade too often",
        "The cost of unnecessary trades on compounding",
        "How systematic screening enforces patience",
        "The psychology of sitting still when everyone is trading",
        "Redefining productivity in investing: less is more",
    ],
    tags=["psychology", "patience", "overtrading", "discipline", "FOMO"],
)

_SYSTEMATIC_DISCIPLINE = LearningTopic(
    id="systematic_discipline",
    title="Removing Emotion with a Rules-Based System",
    category="psychology",
    hook=(
        "Your brain is the worst trading tool you own. "
        "A system that does not feel fear, greed, or FOMO will always outperform your instincts over time."
    ),
    key_concept=(
        "Systematic investing replaces emotional decision-making with repeatable, evidence-based protocols. "
        "The goal is not to eliminate intuition entirely but to ensure that every entry and exit is governed by rules "
        "that were defined before the emotion of the moment kicked in."
    ),
    example=(
        "Our screening system generates signals based on data, not feelings. "
        "Every entry has criteria. Every exit has a trigger. Every position has a size. "
        "We defined these rules during calm markets so we can execute them during chaotic ones."
    ),
    engagement_question="Do you follow a system — or are you still trading on instinct?",
    note_template=(
        "Your brain is the worst trading tool you own. "
        "A system that does not feel fear, greed, or FOMO will always outperform your instincts over time.\n\n"
        "Medicine abandoned intuition-based practice decades ago. "
        "Doctors used to prescribe based on experience and gut feeling. "
        "Now we use evidence-based protocols, clinical trials, and peer-reviewed data. "
        "The result? Dramatically better outcomes.\n\n"
        "Investing is still stuck in the intuition era for most retail participants. "
        "They buy because it feels right. They sell because they panic. "
        "They hold because admitting a mistake hurts. Every one of these is an emotional decision "
        "masquerading as analysis.\n\n"
        "Our screening system generates signals based on data, not feelings. "
        "Every entry has criteria. Every exit has a trigger. Every position has a size. "
        "We defined these rules during calm markets so we can execute them during chaotic ones.\n\n"
        "No ego, just execution.\n\n"
        "Do you follow a system — or are you still trading on instinct?\n\n"
        "Not financial advice. Informational only."
    ),
    post_outline=[
        "Why human brains are poorly designed for investing",
        "The evidence-based revolution: lessons from medicine",
        "What a rules-based investing system looks like in practice",
        "Defining rules in calm markets for chaotic execution",
        "The discipline loop: system, execute, review, refine",
    ],
    tags=["psychology", "discipline", "system", "emotion", "rules"],
)

_LOSS_ACCEPTANCE = LearningTopic(
    id="loss_acceptance",
    title="Controlled Losses Are the Cost of Doing Business",
    category="psychology",
    hook=(
        "If you cannot accept a controlled loss, you will eventually experience an uncontrolled one. "
        "Every professional trader understands this."
    ),
    key_concept=(
        "Losses are not failures. They are the cost of participating in an uncertain system. "
        "The difference between a professional and an amateur is not win rate — it is how they handle the inevitable losses. "
        "Controlled, systematic exits preserve capital for the next opportunity."
    ),
    example=(
        "When our screening system triggers an exit, we do not negotiate with the data. "
        "The position is closed. The capital is preserved. "
        "We have seen that disciplined exits on small losses create the runway "
        "for the big winners to compound."
    ),
    engagement_question="How do you handle a loss — do you let the system decide, or does emotion take over?",
    note_template=(
        "If you cannot accept a controlled loss, you will eventually experience an uncontrolled one. "
        "Every professional trader understands this.\n\n"
        "In surgery, complications happen. The question is never whether something will go wrong — "
        "it is whether the team is prepared to respond systematically when it does. "
        "A controlled complication managed with protocol is vastly different from an uncontrolled crisis.\n\n"
        "Losses in investing work the same way. "
        "They are not failures. They are the cost of participating in an uncertain system. "
        "A small, planned exit preserves capital for the next setup. "
        "An unplanned exit after a 50% decline destroys it.\n\n"
        "When our screening system triggers an exit, we do not negotiate with the data. "
        "The position is closed. The capital is preserved. "
        "Disciplined exits on small losses create the runway for the big winners to compound.\n\n"
        "The professional's edge is not avoiding losses. It is managing them.\n\n"
        "How do you handle a loss — do you let the system decide, or does emotion take over?\n\n"
        "Not financial advice. Informational only."
    ),
    post_outline=[
        "Why losses are inevitable and how to reframe them",
        "The surgery analogy: planned response vs uncontrolled crisis",
        "How holding losers destroys compound returns",
        "Building an exit protocol before the loss happens",
        "The emotional freedom of systematic risk management",
    ],
    tags=["psychology", "losses", "exits", "acceptance", "discipline"],
)

_COMPOUNDING_MATH = LearningTopic(
    id="compounding_math",
    title="The Math of Multibaggers: Why 10x Returns Start with Discipline",
    category="psychology",
    hook=(
        "Everyone wants a 10x return. Almost nobody has the discipline to let a winner run long enough to become one."
    ),
    key_concept=(
        "Compounding requires time, reinvestment, and the discipline to not interrupt the process. "
        "A stock that returns 25% per year for 10 years is a 9.3x return. "
        "But only if you hold it, do not panic sell during corrections, and let the math do the work."
    ),
    example=(
        "Our portfolio includes positions that started as modest gains and compounded into significant winners. "
        "The key was not genius stock selection. "
        "It was the trailing stop discipline that kept us in the trade during normal volatility "
        "while protecting against structural breakdowns."
    ),
    engagement_question="What is your longest-held winning position — and what kept you from selling too early?",
    note_template=(
        "Everyone wants a 10x return. Almost nobody has the discipline "
        "to let a winner run long enough to become one.\n\n"
        "In medicine, the most effective treatments are often the slow ones. "
        "Antibiotics take a full course. Physical therapy takes months. "
        "The patient who stops treatment early because they feel better "
        "is the one who relapses.\n\n"
        "Compounding works the same way. A stock returning 25% per year for 10 years "
        "is a 9.3x return. But only if you hold it. "
        "Only if you do not panic during the inevitable 15% corrections along the way. "
        "Only if you let the math do the work.\n\n"
        "Our portfolio includes positions that started as modest gains and compounded into significant winners. "
        "The key was not genius stock selection. "
        "It was trailing stop discipline that kept us in during normal volatility "
        "while protecting against structural breakdowns.\n\n"
        "Compounding rewards the patient and punishes the impatient. Every single time.\n\n"
        "What is your longest-held winning position — and what kept you from selling too early?\n\n"
        "Not financial advice. Informational only."
    ),
    post_outline=[
        "The compounding table most investors have never seen",
        "Why 10x returns are built on boring consistency",
        "The interruption cost: how selling too early kills compounding",
        "Trailing stops as compounding enablers, not limiters",
        "The psychology of holding through volatility",
    ],
    tags=["psychology", "compounding", "multibagger", "patience", "math"],
)


# =============================================================================
# TOPIC DEFINITIONS — STRATEGY (4)
# =============================================================================

_SCREENING_ADVANTAGE = LearningTopic(
    id="screening_advantage",
    title="Systematic Screening Finds What Human Eyes Miss",
    category="strategy",
    hook=(
        "You cannot manually analyze 1,800 stocks every week. "
        "But a screening system can — and it will never get tired, distracted, or biased."
    ),
    key_concept=(
        "Systematic screening eliminates the coverage gap that causes most retail investors to miss opportunities. "
        "A human can follow 20-30 stocks. A screening system evaluates the entire universe simultaneously, "
        "applying the same criteria without fatigue or recency bias."
    ),
    example=(
        "Our screening system filters 1,800 US stocks through multiple independent criteria every single week. "
        "The names that clear all gates are often ones that no analyst is covering and no subreddit is discussing. "
        "That is the edge — systematic coverage of the entire playing field."
    ),
    engagement_question="How many stocks can you realistically follow — and what are you missing?",
    note_template=(
        "You cannot manually analyze 1,800 stocks every week. "
        "But a screening system can — and it will never get tired, distracted, or biased.\n\n"
        "A radiologist reviewing scans uses systematic protocols to ensure nothing gets missed. "
        "They do not skip images because they are hungry. "
        "They do not focus on the interesting cases and ignore the routine ones. "
        "Every scan gets the same level of scrutiny.\n\n"
        "That is the edge of systematic screening. "
        "A human can follow 20, maybe 30 stocks with any depth. "
        "Our system evaluates 1,800 simultaneously, applying the same criteria to every single name "
        "without fatigue, without recency bias, without emotion.\n\n"
        "The stocks that clear all the criteria are often ones that no analyst is covering "
        "and no subreddit is discussing. By the time the crowd discovers them, "
        "the institutional accumulation has been underway for weeks.\n\n"
        "Coverage is an edge. Systematic coverage is an unfair advantage.\n\n"
        "How many stocks can you realistically follow — and what are you missing?\n\n"
        "Not financial advice. Informational only."
    ),
    post_outline=[
        "The coverage gap: why most investors miss most opportunities",
        "How systematic screening solves the human bandwidth problem",
        "The radiology analogy: protocol-driven analysis",
        "What a 1,800-stock weekly scan actually looks like",
        "Finding alpha in the names nobody is watching",
    ],
    tags=["strategy", "screening", "system", "coverage", "edge"],
)

_THEME_SURFING = LearningTopic(
    id="theme_surfing",
    title="Riding Sector Themes from Identification to Peak Momentum",
    category="strategy",
    hook=(
        "The best trades are not isolated stock picks. "
        "They are individual bets aligned with a macro theme that is accelerating."
    ),
    key_concept=(
        "Theme surfing means identifying a sector trend early, selecting the best-positioned stocks within it, "
        "and riding the wave until momentum deteriorates. "
        "The theme provides the wind. The stock selection determines how fast you sail."
    ),
    example=(
        "Our sector flow analysis scores themes from high conviction down to avoid. "
        "When a theme reaches peak institutional flow, the individual stocks within it "
        "become the highest-probability setups in our screening system. "
        "When the theme cools, the system rotates us out before the crowd notices."
    ),
    engagement_question="What theme are you surfing right now — and how do you know when to paddle out?",
    note_template=(
        "The best trades are not isolated stock picks. "
        "They are individual bets aligned with a macro theme that is accelerating.\n\n"
        "Think of it like an epidemic. When a disease is spreading, "
        "you do not treat patients in isolation. You study the epidemiology — "
        "where is it spreading, how fast, and which populations are most affected. "
        "Then you allocate resources accordingly.\n\n"
        "Theme surfing works the same way. "
        "Identify the sector trend early. Select the best-positioned stocks within it. "
        "Ride the wave until momentum deteriorates. "
        "The theme provides the wind. The stock selection determines how fast you sail.\n\n"
        "Our sector flow analysis scores themes and ranks them by institutional conviction. "
        "When a theme reaches peak flow, the individual stocks within it "
        "become our highest-probability setups. "
        "When the theme cools, the system rotates us out before the crowd notices.\n\n"
        "Do not just pick stocks. Pick the wave first, then choose your board.\n\n"
        "What theme are you surfing right now — and how do you know when to paddle out?\n\n"
        "Not financial advice. Informational only."
    ),
    post_outline=[
        "What theme investing is and why it outperforms random stock picking",
        "The lifecycle of a sector theme: early, mid, peak, decline",
        "How to identify themes before they become consensus",
        "Selecting the best stocks within a hot theme",
        "Exit signals: knowing when the wave is breaking",
    ],
    tags=["strategy", "themes", "sectors", "surfing", "momentum"],
)

_WHEN_TO_SELL = LearningTopic(
    id="when_to_sell",
    title="The Hardest Decision: Knowing When to Exit",
    category="strategy",
    hook=(
        "Everyone teaches you how to buy. "
        "Almost nobody teaches you how to sell. "
        "And the sell decision is where most of the money is made or lost."
    ),
    key_concept=(
        "Exit strategy is more important than entry strategy because it determines whether paper gains become real gains. "
        "A systematic exit — whether trailing stop or structural exit signal — removes the guesswork. "
        "The goal is not to sell at the top. It is to sell at a level that locks in the majority of the move."
    ),
    example=(
        "Our screening system generates structural exit signals that tell us when the trend has changed, "
        "independent of our opinion. Combined with trailing stop discipline, "
        "we have a two-layer exit system that catches both slow deterioration and sudden reversals."
    ),
    engagement_question="What is your sell strategy — and when was the last time you actually followed it?",
    note_template=(
        "Everyone teaches you how to buy. "
        "Almost nobody teaches you how to sell. "
        "And the sell decision is where most of the money is made or lost.\n\n"
        "A doctor who is excellent at diagnosis but terrible at discharge planning "
        "creates a different kind of harm. "
        "Knowing when to let go — when the treatment is complete, "
        "when the condition has changed — is the other half of the skill.\n\n"
        "Exit strategy is more important than entry strategy "
        "because it determines whether paper gains become real gains. "
        "Without a defined exit, you are relying on emotion to tell you when to sell. "
        "And emotion will always either sell too early out of fear or too late out of greed.\n\n"
        "Our screening system generates structural exit signals that indicate when the trend has changed, "
        "independent of our opinion. Combined with trailing stop discipline, "
        "we have a two-layer exit system that handles both slow deterioration and sudden reversals.\n\n"
        "The goal is not to sell at the top. It is to sell at a level that protects the move.\n\n"
        "What is your sell strategy — and when was the last time you actually followed it?\n\n"
        "Not financial advice. Informational only."
    ),
    post_outline=[
        "Why most investors have a buy strategy but no sell strategy",
        "The two types of exits: structural and protective",
        "Selling at the top is a myth: aim for the majority of the move",
        "How trailing stops and structural signals complement each other",
        "Building an exit protocol and actually following it",
    ],
    tags=["strategy", "exits", "selling", "discipline", "stops"],
)

_PORTFOLIO_CONCENTRATION = LearningTopic(
    id="portfolio_concentration",
    title="Concentration vs Diversification: The Small-Cap Dilemma",
    category="strategy",
    hook=(
        "Diversification protects wealth. Concentration builds it. "
        "The question is which mode you should be in right now."
    ),
    key_concept=(
        "Over-diversification dilutes your best ideas into mediocrity. "
        "Over-concentration turns a single miss into a portfolio-level event. "
        "The optimal answer for growth-focused investors is a concentrated portfolio with strict risk management — "
        "enough positions to spread risk, few enough that each one matters."
    ),
    example=(
        "Our portfolio holds a limited number of positions at any given time. "
        "Each one cleared our full screening process. Each one is sized based on conviction. "
        "And each one has a trailing stop that limits the downside if the thesis breaks."
    ),
    engagement_question="How many positions do you hold — and could you defend every one of them?",
    note_template=(
        "Diversification protects wealth. Concentration builds it. "
        "The question is which mode you should be in right now.\n\n"
        "In medicine, a generalist sees everything but treats nothing deeply. "
        "A specialist focuses narrowly and delivers superior outcomes in their domain. "
        "Portfolio construction faces the same tradeoff.\n\n"
        "Hold 50 stocks and you own a poorly constructed index fund with higher fees. "
        "Your best idea gets diluted to a 2% allocation that barely moves the needle. "
        "Hold 2 stocks and a single bad outcome can set you back years.\n\n"
        "The optimal answer for growth-focused investors is a concentrated portfolio with strict risk management. "
        "Enough positions to spread risk across themes and sectors. "
        "Few enough that each position is meaningful.\n\n"
        "Our portfolio holds a limited number of positions at any given time. "
        "Each one cleared our full screening process. Each one is sized based on conviction. "
        "And each one has a trailing stop that limits the downside if the thesis breaks.\n\n"
        "Concentrated conviction, managed risk.\n\n"
        "How many positions do you hold — and could you defend every one of them?\n\n"
        "Not financial advice. Informational only."
    ),
    post_outline=[
        "The diversification myth: why 50 stocks is not safer",
        "Concentration risk: when too few positions becomes dangerous",
        "The sweet spot: how many positions are optimal for growth",
        "Conviction-based sizing within a concentrated portfolio",
        "Risk management as the enabler of concentration",
    ],
    tags=["strategy", "concentration", "diversification", "portfolio", "sizing"],
)


# =============================================================================
# MASTER TOPIC REGISTRY
# =============================================================================

LEARNING_TOPICS: Dict[str, LearningTopic] = {
    # Risk Management
    "position_sizing": _POSITION_SIZING,
    "trailing_stops": _TRAILING_STOPS,
    "max_drawdown": _MAX_DRAWDOWN,
    "cash_reserve": _CASH_RESERVE,
    # Momentum
    "structural_momentum": _STRUCTURAL_MOMENTUM,
    "institutional_accumulation": _INSTITUTIONAL_ACCUMULATION,
    "sector_rotation": _SECTOR_ROTATION,
    "breadth_signals": _BREADTH_SIGNALS,
    # Fundamentals
    "catalyst_investing": _CATALYST_INVESTING,
    "revenue_acceleration": _REVENUE_ACCELERATION,
    "theme_alignment": _THEME_ALIGNMENT,
    "small_cap_edge": _SMALL_CAP_EDGE,
    # Psychology
    "patience_over_fomo": _PATIENCE_OVER_FOMO,
    "systematic_discipline": _SYSTEMATIC_DISCIPLINE,
    "loss_acceptance": _LOSS_ACCEPTANCE,
    "compounding_math": _COMPOUNDING_MATH,
    # Strategy
    "screening_advantage": _SCREENING_ADVANTAGE,
    "theme_surfing": _THEME_SURFING,
    "when_to_sell": _WHEN_TO_SELL,
    "portfolio_concentration": _PORTFOLIO_CONCENTRATION,
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_random_topic(
    exclude_ids: Optional[List[str]] = None,
    category: Optional[str] = None,
) -> LearningTopic:
    """
    Return a random topic, optionally filtered by category and excluding IDs.

    Args:
        exclude_ids: Topic IDs to skip (e.g. recently used).
        category: Restrict to a single category.

    Returns:
        A randomly selected LearningTopic.

    Raises:
        ValueError: If no topics remain after filtering.
    """
    pool = list(LEARNING_TOPICS.values())

    if category:
        pool = [t for t in pool if t.category == category]

    if exclude_ids:
        exclude_set = set(exclude_ids)
        pool = [t for t in pool if t.id not in exclude_set]

    if not pool:
        raise ValueError(
            f"No topics available after filtering (category={category}, "
            f"excluded={exclude_ids})"
        )

    return random.choice(pool)


def get_topics_by_category(category: str) -> List[LearningTopic]:
    """
    Return all topics in a given category, ordered by their position in the registry.

    Args:
        category: One of risk_management, momentum, fundamentals, psychology, strategy.

    Returns:
        List of matching LearningTopic objects.
    """
    return [t for t in LEARNING_TOPICS.values() if t.category == category]


def get_all_categories() -> List[str]:
    """Return a sorted list of unique category names."""
    return sorted({t.category for t in LEARNING_TOPICS.values()})


# =============================================================================
# SELF-TEST
# =============================================================================

if __name__ == "__main__":
    print("Learning Content Library — Self-Test")
    print("=" * 60)
    print(f"Total topics:  {len(LEARNING_TOPICS)}")
    print(f"Categories:    {get_all_categories()}")
    print()

    # Per-category counts
    for cat in get_all_categories():
        topics = get_topics_by_category(cat)
        print(f"  {cat}: {len(topics)} topics")
        for t in topics:
            word_count = len(t.note_template.split())
            print(f"    - {t.id} ({word_count} words)")

    print()

    # Validate note_template word counts (150-250 target)
    issues = []
    for tid, topic in LEARNING_TOPICS.items():
        wc = len(topic.note_template.split())
        if wc < 130:
            issues.append(f"  {tid}: {wc} words (below 130)")
        elif wc > 270:
            issues.append(f"  {tid}: {wc} words (above 270)")

    if issues:
        print("Word count warnings:")
        for issue in issues:
            print(issue)
    else:
        print("All note templates within acceptable word count range.")

    # Check for banned terms
    print()
    try:
        from config.banned_terms import ALL_BANNED
        violations_found = False
        for tid, topic in LEARNING_TOPICS.items():
            text = (
                topic.note_template + " " +
                topic.hook + " " +
                topic.key_concept + " " +
                topic.example
            )
            text_lower = text.lower()
            for term in ALL_BANNED:
                if term.lower() in text_lower:
                    # Word-boundary check for short terms
                    import re
                    short_terms = [
                        "RSI", "MACD", "KDJ", "BoS", "BOS", "GMT", "BST",
                        "HMA", "PDT", "TEAL", "teal",
                    ]
                    if term in short_terms:
                        if re.search(rf'\b{re.escape(term)}\b', text, re.IGNORECASE):
                            print(f"  BANNED TERM in {tid}: '{term}'")
                            violations_found = True
                    else:
                        print(f"  BANNED TERM in {tid}: '{term}'")
                        violations_found = True

        if not violations_found:
            print("No banned terms found in any topic content.")
    except ImportError:
        print("Could not import banned_terms for validation (run from project root).")

    # Random topic test
    print()
    topic = get_random_topic()
    print(f"Random topic: {topic.id} ({topic.category})")
    topic2 = get_random_topic(category="psychology")
    print(f"Random psychology topic: {topic2.id}")
    topic3 = get_random_topic(exclude_ids=[topic.id, topic2.id])
    print(f"Random (excluding {topic.id}, {topic2.id}): {topic3.id}")

    print()
    print("Self-test complete.")
