"""
Cycle Position Engine v1.0

Определяет положение в рыночном цикле:
- Локальное/глобальное дно
- Локальная/глобальная вершина
- Cycle position (0-100%)

Генерирует сигналы: STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


# ============================================================
# ENUMS
# ============================================================

class CyclePhase(Enum):
    """Фаза рыночного цикла"""
    ACCUMULATION = "ACCUMULATION"      # Дно, накопление
    EARLY_BULL = "EARLY_BULL"          # Ранний бык
    MID_BULL = "MID_BULL"              # Середина быка
    LATE_BULL = "LATE_BULL"            # Поздний бык, эйфория
    DISTRIBUTION = "DISTRIBUTION"      # Вершина, распределение
    EARLY_BEAR = "EARLY_BEAR"          # Ранний медведь
    MID_BEAR = "MID_BEAR"              # Середина медведя
    CAPITULATION = "CAPITULATION"      # Капитуляция, паника


class BottomTopSignal(Enum):
    """Сигнал дна/вершины"""
    GLOBAL_BOTTOM = "GLOBAL_BOTTOM"    # Глобальное дно (редко)
    LOCAL_BOTTOM = "LOCAL_BOTTOM"      # Локальное дно
    NO_SIGNAL = "NO_SIGNAL"            # Нет сигнала
    LOCAL_TOP = "LOCAL_TOP"            # Локальная вершина
    GLOBAL_TOP = "GLOBAL_TOP"          # Глобальная вершина (редко)


class ActionSignal(Enum):
    """Торговый сигнал"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class CycleMetrics:
    """Метрики для определения позиции в цикле"""
    # Price metrics
    current_price: float
    ath: float                    # All-time high
    atl_52w: float               # 52-week low
    ath_52w: float               # 52-week high
    
    # Moving averages
    ma_50: float
    ma_200: float
    ma_50_slope: float           # Наклон 50MA (нормализованный)
    ma_200_slope: float          # Наклон 200MA (нормализованный)
    
    # RSI
    rsi_14: float
    rsi_7: float
    
    # Drawdown
    drawdown_from_ath: float     # % от ATH (отрицательное)
    drawdown_from_52w: float     # % от 52w high
    
    # Rally
    rally_from_atl: float        # % от ATL
    rally_from_52w_low: float    # % от 52w low
    
    # Volatility
    realized_vol_30d: float
    vol_percentile: float        # Где волатильность относительно истории (0-1)
    
    # Sentiment
    fear_greed: float            # 0-100
    
    # Volume
    volume_ratio: float          # Текущий объём / средний объём


@dataclass
class CyclePosition:
    """Результат анализа позиции в цикле"""
    phase: CyclePhase
    phase_confidence: float      # 0-1
    
    # Position metrics
    cycle_position: float        # 0 = дно, 100 = вершина
    bottom_proximity: float      # 0-1, насколько близко к дну
    top_proximity: float         # 0-1, насколько близко к вершине
    
    # Signals
    bottom_top_signal: BottomTopSignal
    signal_strength: float       # 0-1
    
    # Action
    action: ActionSignal
    action_confidence: float     # 0-1
    size_modifier: float         # Множитель размера позиции
    
    # Context
    vs_ath_pct: float
    vs_200ma_pct: float
    rsi: float
    fear_greed: float
    
    # Reasoning
    reasons: List[str]


# ============================================================
# THRESHOLDS
# ============================================================

class CycleThresholds:
    """Пороги для определения фаз цикла"""
    
    # === BOTTOM DETECTION ===
    
    # Global bottom (очень редкий сигнал)
    GLOBAL_BOTTOM = {
        "drawdown_from_ath": -0.75,    # -75% от ATH
        "fear_greed_max": 10,           # Extreme fear
        "rsi_max": 20,                  # Deeply oversold
        "vol_percentile_min": 0.90,     # Extreme volatility
    }
    
    # Local bottom
    LOCAL_BOTTOM = {
        "drawdown_from_52w": -0.30,    # -30% от 52w high
        "fear_greed_max": 25,           # Fear
        "rsi_max": 30,                  # Oversold
        "price_below_200ma": -0.20,     # 20%+ ниже 200MA
    }
    
    # === TOP DETECTION ===
    
    # Global top (очень редкий сигнал)
    GLOBAL_TOP = {
        "near_ath_pct": 0.95,           # В пределах 5% от ATH
        "fear_greed_min": 85,           # Extreme greed
        "rsi_min": 80,                  # Deeply overbought
        "price_above_200ma": 0.80,      # 80%+ выше 200MA
    }
    
    # Local top
    LOCAL_TOP = {
        "near_52w_high_pct": 0.90,     # В пределах 10% от 52w high
        "fear_greed_min": 70,           # Greed
        "rsi_min": 70,                  # Overbought
        "price_above_200ma": 0.40,      # 40%+ выше 200MA
    }
    
    # === CYCLE PHASES ===
    
    ACCUMULATION = {
        "drawdown_min": -0.50,
        "fear_greed_max": 30,
        "rsi_max": 40,
        "ma_200_slope_max": 0,
    }
    
    CAPITULATION = {
        "drawdown_min": -0.40,
        "fear_greed_max": 20,
        "vol_spike": True,
        "volume_ratio_min": 2.0,
    }
    
    DISTRIBUTION = {
        "near_ath_pct": 0.85,
        "fear_greed_min": 65,
        "rsi_min": 60,
        "ma_50_below_ma_200": False,
    }


# ============================================================
# CYCLE POSITION ENGINE
# ============================================================

class CyclePositionEngine:
    """
    Определяет позицию в рыночном цикле и генерирует сигналы.
    """
    
    def __init__(self):
        self.thresholds = CycleThresholds()
    
    def analyze(self, metrics: CycleMetrics) -> CyclePosition:
        """
        Главный метод анализа.
        """
        reasons = []
        
        # 1. Вычисляем cycle position (0-100)
        cycle_pos = self._calculate_cycle_position(metrics)
        
        # 2. Определяем proximity к дну/вершине
        bottom_prox = self._calculate_bottom_proximity(metrics)
        top_prox = self._calculate_top_proximity(metrics)
        
        # 3. Определяем фазу цикла
        phase, phase_conf = self._determine_phase(metrics, cycle_pos, bottom_prox, top_prox)
        
        # 4. Детектим сигналы дна/вершины
        bt_signal, signal_strength = self._detect_bottom_top(metrics, bottom_prox, top_prox)
        
        # 5. Генерируем торговый сигнал
        action, action_conf, size_mod = self._generate_action(
            metrics, phase, bt_signal, signal_strength, bottom_prox, top_prox
        )
        
        # 6. Собираем reasons
        reasons = self._compile_reasons(
            metrics, phase, bt_signal, action, bottom_prox, top_prox
        )
        
        return CyclePosition(
            phase=phase,
            phase_confidence=phase_conf,
            cycle_position=cycle_pos,
            bottom_proximity=bottom_prox,
            top_proximity=top_prox,
            bottom_top_signal=bt_signal,
            signal_strength=signal_strength,
            action=action,
            action_confidence=action_conf,
            size_modifier=size_mod,
            vs_ath_pct=metrics.drawdown_from_ath,
            vs_200ma_pct=(metrics.current_price / metrics.ma_200 - 1) if metrics.ma_200 > 0 else 0,
            rsi=metrics.rsi_14,
            fear_greed=metrics.fear_greed,
            reasons=reasons,
        )
    
    def _calculate_cycle_position(self, m: CycleMetrics) -> float:
        """
        Cycle position: 0 = абсолютное дно, 100 = абсолютная вершина.
        Комбинирует несколько метрик.
        """
        scores = []
        
        # 1. Position в 52-week range (вес 30%)
        if m.ath_52w > m.atl_52w:
            range_pos = (m.current_price - m.atl_52w) / (m.ath_52w - m.atl_52w)
            range_pos = max(0, min(1, range_pos))
            scores.append((range_pos * 100, 0.30))
        
        # 2. RSI (вес 25%)
        rsi_score = m.rsi_14  # Already 0-100
        scores.append((rsi_score, 0.25))
        
        # 3. Fear & Greed (вес 20%)
        fg_score = m.fear_greed  # Already 0-100
        scores.append((fg_score, 0.20))
        
        # 4. Distance from 200MA (вес 15%)
        if m.ma_200 > 0:
            ma_dist = (m.current_price / m.ma_200 - 1)
            # Normalize: -50% = 0, +100% = 100
            ma_score = (ma_dist + 0.5) / 1.5 * 100
            ma_score = max(0, min(100, ma_score))
            scores.append((ma_score, 0.15))
        
        # 5. Drawdown from ATH (вес 10%)
        # -80% = 0, 0% = 100
        dd_score = (1 + m.drawdown_from_ath) * 100
        dd_score = max(0, min(100, dd_score))
        scores.append((dd_score, 0.10))
        
        # Weighted average
        total_weight = sum(w for _, w in scores)
        if total_weight > 0:
            cycle_pos = sum(s * w for s, w in scores) / total_weight
        else:
            cycle_pos = 50
        
        return round(cycle_pos, 1)
    
    def _calculate_bottom_proximity(self, m: CycleMetrics) -> float:
        """
        Proximity к дну: 0 = далеко от дна, 1 = на дне.
        """
        signals = []
        
        # Drawdown severity
        if m.drawdown_from_ath <= -0.75:
            signals.append(1.0)
        elif m.drawdown_from_ath <= -0.50:
            signals.append(0.7)
        elif m.drawdown_from_ath <= -0.30:
            signals.append(0.4)
        else:
            signals.append(0.0)
        
        # RSI oversold
        if m.rsi_14 <= 20:
            signals.append(1.0)
        elif m.rsi_14 <= 30:
            signals.append(0.7)
        elif m.rsi_14 <= 40:
            signals.append(0.3)
        else:
            signals.append(0.0)
        
        # Fear & Greed
        if m.fear_greed <= 10:
            signals.append(1.0)
        elif m.fear_greed <= 25:
            signals.append(0.7)
        elif m.fear_greed <= 40:
            signals.append(0.3)
        else:
            signals.append(0.0)
        
        # Below 200MA
        if m.ma_200 > 0:
            below_ma = (m.current_price / m.ma_200 - 1)
            if below_ma <= -0.30:
                signals.append(1.0)
            elif below_ma <= -0.15:
                signals.append(0.5)
            elif below_ma < 0:
                signals.append(0.2)
            else:
                signals.append(0.0)
        
        # Volatility spike (capitulation signal)
        if m.vol_percentile >= 0.95:
            signals.append(0.8)
        elif m.vol_percentile >= 0.80:
            signals.append(0.4)
        else:
            signals.append(0.0)
        
        return round(sum(signals) / len(signals), 2) if signals else 0.0
    
    def _calculate_top_proximity(self, m: CycleMetrics) -> float:
        """
        Proximity к вершине: 0 = далеко от вершины, 1 = на вершине.
        """
        signals = []
        
        # Near ATH
        if m.drawdown_from_ath >= -0.05:
            signals.append(1.0)
        elif m.drawdown_from_ath >= -0.15:
            signals.append(0.6)
        elif m.drawdown_from_ath >= -0.25:
            signals.append(0.3)
        else:
            signals.append(0.0)
        
        # RSI overbought
        if m.rsi_14 >= 80:
            signals.append(1.0)
        elif m.rsi_14 >= 70:
            signals.append(0.7)
        elif m.rsi_14 >= 60:
            signals.append(0.3)
        else:
            signals.append(0.0)
        
        # Fear & Greed (greed)
        if m.fear_greed >= 85:
            signals.append(1.0)
        elif m.fear_greed >= 70:
            signals.append(0.7)
        elif m.fear_greed >= 55:
            signals.append(0.3)
        else:
            signals.append(0.0)
        
        # Above 200MA
        if m.ma_200 > 0:
            above_ma = (m.current_price / m.ma_200 - 1)
            if above_ma >= 0.80:
                signals.append(1.0)
            elif above_ma >= 0.50:
                signals.append(0.6)
            elif above_ma >= 0.25:
                signals.append(0.3)
            else:
                signals.append(0.0)
        
        return round(sum(signals) / len(signals), 2) if signals else 0.0
    
    def _determine_phase(
        self, m: CycleMetrics, cycle_pos: float, bottom_prox: float, top_prox: float
    ) -> Tuple[CyclePhase, float]:
        """
        Определяет фазу цикла.
        """
        # Check for extreme phases first
        
        # Capitulation
        if (bottom_prox >= 0.7 and m.vol_percentile >= 0.80 and 
            m.fear_greed <= 20 and m.volume_ratio >= 1.5):
            return CyclePhase.CAPITULATION, min(0.9, bottom_prox)
        
        # Accumulation
        if bottom_prox >= 0.5 and m.ma_200_slope <= 0 and m.fear_greed <= 35:
            return CyclePhase.ACCUMULATION, min(0.8, bottom_prox)
        
        # Distribution
        if top_prox >= 0.6 and m.fear_greed >= 60:
            return CyclePhase.DISTRIBUTION, min(0.8, top_prox)
        
        # Bull phases
        if m.ma_50 > m.ma_200 and m.ma_200_slope > 0:
            if cycle_pos >= 75:
                return CyclePhase.LATE_BULL, 0.6
            elif cycle_pos >= 50:
                return CyclePhase.MID_BULL, 0.7
            else:
                return CyclePhase.EARLY_BULL, 0.6
        
        # Bear phases
        if m.ma_50 < m.ma_200 or m.ma_200_slope < 0:
            if cycle_pos <= 25:
                if bottom_prox >= 0.4:
                    return CyclePhase.CAPITULATION, 0.5
                return CyclePhase.MID_BEAR, 0.6
            else:
                return CyclePhase.EARLY_BEAR, 0.5
        
        # Default
        return CyclePhase.MID_BEAR, 0.4
    
    def _detect_bottom_top(
        self, m: CycleMetrics, bottom_prox: float, top_prox: float
    ) -> Tuple[BottomTopSignal, float]:
        """
        Детектирует сигналы дна/вершины.
        """
        # Global bottom (очень редкий)
        if (m.drawdown_from_ath <= -0.75 and 
            m.fear_greed <= 10 and 
            m.rsi_14 <= 20 and
            m.vol_percentile >= 0.90):
            return BottomTopSignal.GLOBAL_BOTTOM, 0.9
        
        # Local bottom
        if (bottom_prox >= 0.6 and
            m.rsi_14 <= 35 and
            m.fear_greed <= 30):
            strength = min(0.8, bottom_prox * 0.9)
            return BottomTopSignal.LOCAL_BOTTOM, strength
        
        # Global top (очень редкий)
        if (m.drawdown_from_ath >= -0.05 and
            m.fear_greed >= 85 and
            m.rsi_14 >= 80):
            return BottomTopSignal.GLOBAL_TOP, 0.9
        
        # Local top
        if (top_prox >= 0.6 and
            m.rsi_14 >= 70 and
            m.fear_greed >= 65):
            strength = min(0.8, top_prox * 0.9)
            return BottomTopSignal.LOCAL_TOP, strength
        
        return BottomTopSignal.NO_SIGNAL, 0.0
    
    def _generate_action(
        self, m: CycleMetrics, phase: CyclePhase, 
        bt_signal: BottomTopSignal, signal_strength: float,
        bottom_prox: float, top_prox: float
    ) -> Tuple[ActionSignal, float, float]:
        """
        Генерирует торговый сигнал на основе всех факторов.
        
        Returns: (action, confidence, size_modifier)
        """
        # STRONG_BUY: Global/Local bottom с высокой уверенностью
        if bt_signal == BottomTopSignal.GLOBAL_BOTTOM:
            return ActionSignal.STRONG_BUY, signal_strength, 1.5
        
        if bt_signal == BottomTopSignal.LOCAL_BOTTOM and signal_strength >= 0.6:
            return ActionSignal.STRONG_BUY, signal_strength * 0.9, 1.2
        
        # BUY: Accumulation phase или приближение к дну
        if phase == CyclePhase.ACCUMULATION:
            return ActionSignal.BUY, 0.6, 1.0
        
        if phase == CyclePhase.CAPITULATION and bottom_prox >= 0.5:
            # Осторожная покупка на капитуляции
            return ActionSignal.BUY, 0.5, 0.7
        
        if phase == CyclePhase.EARLY_BULL:
            return ActionSignal.BUY, 0.6, 0.9
        
        # STRONG_SELL: Global/Local top
        if bt_signal == BottomTopSignal.GLOBAL_TOP:
            return ActionSignal.STRONG_SELL, signal_strength, 1.5
        
        if bt_signal == BottomTopSignal.LOCAL_TOP and signal_strength >= 0.6:
            return ActionSignal.STRONG_SELL, signal_strength * 0.9, 1.2
        
        # SELL: Distribution или late bull
        if phase == CyclePhase.DISTRIBUTION:
            return ActionSignal.SELL, 0.6, 1.0
        
        if phase == CyclePhase.LATE_BULL and top_prox >= 0.4:
            return ActionSignal.SELL, 0.5, 0.8
        
        if phase == CyclePhase.EARLY_BEAR:
            return ActionSignal.SELL, 0.5, 0.7
        
        # HOLD: всё остальное
        return ActionSignal.HOLD, 0.5, 1.0
    
    def _compile_reasons(
        self, m: CycleMetrics, phase: CyclePhase, 
        bt_signal: BottomTopSignal, action: ActionSignal,
        bottom_prox: float, top_prox: float
    ) -> List[str]:
        """
        Собирает причины для сигнала.
        """
        reasons = []
        
        # Phase
        phase_desc = {
            CyclePhase.ACCUMULATION: "Фаза накопления — умные деньги покупают",
            CyclePhase.EARLY_BULL: "Ранний бык — подтверждение тренда",
            CyclePhase.MID_BULL: "Середина бычьего цикла",
            CyclePhase.LATE_BULL: "Поздний бык — осторожно, эйфория",
            CyclePhase.DISTRIBUTION: "Распределение — умные деньги продают",
            CyclePhase.EARLY_BEAR: "Начало медвежьего рынка",
            CyclePhase.MID_BEAR: "Медвежий рынок продолжается",
            CyclePhase.CAPITULATION: "Капитуляция — паника на рынке",
        }
        reasons.append(phase_desc.get(phase, str(phase.value)))
        
        # Bottom/Top signal
        if bt_signal == BottomTopSignal.GLOBAL_BOTTOM:
            reasons.append("🟢 ГЛОБАЛЬНОЕ ДНО — редкий сигнал!")
        elif bt_signal == BottomTopSignal.LOCAL_BOTTOM:
            reasons.append("🟢 Локальное дно — возможность для покупки")
        elif bt_signal == BottomTopSignal.GLOBAL_TOP:
            reasons.append("🔴 ГЛОБАЛЬНАЯ ВЕРШИНА — редкий сигнал!")
        elif bt_signal == BottomTopSignal.LOCAL_TOP:
            reasons.append("🔴 Локальная вершина — фиксируем прибыль")
        
        # Technical context
        if m.rsi_14 <= 30:
            reasons.append(f"RSI oversold ({m.rsi_14:.0f})")
        elif m.rsi_14 >= 70:
            reasons.append(f"RSI overbought ({m.rsi_14:.0f})")
        
        if m.fear_greed <= 25:
            reasons.append(f"Extreme fear ({m.fear_greed:.0f})")
        elif m.fear_greed >= 75:
            reasons.append(f"Extreme greed ({m.fear_greed:.0f})")
        
        if m.drawdown_from_ath <= -0.50:
            reasons.append(f"Глубокая просадка ({m.drawdown_from_ath:.0%} от ATH)")
        
        return reasons


# ============================================================
# POLICY INTEGRATION
# ============================================================

@dataclass
class CyclePolicy:
    """
    Политика на основе позиции в цикле.
    Интегрируется с Asset Allocation.
    """
    # Сигнал
    action: ActionSignal
    action_confidence: float
    
    # Sizing
    base_size_pct: float         # Базовый размер позиции
    adjusted_size_pct: float     # С учётом confidence
    
    # Risk
    max_position_pct: float      # Максимальная позиция
    stop_loss_pct: float         # Рекомендуемый стоп
    
    # Cycle context
    phase: CyclePhase
    cycle_position: float
    bottom_proximity: float
    top_proximity: float
    bottom_top_signal: BottomTopSignal
    
    # Reasoning
    reasons: List[str]


def create_cycle_policy(cycle_pos: CyclePosition, regime_risk: float) -> CyclePolicy:
    """
    Создаёт политику на основе позиции в цикле.
    
    Args:
        cycle_pos: Результат CyclePositionEngine.analyze()
        regime_risk: Risk level из Regime Engine (-1 до +1)
    """
    action = cycle_pos.action
    conf = cycle_pos.action_confidence
    
    # Base size based on action
    base_sizes = {
        ActionSignal.STRONG_BUY: 0.30,   # 30% капитала
        ActionSignal.BUY: 0.15,          # 15%
        ActionSignal.HOLD: 0.00,         # Не менять
        ActionSignal.SELL: -0.15,        # Продать 15%
        ActionSignal.STRONG_SELL: -0.30, # Продать 30%
    }
    base_size = base_sizes.get(action, 0.0)
    
    # Adjust by confidence
    adjusted_size = base_size * conf * cycle_pos.size_modifier
    
    # Apply regime risk overlay
    # В RISK-OFF режиме уменьшаем покупки, увеличиваем продажи
    if regime_risk < -0.3:
        if adjusted_size > 0:
            adjusted_size *= 0.5  # Уменьшаем покупки
        else:
            adjusted_size *= 1.2  # Увеличиваем продажи
    elif regime_risk > 0.3:
        if adjusted_size > 0:
            adjusted_size *= 1.2  # Увеличиваем покупки
        else:
            adjusted_size *= 0.5  # Уменьшаем продажи
    
    # Max position based on cycle phase
    max_positions = {
        CyclePhase.ACCUMULATION: 0.80,
        CyclePhase.EARLY_BULL: 0.90,
        CyclePhase.MID_BULL: 1.00,
        CyclePhase.LATE_BULL: 0.60,
        CyclePhase.DISTRIBUTION: 0.40,
        CyclePhase.EARLY_BEAR: 0.30,
        CyclePhase.MID_BEAR: 0.20,
        CyclePhase.CAPITULATION: 0.50,  # Можно накапливать
    }
    max_pos = max_positions.get(cycle_pos.phase, 0.50)
    
    # Stop loss based on phase
    stop_losses = {
        CyclePhase.ACCUMULATION: 0.15,
        CyclePhase.EARLY_BULL: 0.12,
        CyclePhase.MID_BULL: 0.10,
        CyclePhase.LATE_BULL: 0.08,
        CyclePhase.DISTRIBUTION: 0.05,
        CyclePhase.EARLY_BEAR: 0.05,
        CyclePhase.MID_BEAR: 0.10,
        CyclePhase.CAPITULATION: 0.20,
    }
    stop_loss = stop_losses.get(cycle_pos.phase, 0.10)
    
    return CyclePolicy(
        action=action,
        action_confidence=conf,
        base_size_pct=base_size,
        adjusted_size_pct=round(adjusted_size, 3),
        max_position_pct=max_pos,
        stop_loss_pct=stop_loss,
        phase=cycle_pos.phase,
        cycle_position=cycle_pos.cycle_position,
        bottom_proximity=cycle_pos.bottom_proximity,
        top_proximity=cycle_pos.top_proximity,
        bottom_top_signal=cycle_pos.bottom_top_signal,
        reasons=cycle_pos.reasons,
    )
