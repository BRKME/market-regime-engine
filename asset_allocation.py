"""
Asset Allocation Policy v1.4.1

Conservative capital preservation policy with counter-cyclical logic.

v1.4.1 Changes (from CFO backtest):
- More sensitive panic detection (catches panic earlier)
- Tightened thresholds: drawdown -25%, rally +40%
- Added oversold protection in BEAR regime

v1.4 Changes:
- Don't sell in panic (momentum < -0.7 + high vol)
- Accumulate on fear (extreme panic + deep drawdown)
- Take profit on greed (euphoria + big rally)
- Mean reversion in RANGE regime

Trade-offs (documented):
- TRANSITION = don't play (misses early trends)
- ETH ≤ BTC always (ETH never leads)
- Linear momentum (no vol context)
- No EV calculation
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple
from datetime import date, datetime, timedelta

import settings as cfg


# ============================================================
# ENUMS
# ============================================================

class AllocationAction(Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class Stance(Enum):
    RISK_ON = "RISK_ON"
    RISK_NEUTRAL = "RISK_NEUTRAL"
    RISK_OFF = "RISK_OFF"


# ============================================================
# OUTPUT DATACLASS
# ============================================================

@dataclass
class AllocationPolicy:
    """Final allocation policy output."""
    asset: str
    action: AllocationAction
    size_pct: float
    confidence: float
    stance: Stance
    blocked_by: Optional[str]  # CONFIDENCE | CHURN | COOLDOWN | None
    reasoning: List[str]


# ============================================================
# CONSTANTS (from settings)
# ============================================================

# Confidence gates
CONF_NO_ACTION = getattr(cfg, 'AA_CONF_NO_ACTION', 0.40)
CONF_ACTION = getattr(cfg, 'AA_CONF_ACTION', 0.50)
CONF_STRONG_SELL = getattr(cfg, 'AA_CONF_STRONG_SELL', 0.60)
CONF_STRONG_BUY = getattr(cfg, 'AA_CONF_STRONG_BUY', 0.70)

# Momentum thresholds
MOM_STRONG = getattr(cfg, 'AA_MOM_STRONG', 0.50)
MOM_WEAK = getattr(cfg, 'AA_MOM_WEAK', 0.0)

# Risk thresholds
RISK_TRANSITION_SELL = getattr(cfg, 'AA_RISK_TRANSITION_SELL', -0.30)

# Position sizes
SIZES_BTC = {
    AllocationAction.STRONG_BUY: +0.20,
    AllocationAction.BUY: +0.10,
    AllocationAction.HOLD: 0.00,
    AllocationAction.SELL: -0.15,
    AllocationAction.STRONG_SELL: -0.50,
}

SIZES_ETH = {
    AllocationAction.STRONG_BUY: 0.00,  # Not allowed
    AllocationAction.BUY: +0.05,
    AllocationAction.HOLD: 0.00,
    AllocationAction.SELL: -0.20,
    AllocationAction.STRONG_SELL: -0.70,
}

# Anti-churn
MAX_ACTIONS_30D = getattr(cfg, 'AA_MAX_ACTIONS_30D', 3)
COOLDOWN_BUY_AFTER_SELL = getattr(cfg, 'AA_COOLDOWN_BUY_AFTER_SELL', 7)
COOLDOWN_SELL_AFTER_BUY = getattr(cfg, 'AA_COOLDOWN_SELL_AFTER_BUY', 3)
COOLDOWN_STRONG_AFTER_STRONG = getattr(cfg, 'AA_COOLDOWN_STRONG', 14)

# Regime actions
REGIME_ACTIONS = {
    "BULL": [AllocationAction.STRONG_BUY, AllocationAction.BUY, AllocationAction.HOLD],
    "BEAR": [AllocationAction.STRONG_SELL, AllocationAction.SELL, AllocationAction.HOLD],
    "RANGE": [AllocationAction.HOLD],
    "TRANSITION": [AllocationAction.STRONG_SELL, AllocationAction.SELL, AllocationAction.HOLD],
}

# ETH rules by stance
ETH_ALLOWED = {
    Stance.RISK_ON: [AllocationAction.BUY, AllocationAction.HOLD],
    Stance.RISK_NEUTRAL: [AllocationAction.HOLD],
    Stance.RISK_OFF: [AllocationAction.STRONG_SELL, AllocationAction.SELL],
}

# Action ranking (for ETH ceiling)
ACTION_RANK = {
    AllocationAction.STRONG_BUY: 4,
    AllocationAction.BUY: 3,
    AllocationAction.HOLD: 2,
    AllocationAction.SELL: 1,
    AllocationAction.STRONG_SELL: 0,
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def determine_stance(regime: str, confidence: float, risk_level: float) -> Stance:
    """
    Determine market stance.
    """
    if regime == "BULL" and confidence > 0.60 and risk_level > 0.30:
        return Stance.RISK_ON
    elif regime == "BEAR" and risk_level < -0.30:
        return Stance.RISK_OFF
    elif regime == "TRANSITION" and risk_level < -0.30:
        return Stance.RISK_OFF
    elif regime == "RANGE":
        return Stance.RISK_NEUTRAL
    else:
        return Stance.RISK_NEUTRAL


def confidence_allows(confidence: float, action: AllocationAction) -> bool:
    """
    Check if confidence allows this action.
    """
    if action == AllocationAction.HOLD:
        return True
    if action in [AllocationAction.BUY, AllocationAction.SELL]:
        return confidence >= CONF_ACTION
    if action == AllocationAction.STRONG_SELL:
        return confidence >= CONF_STRONG_SELL
    if action == AllocationAction.STRONG_BUY:
        return confidence >= CONF_STRONG_BUY
    return False


def regime_allows(regime: str, action: AllocationAction) -> bool:
    """
    Check if regime allows this action.
    """
    allowed = REGIME_ACTIONS.get(regime, [AllocationAction.HOLD])
    return action in allowed


def is_cooldown_active(
    last_action: Optional[str],
    last_action_date: Optional[date],
    proposed_action: AllocationAction,
    today: date
) -> Tuple[bool, int]:
    """
    Check if cooldown prevents this action.
    Returns (is_active, days_remaining).
    """
    if last_action is None or last_action_date is None:
        return False, 0
    
    days_since = (today - last_action_date).days
    
    # BUY after SELL
    if last_action in ["SELL", "STRONG_SELL"]:
        if proposed_action in [AllocationAction.BUY, AllocationAction.STRONG_BUY]:
            if days_since < COOLDOWN_BUY_AFTER_SELL:
                return True, COOLDOWN_BUY_AFTER_SELL - days_since
    
    # SELL after BUY
    if last_action in ["BUY", "STRONG_BUY"]:
        if proposed_action in [AllocationAction.SELL, AllocationAction.STRONG_SELL]:
            if days_since < COOLDOWN_SELL_AFTER_BUY:
                return True, COOLDOWN_SELL_AFTER_BUY - days_since
    
    # STRONG after STRONG
    if "STRONG" in last_action and "STRONG" in proposed_action.value:
        if days_since < COOLDOWN_STRONG_AFTER_STRONG:
            return True, COOLDOWN_STRONG_AFTER_STRONG - days_since
    
    return False, 0


def count_actions_30d(action_history: List[Tuple[str, date]], today: date) -> int:
    """
    Count non-HOLD actions in last 30 days.
    """
    cutoff = today - timedelta(days=30)
    count = 0
    for action, action_date in action_history:
        if action_date >= cutoff and action != "HOLD":
            count += 1
    return count


def is_churn(action_history: List[Tuple[str, date]], today: date) -> bool:
    """
    Detect overtrading.
    """
    return count_actions_30d(action_history, today) >= MAX_ACTIONS_30D


def apply_eth_ceiling(btc_action: AllocationAction, eth_action: AllocationAction) -> AllocationAction:
    """
    ETH action cannot exceed BTC action (be more bullish).
    """
    btc_rank = ACTION_RANK[btc_action]
    eth_rank = ACTION_RANK[eth_action]
    
    if eth_rank > btc_rank:
        # Find action at BTC level
        for action, rank in ACTION_RANK.items():
            if rank == btc_rank:
                return action
    
    return eth_action


def apply_eth_stance_rules(action: AllocationAction, stance: Stance) -> AllocationAction:
    """
    Apply ETH-specific stance rules.
    """
    allowed = ETH_ALLOWED.get(stance, [AllocationAction.HOLD])
    
    if action not in allowed:
        # Downgrade logic
        if action == AllocationAction.STRONG_BUY:
            # STRONG_BUY → BUY (if BUY allowed) → HOLD
            if AllocationAction.BUY in allowed:
                return AllocationAction.BUY
            return AllocationAction.HOLD
        elif stance == Stance.RISK_NEUTRAL:
            return AllocationAction.HOLD
        elif stance == Stance.RISK_OFF:
            return AllocationAction.SELL
    
    return action


def get_size(asset: str, action: AllocationAction) -> float:
    """
    Get position size for action.
    """
    if asset == "BTC":
        return SIZES_BTC.get(action, 0.0)
    else:
        return SIZES_ETH.get(action, 0.0)


# ============================================================
# MAIN COMPUTATION
# ============================================================

def compute_allocation(
    regime: str,
    confidence: float,
    risk_level: float,
    momentum: float,
    tail_risk: bool,
    tail_polarity: Optional[str],
    asset: str,
    btc_action: Optional[AllocationAction] = None,
    last_action: Optional[str] = None,
    last_action_date: Optional[date] = None,
    action_history: Optional[List[Tuple[str, date]]] = None,
    today: Optional[date] = None,
    # v1.4 Counter-cyclical parameters
    vol_z: float = 0.0,
    returns_30d: float = 0.0,
) -> AllocationPolicy:
    """
    Compute asset allocation policy.
    
    v1.4: Added counter-cyclical logic:
    - Don't sell in panic (momentum < -0.7 + high vol)
    - Accumulate on fear (extreme negative momentum + drawdown)
    - Take profit on greed (extreme positive momentum + rally)
    
    Args:
        regime: BULL | BEAR | RANGE | TRANSITION
        confidence: Model confidence [0, 1]
        risk_level: Directional risk [-1, +1]
        momentum: Momentum score [-1, +1]
        tail_risk: Whether tail risk is active
        tail_polarity: "downside" | "upside" | None
        asset: "BTC" | "ETH"
        btc_action: BTC action (required for ETH)
        last_action: Last action taken
        last_action_date: Date of last action
        action_history: List of (action, date) tuples
        today: Current date (defaults to today)
        vol_z: Volatility z-score (for panic detection)
        returns_30d: 30-day returns (for drawdown/rally detection)
    
    Returns:
        AllocationPolicy with action and reasoning
    """
    if today is None:
        today = date.today()
    
    if action_history is None:
        action_history = []
    
    reasoning = []
    blocked_by = None
    
    # Determine stance
    stance = determine_stance(regime, confidence, risk_level)
    
    # ══════════════════════════════════════════════════════════════
    # v1.4.1 COUNTER-CYCLICAL LOGIC (tuned from stress test)
    # ══════════════════════════════════════════════════════════════
    
    # Detect panic conditions (tuned thresholds from CFO backtest)
    # More sensitive detection: catches panic earlier
    is_panic = (
        (momentum < -0.50 and vol_z > 1.5) or  # High vol + negative momentum
        (momentum < -0.60 and vol_z > 1.0) or  # Strong negative momentum
        (returns_30d < -0.30)                   # Deep drawdown alone
    )
    is_extreme_panic = momentum < -0.75 and vol_z > 2.0
    is_deep_drawdown = returns_30d < -0.25  # Tightened from -0.20
    
    # Detect euphoria conditions (proxy for RSI > 75)
    is_euphoria = momentum > 0.70 and confidence > 0.60
    is_extreme_euphoria = momentum > 0.80 and confidence > 0.70
    is_big_rally = returns_30d > 0.40  # Raised from 0.30 for less false positives
    
    # COUNTER-CYCLICAL RULE 1: Don't sell in panic
    # If we're in panic, block SELL/STRONG_SELL (will be applied later)
    panic_block_sell = is_panic or is_extreme_panic
    
    # COUNTER-CYCLICAL RULE 2: Accumulate on fear
    # Extreme panic + deep drawdown = buying opportunity
    if is_extreme_panic and is_deep_drawdown and asset == "BTC":
        action = AllocationAction.BUY
        reasoning.append("COUNTER-CYCLICAL: Panic + deep drawdown = accumulation")
        reasoning.append(f"Momentum: {momentum:.2f}, Vol_z: {vol_z:.2f}, Returns_30d: {returns_30d:.1%}")
        
        # Still apply cooldown check
        cooldown_active, days_remaining = is_cooldown_active(
            last_action, last_action_date, action, today
        )
        if cooldown_active:
            action = AllocationAction.HOLD
            reasoning.append(f"Cooldown active: {days_remaining}d remaining")
            blocked_by = "COOLDOWN"
        
        return AllocationPolicy(
            asset=asset,
            action=action,
            size_pct=get_size(asset, action),
            confidence=confidence,
            stance=stance,
            blocked_by=blocked_by,
            reasoning=reasoning
        )
    
    # COUNTER-CYCLICAL RULE 3: Take profit on greed
    # Extreme euphoria + big rally = reduce exposure
    if is_extreme_euphoria and is_big_rally and asset == "BTC":
        action = AllocationAction.SELL
        reasoning.append("COUNTER-CYCLICAL: Euphoria + big rally = take profit")
        reasoning.append(f"Momentum: {momentum:.2f}, Confidence: {confidence:.2f}, Returns_30d: {returns_30d:.1%}")
        
        # Still apply cooldown check
        cooldown_active, days_remaining = is_cooldown_active(
            last_action, last_action_date, action, today
        )
        if cooldown_active:
            action = AllocationAction.HOLD
            reasoning.append(f"Cooldown active: {days_remaining}d remaining")
            blocked_by = "COOLDOWN"
        
        return AllocationPolicy(
            asset=asset,
            action=action,
            size_pct=get_size(asset, action),
            confidence=confidence,
            stance=stance,
            blocked_by=blocked_by,
            reasoning=reasoning
        )
    
    # ── Step 1: Tail risk override (highest priority) ──
    # v1.4 MODIFICATION: Don't trigger STRONG_SELL in panic conditions
    if tail_risk and tail_polarity == "downside":
        if panic_block_sell:
            # In panic: downgrade to HOLD, don't sell the bottom
            action = AllocationAction.HOLD
            reasoning.append("TAIL RISK detected, but PANIC conditions active")
            reasoning.append("COUNTER-CYCLICAL: Not selling into panic")
            reasoning.append(f"Momentum: {momentum:.2f}, Vol_z: {vol_z:.2f}")
            
            return AllocationPolicy(
                asset=asset,
                action=action,
                size_pct=get_size(asset, action),
                confidence=confidence,
                stance=stance,
                blocked_by=None,
                reasoning=reasoning
            )
        else:
            # Normal tail risk response (not in panic)
            action = AllocationAction.STRONG_SELL
            reasoning.append("TAIL RISK: Emergency exit")
            reasoning.append(f"Regime: {regime}, bypassing all gates")
            
            return AllocationPolicy(
                asset=asset,
                action=action,
                size_pct=get_size(asset, action),
                confidence=confidence,
                stance=stance,
                blocked_by=None,
                reasoning=reasoning
            )
    
    # Upside tail risk: take profit
    if tail_risk and tail_polarity == "upside":
        action = AllocationAction.SELL
        reasoning.append("TAIL RISK (upside): Take profit on euphoria")
        
        return AllocationPolicy(
            asset=asset,
            action=action,
            size_pct=get_size(asset, action),
            confidence=confidence,
            stance=stance,
            blocked_by=None,
            reasoning=reasoning
        )
    
    # ── Step 2: Confidence gate ──
    if confidence < CONF_NO_ACTION:
        action = AllocationAction.HOLD
        reasoning.append(f"Confidence {confidence:.2f} < {CONF_NO_ACTION}")
        reasoning.append("No action allowed below confidence gate")
        blocked_by = "CONFIDENCE"
        
        # Exception: ETH in RISK_OFF must still exit
        if asset == "ETH" and stance == Stance.RISK_OFF:
            action = AllocationAction.SELL
            reasoning.append("ETH exception: must exit in RISK_OFF")
            blocked_by = None
        
        return AllocationPolicy(
            asset=asset,
            action=action,
            size_pct=get_size(asset, action),
            confidence=confidence,
            stance=stance,
            blocked_by=blocked_by,
            reasoning=reasoning
        )
    
    # ── Step 3: Compute raw action based on regime ──
    if regime == "BULL":
        # v1.4 COUNTER-CYCLICAL: Don't buy in euphoria
        if is_euphoria or is_extreme_euphoria:
            raw_action = AllocationAction.HOLD
            reasoning.append(f"BULL: Euphoria detected (mom={momentum:.2f})")
            reasoning.append("COUNTER-CYCLICAL: Not buying into overbought")
        elif confidence >= CONF_STRONG_BUY and momentum > MOM_STRONG:
            raw_action = AllocationAction.STRONG_BUY
            reasoning.append(f"BULL: conf {confidence:.2f} ≥ {CONF_STRONG_BUY}, mom {momentum:.2f} > {MOM_STRONG}")
        elif confidence >= CONF_ACTION and momentum > MOM_WEAK:
            raw_action = AllocationAction.BUY
            reasoning.append(f"BULL: conf {confidence:.2f} ≥ {CONF_ACTION}, mom {momentum:.2f} > 0")
        else:
            raw_action = AllocationAction.HOLD
            reasoning.append(f"BULL: conditions not met for action")
    
    elif regime == "BEAR":
        # v1.4 COUNTER-CYCLICAL: Don't sell in panic conditions
        if panic_block_sell:
            raw_action = AllocationAction.HOLD
            reasoning.append(f"BEAR: Panic detected (mom={momentum:.2f}, vol_z={vol_z:.2f})")
            reasoning.append("COUNTER-CYCLICAL: Not selling into panic")
        elif confidence >= CONF_STRONG_SELL and momentum < -MOM_STRONG and not is_panic:
            raw_action = AllocationAction.STRONG_SELL
            reasoning.append(f"BEAR: conf {confidence:.2f} ≥ {CONF_STRONG_SELL}, mom {momentum:.2f} < -{MOM_STRONG}")
        elif confidence >= CONF_ACTION and momentum < MOM_WEAK and not is_panic:
            raw_action = AllocationAction.SELL
            reasoning.append(f"BEAR: conf {confidence:.2f} ≥ {CONF_ACTION}, mom {momentum:.2f} < 0")
        else:
            raw_action = AllocationAction.HOLD
            reasoning.append(f"BEAR: conditions not met for action")
    
    elif regime == "TRANSITION":
        if risk_level < RISK_TRANSITION_SELL and confidence >= CONF_ACTION:
            raw_action = AllocationAction.SELL
            reasoning.append(f"TRANSITION: risk {risk_level:.2f} < {RISK_TRANSITION_SELL}")
        else:
            raw_action = AllocationAction.HOLD
            reasoning.append("TRANSITION: no action (capital preservation)")
    
    else:  # RANGE
        # v1.4 COUNTER-CYCLICAL: Mean reversion in range
        if is_panic and asset == "BTC":
            raw_action = AllocationAction.BUY
            reasoning.append("RANGE + panic: Mean reversion accumulation")
        elif is_euphoria and asset == "BTC":
            raw_action = AllocationAction.SELL
            reasoning.append("RANGE + euphoria: Mean reversion reduction")
        else:
            raw_action = AllocationAction.HOLD
            reasoning.append("RANGE: HOLD only")
    
    # ── Step 4: Regime gate ──
    if not regime_allows(regime, raw_action):
        raw_action = AllocationAction.HOLD
        reasoning.append(f"Regime gate: {raw_action.value} not allowed in {regime}")
    
    # ── Step 5: Confidence gate (double check) ──
    if not confidence_allows(confidence, raw_action):
        raw_action = AllocationAction.HOLD
        reasoning.append(f"Confidence gate: {raw_action.value} requires higher confidence")
    
    # ── Step 6: ETH adjustments ──
    if asset == "ETH":
        original = raw_action
        
        # ETH stance rules
        raw_action = apply_eth_stance_rules(raw_action, stance)
        if raw_action != original:
            reasoning.append(f"ETH stance rule: {original.value} → {raw_action.value}")
        
        # ETH ceiling (cannot exceed BTC)
        if btc_action is not None:
            original = raw_action
            raw_action = apply_eth_ceiling(btc_action, raw_action)
            if raw_action != original:
                reasoning.append(f"ETH ceiling: cannot exceed BTC ({btc_action.value})")
        
        # ETH STRONG_BUY never allowed
        if raw_action == AllocationAction.STRONG_BUY:
            raw_action = AllocationAction.BUY
            reasoning.append("ETH: STRONG_BUY not allowed, downgraded to BUY")
    
    # ── Step 7: Cooldown check ──
    cooldown_active, days_remaining = is_cooldown_active(
        last_action, last_action_date, raw_action, today
    )
    if cooldown_active:
        reasoning.append(f"Cooldown: {days_remaining}d remaining before {raw_action.value}")
        raw_action = AllocationAction.HOLD
        blocked_by = "COOLDOWN"
        
        return AllocationPolicy(
            asset=asset,
            action=raw_action,
            size_pct=get_size(asset, raw_action),
            confidence=confidence,
            stance=stance,
            blocked_by=blocked_by,
            reasoning=reasoning
        )
    
    # ── Step 8: Churn protection ──
    if is_churn(action_history, today) and raw_action != AllocationAction.STRONG_SELL:
        actions_count = count_actions_30d(action_history, today)
        reasoning.append(f"Churn protection: {actions_count}/{MAX_ACTIONS_30D} actions in 30d")
        raw_action = AllocationAction.HOLD
        blocked_by = "CHURN"
        
        return AllocationPolicy(
            asset=asset,
            action=raw_action,
            size_pct=get_size(asset, raw_action),
            confidence=confidence,
            stance=stance,
            blocked_by=blocked_by,
            reasoning=reasoning
        )
    
    # ── Step 9: Return final action ──
    return AllocationPolicy(
        asset=asset,
        action=raw_action,
        size_pct=get_size(asset, raw_action),
        confidence=confidence,
        stance=stance,
        blocked_by=blocked_by,
        reasoning=reasoning
    )


def compute_btc_eth_allocation(
    regime_output: dict,
    tail_risk: bool = False,
    tail_polarity: Optional[str] = None,
    btc_last_action: Optional[str] = None,
    btc_last_date: Optional[date] = None,
    btc_history: Optional[List[Tuple[str, date]]] = None,
    eth_last_action: Optional[str] = None,
    eth_last_date: Optional[date] = None,
    eth_history: Optional[List[Tuple[str, date]]] = None,
) -> dict:
    """
    Compute allocation for both BTC and ETH.
    
    Args:
        regime_output: Full output from Regime Engine v3.3
        tail_risk: Whether tail risk is active
        tail_polarity: "downside" | "upside" | None
        *_last_action: Last action for each asset
        *_last_date: Date of last action
        *_history: Action history
    
    Returns:
        Dict with btc, eth, and meta keys
    """
    # Extract inputs from regime output
    regime = regime_output.get("regime", "TRANSITION")
    confidence = regime_output.get("confidence", {}).get("quality_adjusted", 0.0)
    risk_level = regime_output.get("risk", {}).get("risk_level", 0.0)
    momentum = regime_output.get("buckets", {}).get("Momentum", 0.0)
    vol_z = regime_output.get("metadata", {}).get("vol_z", 0.0)
    structural_break = regime_output.get("normalization", {}).get("break_active", False)
    
    # v1.4: Extract 30d returns for counter-cyclical logic
    # This comes from the price data if available
    returns_30d = regime_output.get("metadata", {}).get("returns_30d", 0.0)
    
    # Auto-detect tail risk if not provided
    if not tail_risk:
        tail_risk, tail_polarity = detect_tail_risk(vol_z, risk_level, momentum, structural_break)
    
    # Compute BTC first
    btc_policy = compute_allocation(
        regime=regime,
        confidence=confidence,
        risk_level=risk_level,
        momentum=momentum,
        tail_risk=tail_risk,
        tail_polarity=tail_polarity,
        asset="BTC",
        btc_action=None,
        last_action=btc_last_action,
        last_action_date=btc_last_date,
        action_history=btc_history,
        vol_z=vol_z,
        returns_30d=returns_30d,
    )
    
    # Compute ETH with BTC as ceiling
    eth_policy = compute_allocation(
        regime=regime,
        confidence=confidence,
        risk_level=risk_level,
        momentum=momentum,
        tail_risk=tail_risk,
        tail_polarity=tail_polarity,
        asset="ETH",
        btc_action=btc_policy.action,
        last_action=eth_last_action,
        last_action_date=eth_last_date,
        action_history=eth_history,
        vol_z=vol_z,
        returns_30d=returns_30d,
    )
    
    return {
        "btc": {
            "action": btc_policy.action.value,
            "size_pct": btc_policy.size_pct,
            "confidence": btc_policy.confidence,
            "stance": btc_policy.stance.value,
            "blocked_by": btc_policy.blocked_by,
            "reasoning": btc_policy.reasoning,
        },
        "eth": {
            "action": eth_policy.action.value,
            "size_pct": eth_policy.size_pct,
            "confidence": eth_policy.confidence,
            "stance": eth_policy.stance.value,
            "blocked_by": eth_policy.blocked_by,
            "reasoning": eth_policy.reasoning,
        },
        "meta": {
            "regime": regime,
            "tail_risk_active": tail_risk,
            "tail_polarity": tail_polarity,
            "structural_break": structural_break,
        }
    }


def detect_tail_risk(
    vol_z: float,
    risk_level: float,
    momentum: float,
    structural_break: bool
) -> Tuple[bool, Optional[str]]:
    """
    Detect tail risk and polarity.
    """
    extreme_vol = vol_z > 2.5
    deep_risk_off = risk_level < -0.70
    break_negative = structural_break and risk_level < -0.30
    
    is_tail = extreme_vol or deep_risk_off or break_negative
    
    if not is_tail:
        return False, None
    
    # Polarity
    if risk_level < -0.30 or momentum < -0.30:
        return True, "downside"
    elif risk_level > 0.30 and momentum > 0.30:
        return True, "upside"
    else:
        return True, "downside"  # Conservative default


# ============================================================
# ACTION EMOJI (for Telegram)
# ============================================================

ACTION_EMOJI = {
    "STRONG_BUY": "🟢🟢",
    "BUY": "🟢",
    "HOLD": "⚪️",
    "SELL": "🔴",
    "STRONG_SELL": "🔴🔴",
}


def get_action_emoji(action: str) -> str:
    """Get emoji for action."""
    return ACTION_EMOJI.get(action, "⚪️")
