# MARKET REGIME ENGINE v3.4

**Status:** Production-ready  
**Build Date:** 2026-02-15  
**Paradigm:** Probabilistic regime detection with operational rigor  
**Replaces:** v3.3  

---

## Changes (v3.3 → v3.4)

### UI/UX Improvements (telegram_bot.py)

```diff
REMOVED:
- Horizontal separator lines (━━━)
- Confusing "ACTION REQUIRED" header
- Generic one-line comments

ADDED:
+ Regime emoji based on type (🟢🔴🟡⚪)
+ Probabilities with visual bars (█░)
+ Rich logic comments (context-aware, Russian)
+ LP quadrant matrix visualization
+ Cleaner FLAGS section with explanations
+ returns_30d in engine metadata (for counter-cyclical)

STYLE:
+ Показатели: English (BEAR, RISK-OFF, Confidence)
+ Комментарии: Русский (→ Рынок опасен...)
```

### Header Changes

| Condition | v3.3 | v3.4 |
|-----------|------|------|
| Tail risk active | 🚨 ACTION REQUIRED | 🚨 ALERT: TAIL RISK |
| Risk < -0.3 | ⚠️ CAUTION | ⚠️ RISK-OFF MODE |
| Normal | 📊 STATUS | 📊 MONITORING |

### Probabilities Display

```
v3.3: (not shown)

v3.4:
Probabilities:
   BULL       ░░░░░░░░░░░░ 0.04
   BEAR       ██████░░░░░░ 0.55
   RANGE      ░░░░░░░░░░░░ 0.03
   TRANSITION ████░░░░░░░░ 0.38
```

### LP Quadrant Matrix

```
v3.3:
Quadrant: Q2
Dir: -0.82 · LP: +0.20

v3.4:
         Dir Risk →
     ┌───────┬───────┐
 LP↑ │ Q3   │ Q1   │
     │ spot  │ ideal │
     ├───────┼───────┤
 LP↓ │ Q4   │[Q2]  │
     │ exit  │ LP    │
     └───────┴───────┘

Dir: -0.82 · LP: +0.20 · F/V: 1.2x
→ LP opportunity есть, но капитал ограничен...
```

### Rich Logic Comments

```python
def _get_regime_comment(regime, days, tail_active, conf, mom, risk):
    """Context-aware comments in Russian."""
    
    if regime == "BEAR":
        if tail_active and conf < 0.25:
            return "Паника на рынке. Возможно близко дно — не лучшее время продавать."
        elif days <= 2:
            return "Начало коррекции. Наблюдаем глубину падения."
        elif days > 14 and mom > -0.3:
            return "Затяжной медвежий тренд, но импульс слабеет. Возможен разворот."
        # ... more cases
```

### Metadata Addition

```python
# engine.py output now includes:
"metadata": {
    "returns_30d": 0.12,  # NEW: 30-day returns for counter-cyclical logic
    # ... existing fields
}
```

---

## Integration with Asset Allocation v1.4

v3.4 provides `returns_30d` in metadata, which enables counter-cyclical logic in Asset Allocation v1.4:

- **Panic detection**: momentum < -0.70 AND vol_z > 1.5
- **Euphoria detection**: momentum > 0.70 AND confidence > 0.60  
- **Deep drawdown**: returns_30d < -20%
- **Big rally**: returns_30d > 30%

---

## Full Sample Output (v3.4)

```
🚨 ALERT: TAIL RISK
BTC $70,751

🔴 BEAR
   Phase: 8d mature · Confidence: 18%
   Tail risk: ACTIVE ↓

Probabilities:
   BULL       ░░░░░░░░░░░░ 0.04
   BEAR       ██████░░░░░░ 0.55
   RANGE      ░░░░░░░░░░░░ 0.03
   TRANSITION ████░░░░░░░░ 0.38

→ Паника на рынке. Возможно близко дно — не лучшее время продавать.

📉 DIRECTIONAL
   BTC: HOLD
   ETH: HOLD
   → COUNTER-CYCLICAL: Not selling into panic

💧 LP POLICY

          Dir Risk →
      ┌───────┬───────┐
  LP↑ │ Q3   │ Q1   │
      │ spot  │ ideal │
      ├───────┼───────┤
  LP↓ │ Q4   │[Q2]  │
      │ exit  │ LP    │
      └───────┴───────┘

   Dir: -0.82 · LP: +0.20 · F/V: 1.2x
   Exposure: 4% (max 20%)
   Range: wide
   Hedge: REQUIRED
   → LP opportunity есть, но капитал ограничен из-за направленного риска.

⚠️ FLAGS
   • Tail risk active — экстремальное движение
   • Structure break — рынок изменился
   • Partial data — часть данных недоступна

v3.4 · LP v2.0.1 · AA v1.4
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v3.0 | 2026-01-xx | Initial production release |
| v3.1 | 2026-01-xx | Bug fixes |
| v3.2 | 2026-02-01 | Performance improvements |
| v3.3 | 2026-02-07 | Structural break detection, churn penalty |
| **v3.4** | **2026-02-15** | **UI overhaul, rich logic comments, returns_30d** |

---

## Dependencies

- Asset Allocation: v1.4 (counter-cyclical)
- LP Intelligence: v2.0.1 (unchanged)

---

**Base document: [MARKET_REGIME_ENGINE_v3.3.md](./MARKET_REGIME_ENGINE_v3.3.md)**
