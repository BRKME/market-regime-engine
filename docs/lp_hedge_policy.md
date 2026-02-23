# LP Hedging Policy v2.0

## Цель документа

Количественная политика хеджирования Uniswap V3 LP позиций через опционы, интегрированная с Regime Engine.

---

## 1. Интеграция с Regime Engine

### Ключевые метрики из `last_output.json`

| Метрика | Поле | Описание | Диапазон |
|---------|------|----------|----------|
| **Dir** | `risk.risk_level` | Directional risk | [-1, +1] |
| **TailRisk** | `meta.tail_risk_active` | Хвостовой риск активен | bool |
| **TailPolarity** | `meta.tail_polarity` | Направление хвоста | upside/downside |
| **Confidence** | `confidence.quality_adjusted` | Уверенность модели | [0, 1] |
| **Vol_z** | `metadata.vol_z` | Волатильность (z-score) | [-2, +3] |
| **Uncertainty** | `lp_policy.uncertainty_value` | Неопределённость | [0, 1] |
| **HedgeFlag** | `lp_policy.hedge_recommended` | Рекомендация системы | bool |
| **P(BEAR)** | `probabilities.BEAR` | Вероятность BEAR | [0, 1] |
| **Momentum** | `buckets.Momentum` | Моментум z-score | [-1, +1] |
| **Stability** | `buckets.Stability` | Стабильность z-score | [-1, +1] |

### Текущие значения (пример)

```
Dir:          -0.86  (сильный downside)
TailRisk:     True   (активен)
TailPolarity: downside
Confidence:   0.27   (низкая)
Vol_z:        0.81   (умеренная)
Uncertainty:  0.71   (высокая)
HedgeFlag:    True
P(BEAR):      57.6%
Momentum:     -0.62
Stability:    -1.0
```

---

## 2. Формулы расчёта

### 2.1 Hedge Score (необходимость хеджа)

```python
def calculate_hedge_score(metrics):
    """
    Hedge Score = [0, 1], где 1 = максимальная необходимость хеджа
    """
    
    # Компоненты
    dir_component = max(0, -metrics['dir'])  # [0,1], выше при negative dir
    tail_component = 1.0 if metrics['tail_risk_active'] else 0.0
    bear_component = metrics['p_bear']  # [0,1]
    momentum_component = max(0, -metrics['momentum'])  # [0,1]
    
    # Веса
    W_DIR = 0.35
    W_TAIL = 0.25
    W_BEAR = 0.25
    W_MOMENTUM = 0.15
    
    hedge_score = (
        W_DIR * dir_component +
        W_TAIL * tail_component +
        W_BEAR * bear_component +
        W_MOMENTUM * momentum_component
    )
    
    return min(1.0, hedge_score)
```

### 2.2 Hedge Ratio (размер хеджа)

```python
def calculate_hedge_ratio(hedge_score, confidence, vol_z):
    """
    Hedge Ratio = доля volatile exposure для хеджирования
    """
    
    # Базовый ratio от hedge_score
    base_ratio = hedge_score  # [0, 1]
    
    # Корректировка на confidence
    # Низкая confidence = неуверенность в сигнале = меньше хеджа
    confidence_adj = 0.5 + 0.5 * confidence  # [0.5, 1.0]
    
    # Корректировка на волатильность
    # Высокая vol_z = дорогие премии = меньше хеджа
    if vol_z > 1.5:
        vol_adj = 0.7  # Снижаем из-за дорогих премий
    elif vol_z > 1.0:
        vol_adj = 0.85
    else:
        vol_adj = 1.0
    
    hedge_ratio = base_ratio * confidence_adj * vol_adj
    
    return min(0.75, max(0.0, hedge_ratio))  # Cap at 75%
```

### 2.3 Premium Budget

```python
def calculate_premium_budget(expected_fees_14d, hedge_score):
    """
    Максимальный бюджет на премии
    """
    
    # Базовый бюджет = 50% ожидаемых fees
    base_budget = expected_fees_14d * 0.5
    
    # При высоком hedge_score готовы платить больше
    if hedge_score > 0.8:
        budget_multiplier = 1.5  # До 75% fees
    elif hedge_score > 0.6:
        budget_multiplier = 1.2  # До 60% fees
    else:
        budget_multiplier = 1.0  # 50% fees
    
    return base_budget * budget_multiplier
```

---

## 3. Пороговые значения (Thresholds)

### Триггеры для хеджирования

| Условие | Порог | Действие |
|---------|-------|----------|
| Dir < -0.7 | **Критический** | Хедж обязателен |
| TailRisk = True AND polarity = downside | **Критический** | Хедж обязателен |
| Hedge Score > 0.6 | **Высокий** | Рекомендуется хедж |
| Hedge Score 0.3-0.6 | **Умеренный** | Рассмотреть хедж |
| Hedge Score < 0.3 | **Низкий** | Не хеджировать |

### Корректировки

| Условие | Корректировка |
|---------|---------------|
| Vol_z > 1.5 | Hedge ratio × 0.7 (дорогие премии) |
| Confidence < 0.3 | Hedge ratio × 0.8 (неуверенный сигнал) |
| Uncertainty > 0.7 | Premium budget × 1.2 (больше защиты) |
| P(BEAR) > 0.7 | Hedge ratio × 1.15 (высокая вероятность) |

---

## 4. Расчёт экспозиции портфеля

### 4.1 Общий TVL

```python
tvl_total = sum(position.balance_usd for position in all_positions)
# Пример: $30,276
```

### 4.2 Экспозиция по активам

```python
def calculate_exposure(positions):
    """
    LP позиция 50/50 по активам (упрощение для V3)
    """
    exposure = {'ETH': 0, 'BTC': 0, 'BNB': 0, 'STABLE': 0, 'ALT': 0}
    
    for pos in positions:
        t0, t1 = pos.token0, pos.token1
        value = pos.balance_usd / 2  # 50% каждый токен
        
        exposure[classify_token(t0)] += value
        exposure[classify_token(t1)] += value
    
    return exposure

# Пример:
# ETH:    $8,000  (26%)
# BTC:    $5,500  (18%)
# BNB:    $3,000  (10%)
# STABLE: $7,000  (23%)
# ALT:    $6,800  (23%)
```

### 4.3 Volatile Exposure (хеджируемая часть)

```python
volatile_exposure = exposure['ETH'] + exposure['BTC'] + exposure['BNB']
# Пример: $16,500 (54% от TVL)

# ALT не хеджируем опционами (нет ликвидных инструментов)
# STABLE не требует хеджа
```

---

## 5. Delta LP позиций

### Проблема

LP позиция в V3 имеет динамическую delta, которая зависит от:
- Положения цены в диапазоне
- Ширины диапазона
- Концентрации ликвидности

### Упрощённая модель

```python
def estimate_lp_delta(position, current_price):
    """
    Упрощённая оценка delta LP позиции
    
    Delta ≈ 0.5 когда цена в центре диапазона
    Delta → 1.0 когда цена у нижней границы (больше token0)
    Delta → 0.0 когда цена у верхней границы (больше token1)
    """
    
    price_lower = position.price_lower
    price_upper = position.price_upper
    
    if current_price <= price_lower:
        return 1.0  # 100% в token0
    elif current_price >= price_upper:
        return 0.0  # 100% в token1
    else:
        # Линейная интерполяция (упрощение)
        range_position = (current_price - price_lower) / (price_upper - price_lower)
        return 1.0 - range_position
```

### Hedge Notional

```python
def calculate_hedge_notional(position, hedge_ratio, delta):
    """
    Notional для хеджирования = exposure × hedge_ratio × delta
    """
    return position.balance_usd * 0.5 * hedge_ratio * delta
```

---

## 6. Оценка премий и Break-Even

### 6.1 IV Percentile

```python
def evaluate_iv_percentile(vol_z, historical_vol_z):
    """
    IV percentile относительно истории
    """
    # vol_z из regime engine = текущая волатильность
    # Сравниваем с историческим распределением
    
    if vol_z < 0:
        return 'LOW'      # IV ниже среднего → премии дешёвые
    elif vol_z < 1.0:
        return 'NORMAL'   # IV около среднего
    elif vol_z < 1.5:
        return 'ELEVATED' # IV повышенная
    else:
        return 'HIGH'     # IV высокая → премии дорогие
```

### 6.2 Break-Even анализ

```python
def calculate_break_even(strike_distance_pct, premium_pct):
    """
    При каком падении опцион начинает компенсировать IL?
    
    Break-even = strike_distance + premium
    """
    break_even = strike_distance_pct + premium_pct
    
    return break_even

# Пример:
# Strike: -10% от текущей цены
# Premium: 2% от notional
# Break-even: -12% движение для начала компенсации
```

### 6.3 Expected Payoff vs IL

```python
def evaluate_hedge_efficiency(expected_move, strike_distance, premium, il_estimate):
    """
    Оценка эффективности хеджа
    
    Hedge Edge = Expected_Payoff - Premium
    """
    
    if expected_move > strike_distance:
        expected_payoff = expected_move - strike_distance
    else:
        expected_payoff = 0
    
    hedge_edge = expected_payoff - premium
    
    # Сравниваем с IL
    if hedge_edge > il_estimate * 0.3:
        return 'FAVORABLE'  # Хедж выгоден
    elif hedge_edge > 0:
        return 'MARGINAL'   # На грани
    else:
        return 'UNFAVORABLE'  # Не выгоден
```

---

## 7. Алгоритм принятия решения

```python
def hedge_decision(regime_data, positions, options_data):
    """
    Главный алгоритм принятия решения о хедже
    """
    
    # 1. Извлекаем метрики
    dir = regime_data['risk']['risk_level']
    tail_active = regime_data['asset_allocation']['meta']['tail_risk_active']
    tail_polarity = regime_data['asset_allocation']['meta']['tail_polarity']
    confidence = regime_data['confidence']['quality_adjusted']
    vol_z = regime_data['metadata']['vol_z']
    p_bear = regime_data['probabilities']['BEAR']
    momentum = regime_data['buckets']['Momentum']
    hedge_flag = regime_data['lp_policy']['hedge_recommended']
    
    # 2. Рассчитываем Hedge Score
    hedge_score = calculate_hedge_score({
        'dir': dir,
        'tail_risk_active': tail_active and tail_polarity == 'downside',
        'p_bear': p_bear,
        'momentum': momentum
    })
    
    # 3. Определяем необходимость хеджа
    if hedge_score < 0.3 and not hedge_flag:
        return {
            'action': 'NO_HEDGE',
            'reason': f'Hedge Score низкий ({hedge_score:.2f})',
            'hedge_score': hedge_score
        }
    
    # 4. Рассчитываем параметры хеджа
    hedge_ratio = calculate_hedge_ratio(hedge_score, confidence, vol_z)
    
    # 5. Рассчитываем экспозицию
    exposure = calculate_exposure(positions)
    volatile = exposure['ETH'] + exposure['BTC'] + exposure['BNB']
    
    # 6. Проверяем минимальный порог
    if volatile < 5000:
        return {
            'action': 'NO_HEDGE',
            'reason': f'Volatile exposure < $5,000 (${volatile:.0f})',
            'hedge_score': hedge_score
        }
    
    # 7. Рассчитываем notional для каждого актива
    hedge_notional = {
        'ETH': exposure['ETH'] * hedge_ratio,
        'BTC': exposure['BTC'] * hedge_ratio,
        'BNB': exposure['BNB'] * hedge_ratio if has_bnb_options() else 0
    }
    
    # 8. Оцениваем премии
    iv_percentile = evaluate_iv_percentile(vol_z)
    
    if iv_percentile == 'HIGH' and hedge_score < 0.7:
        return {
            'action': 'WAIT',
            'reason': 'IV высокая, hedge_score недостаточен для оправдания премий',
            'hedge_score': hedge_score,
            'iv_percentile': iv_percentile
        }
    
    # 9. Формируем рекомендацию
    return {
        'action': 'HEDGE',
        'hedge_score': hedge_score,
        'hedge_ratio': hedge_ratio,
        'iv_percentile': iv_percentile,
        'notional': hedge_notional,
        'exposure': exposure,
        'recommendations': generate_option_recommendations(hedge_notional, options_data)
    }
```

---

## 8. Формат рекомендации в отчёте

### Когда хедж НЕ нужен

```
🛡️ Хеджирование:
Статус: Не требуется
Hedge Score: 0.25
Причина: Dir нейтральный (+0.15), TailRisk неактивен

Экспозиция: ETH $8K, BTC $5.5K, BNB $3K
```

### Когда нужен, но дорого

```
🛡️ Хеджирование:
Статус: Ожидание
Hedge Score: 0.55
IV Percentile: HIGH (vol_z=1.8)
Причина: Премии дорогие, ждём снижения IV

Экспозиция: ETH $8K, BTC $5.5K
Target: При vol_z < 1.0 рассмотреть хедж
```

### Когда рекомендуется

```
🛡️ Хеджирование:
Статус: Рекомендуется
Hedge Score: 0.72
Dir: -0.86 | TailRisk: Active (downside)
Hedge Ratio: 45%

Экспозиция:
  ETH: $8,000 (хедж $3,600)
  BTC: $5,500 (хедж $2,475)

Предложение #1 (ETH):
  PUT ETH $2,250 (-10%)
  Срок: 14d
  Notional: $3,600
  Премия: ~$50-70 (1.5%)
  Break-even: -11.5%
  Площадка: Aevo

Предложение #2 (BTC):
  PUT BTC $76,500 (-10%)
  Срок: 14d
  Notional: $2,475
  Премия: ~$35-50 (1.5%)
  Break-even: -11.5%
  Площадка: Aevo
```

---

## 9. Площадка: Aevo

### Почему Aevo

- DEX (не CEX)
- Лучшая ликвидность среди DeFi опционов
- ETH и BTC опционы
- Европейский стиль (settlement at expiry)
- API для интеграции

### Интеграция

```python
# Aevo API endpoints
AEVO_API = "https://api.aevo.xyz"

# Получение цен опционов
GET /options/{underlying}/orderbook?strike={strike}&expiry={expiry}

# Получение IV
GET /options/{underlying}/iv?expiry={expiry}
```

---

## 10. Метрики эффективности

### Post-hoc анализ

1. **Hedge Accuracy** = Правильных решений / Всего решений
2. **Premium Efficiency** = Payoff / Premium spent
3. **IL Reduction** = (IL без хеджа - IL с хеджем) / IL без хеджа
4. **Cost of Protection** = Annual premium / TVL

### Целевые показатели

| Метрика | Цель |
|---------|------|
| Hedge Accuracy | > 60% |
| Premium Efficiency | > 0.8 |
| IL Reduction | > 40% |
| Cost of Protection | < 3% годовых |

---

## Changelog

| Версия | Дата | Изменения |
|--------|------|-----------|
| 1.0 | 2025-02-23 | Первая версия (интуитивная) |
| 1.1 | 2025-02-23 | Добавлен учёт фазы цикла, DEX only |
| 2.0 | 2025-02-23 | Полностью количественная модель, интеграция с Regime Engine |

---

## Изменения v1.1 → v2.0

| Было (v1.1) | Стало (v2.0) |
|-------------|--------------|
| "Фаза цикла" как триггер | Hedge Score на основе Dir, TailRisk, P(BEAR) |
| Hedge ratio по TVL | Hedge ratio = f(score, confidence, vol_z) |
| IV высокая/низкая | IV percentile через vol_z |
| Нет delta расчёта | Упрощённая delta модель для V3 |
| Нет break-even | Break-even = strike + premium |
| Отдельная система | Интеграция с Regime Engine |

---

## TODO

1. [ ] Реализовать `lp_hedge_engine.py`
2. [ ] Интегрировать Aevo API для получения цен и IV
3. [ ] Добавить блок 🛡️ Хеджирование в `lp_system.py`
4. [ ] Тестирование на исторических данных
5. [ ] Калибровка весов в Hedge Score формуле
