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
    
    ВАЖНО: Используем ТОЛЬКО Dir как главный сигнал.
    Dir уже агрегирует P(BEAR), Momentum и другие факторы.
    Добавление их отдельно = двойной счёт.
    
    TailRisk — бинарный override для экстремальных ситуаций.
    """
    
    dir_value = metrics['dir']  # [-1, +1]
    tail_active = metrics['tail_risk_active']
    tail_polarity = metrics['tail_polarity']
    
    # Базовый score из Dir (только downside)
    base_score = max(0, -dir_value)  # [0, 1]
    
    # TailRisk override — минимум 0.7 при активном downside tail
    if tail_active and tail_polarity == 'downside':
        hedge_score = max(0.7, base_score)
    else:
        hedge_score = base_score
    
    return hedge_score
```

**Почему так:**
- Dir = -0.86 уже означает сильный downside risk
- P(BEAR) = 57% коррелирует с Dir (не независимый фактор)
- Momentum = -0.62 тоже коррелирует с Dir
- Складывать их = считать один сигнал 3 раза

### 2.2 Hedge Ratio (размер хеджа)

```python
def calculate_hedge_ratio(hedge_score, confidence, tail_risk_active, vol_z):
    """
    Hedge Ratio = доля volatile exposure для хеджирования
    """
    
    # Базовый ratio от hedge_score
    base_ratio = hedge_score  # [0, 1]
    
    # Корректировка на confidence
    # ВАЖНО: При TailRisk НЕ снижаем из-за низкой confidence
    # Низкая confidence + TailRisk = неопределённость, но риск реален
    if tail_risk_active:
        confidence_adj = 1.0  # Не снижаем
    else:
        confidence_adj = 0.7 + 0.3 * confidence  # [0.7, 1.0]
    
    # Корректировка на волатильность (прокси IV)
    # Высокая vol_z = дорогие премии
    if vol_z > 1.5:
        vol_adj = 0.7
    elif vol_z > 1.0:
        vol_adj = 0.85
    else:
        vol_adj = 1.0
    
    hedge_ratio = base_ratio * confidence_adj * vol_adj
    
    return min(0.75, max(0.0, hedge_ratio))  # Cap at 75%
```

**Исправлен Confidence парадокс:**
- Раньше: низкая confidence → меньше хеджа (даже при TailRisk!)
- Теперь: при TailRisk confidence_adj = 1.0 (не режем защиту)

### 2.3 Premium Budget

```python
def calculate_premium_budget(tvl, volatile_exposure, hedge_ratio):
    """
    Бюджет на премии привязан к TVL, не к fees.
    
    Fees — переменная величина, падает в BEAR.
    Привязка к fees = проциклично снижаем защиту.
    """
    
    # Целевая стоимость защиты: 0.5% от хеджируемой суммы за 14 дней
    # ≈ 1.3% годовых — разумная "страховка"
    hedge_notional = volatile_exposure * hedge_ratio
    max_premium = hedge_notional * 0.005  # 0.5%
    
    # Абсолютный cap: не более 1% от TVL за 14 дней
    absolute_cap = tvl * 0.01
    
    return min(max_premium, absolute_cap)
```

**Почему не от fees:**
- Fees в BEAR падают → бюджет падает → меньше защиты
- Это проциклично и опасно
- TVL стабильнее как база

---

## 3. Типы пар и стратегии хеджирования

### Проблема: IL зависит от типа пары

PUT ETH хеджирует падение ETH. Но IL — функция **относительного** движения пары.

| Тип пары | Пример | IL возникает когда | Хедж инструмент |
|----------|--------|-------------------|-----------------|
| Volatile/Stable | ETH-USDC | ETH движется | PUT ETH ✅ |
| Volatile/Stable | BTC-USDT | BTC движется | PUT BTC ✅ |
| Volatile/Volatile | ETH-BTC | ETH/BTC ratio меняется | Сложно ⚠️ |
| Alt/Volatile | ZRO-ETH | ZRO/ETH ratio меняется | Нет инструментов ❌ |
| Stable/Volatile | USDT-BNB | BNB движется | PUT BNB (если есть) |

### Классификация позиций

```python
def classify_position_for_hedge(token0, token1):
    """
    Определяем можно ли и как хеджировать позицию
    """
    
    STABLES = {'USDC', 'USDT', 'DAI', 'BUSD', 'FDUSD'}
    HEDGEABLE = {'ETH', 'WETH', 'BTC', 'WBTC', 'BTCB'}  # Есть опционы на DEX
    
    t0_stable = token0 in STABLES
    t1_stable = token1 in STABLES
    t0_hedgeable = token0 in HEDGEABLE
    t1_hedgeable = token1 in HEDGEABLE
    
    # Volatile/Stable — идеальный случай
    if t0_stable and t1_hedgeable:
        return {'hedgeable': True, 'underlying': token1, 'type': 'PUT'}
    if t1_stable and t0_hedgeable:
        return {'hedgeable': True, 'underlying': token0, 'type': 'PUT'}
    
    # Volatile/Volatile (ETH-BTC) — сложный случай
    if t0_hedgeable and t1_hedgeable:
        return {
            'hedgeable': 'partial',
            'underlying': 'both',
            'type': 'RATIO',
            'note': 'PUT на один актив не компенсирует IL полностью'
        }
    
    # Alt/Volatile или Alt/Alt — не хеджируем
    return {'hedgeable': False, 'reason': 'Нет ликвидных опционов'}
```

### Рекомендации по типам пар

**✅ Полностью хеджируемые (Volatile/Stable):**
- WETH-USDC → PUT ETH
- WBTC-USDT → PUT BTC
- WBNB-USDT → PUT BNB (если доступен)

**⚠️ Частично хеджируемые (Volatile/Volatile):**
- WBTC-WETH → Можно PUT ETH, но:
  - Если ETH падает сильнее BTC → хедж работает
  - Если BTC падает сильнее ETH → хедж не помогает
  - Опционально: PUT ETH + PUT BTC (дорого)

**❌ Не хеджируемые (с Alt токенами):**
- ZRO-WETH, PENDLE-WETH, ASTER-USDT
- Нет ликвидных опционов на alt токены
- Риск принимается как есть

### Текущий портфель по типам

```
Полностью хеджируемые:     $0 (0%)
  (нет чистых ETH/USDC, BTC/USDT)

Частично хеджируемые:      $11,072 (37%)
  WBTC-WETH: $11,072

С BNB (если есть опционы): $5,902 (19%)
  USDT-WBNB: $5,902

Не хеджируемые:            $13,302 (44%)
  ASTER-USDT: $7,440
  ZRO-WETH: $1,608
  ZEC-USDT: $1,349
  ZEC-WBNB: $1,108
  PENDLE-WETH: $1,754
```

---

## 4. Пороговые значения (Thresholds)

### Триггеры для хеджирования

| Условие | Порог | Действие |
|---------|-------|----------|
| TailRisk Active + Downside | **Override** | Hedge Score ≥ 0.7 автоматически |
| Dir < -0.7 | **Высокий** | Hedge Score ≥ 0.7 |
| Dir -0.4 до -0.7 | **Умеренный** | Hedge Score 0.4-0.7, рассмотреть |
| Dir > -0.4 | **Низкий** | Hedge Score < 0.4, не хеджировать |

### Решение по Hedge Score

| Hedge Score | Действие |
|-------------|----------|
| ≥ 0.6 | Хедж рекомендуется |
| 0.4 - 0.6 | Рассмотреть хедж |
| < 0.4 | Не хеджировать |

### Vol_z корректировки (прокси IV)

| Vol_z | IV Percentile | Корректировка |
|-------|---------------|---------------|
| < 0.5 | LOW | vol_adj = 1.0 (дешёвые премии) |
| 0.5 - 1.0 | NORMAL | vol_adj = 1.0 |
| 1.0 - 1.5 | ELEVATED | vol_adj = 0.85 |
| > 1.5 | HIGH | vol_adj = 0.7 (дорогие премии) |

---

## 5. Расчёт экспозиции портфеля

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

## 6. Delta LP позиций

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

## 7. Оценка премий и Break-Even

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

## 8. Алгоритм принятия решения

```python
def hedge_decision(regime_data, positions):
    """
    Главный алгоритм принятия решения о хедже
    """
    
    # 1. Извлекаем метрики из Regime Engine
    dir_value = regime_data['risk']['risk_level']
    tail_active = regime_data['asset_allocation']['meta']['tail_risk_active']
    tail_polarity = regime_data['asset_allocation']['meta'].get('tail_polarity', '')
    confidence = regime_data['confidence']['quality_adjusted']
    vol_z = regime_data['metadata']['vol_z']
    
    # 2. Рассчитываем Hedge Score (упрощённая формула)
    base_score = max(0, -dir_value)
    
    if tail_active and tail_polarity == 'downside':
        hedge_score = max(0.7, base_score)
    else:
        hedge_score = base_score
    
    # 3. Классифицируем позиции по типам
    hedgeable_exposure = {'ETH': 0, 'BTC': 0, 'BNB': 0}
    non_hedgeable = 0
    
    for pos in positions:
        classification = classify_position_for_hedge(pos.token0, pos.token1)
        
        if classification['hedgeable'] == True:
            underlying = classification['underlying']
            hedgeable_exposure[underlying] += pos.balance_usd * 0.5
        elif classification['hedgeable'] == 'partial':
            # Volatile/Volatile — добавляем к обоим с коэффициентом
            hedgeable_exposure['ETH'] += pos.balance_usd * 0.25
            hedgeable_exposure['BTC'] += pos.balance_usd * 0.25
        else:
            non_hedgeable += pos.balance_usd
    
    total_hedgeable = sum(hedgeable_exposure.values())
    
    # 4. Проверяем минимальный порог
    if total_hedgeable < 5000:
        return {
            'action': 'NO_HEDGE',
            'reason': f'Hedgeable exposure < $5,000 (${total_hedgeable:.0f})',
            'hedge_score': hedge_score
        }
    
    # 5. Проверяем hedge_score
    if hedge_score < 0.4:
        return {
            'action': 'NO_HEDGE',
            'reason': f'Hedge Score низкий ({hedge_score:.2f})',
            'hedge_score': hedge_score
        }
    
    # 6. Рассчитываем hedge_ratio
    if tail_active:
        confidence_adj = 1.0
    else:
        confidence_adj = 0.7 + 0.3 * confidence
    
    if vol_z > 1.5:
        vol_adj = 0.7
    elif vol_z > 1.0:
        vol_adj = 0.85
    else:
        vol_adj = 1.0
    
    hedge_ratio = min(0.75, hedge_score * confidence_adj * vol_adj)
    
    # 7. Рассчитываем notional для каждого актива
    hedge_notional = {
        asset: exposure * hedge_ratio 
        for asset, exposure in hedgeable_exposure.items()
        if exposure > 0
    }
    
    # 8. Рассчитываем premium budget (0.5% от hedge notional)
    total_notional = sum(hedge_notional.values())
    max_premium = total_notional * 0.005
    
    # 9. Проверяем IV (vol_z как прокси)
    if vol_z > 1.5 and hedge_score < 0.6:
        return {
            'action': 'WAIT',
            'reason': 'IV высокая, hedge_score недостаточен',
            'hedge_score': hedge_score,
            'vol_z': vol_z
        }
    
    # 10. Формируем рекомендацию
    return {
        'action': 'HEDGE',
        'hedge_score': hedge_score,
        'hedge_ratio': hedge_ratio,
        'hedgeable_exposure': hedgeable_exposure,
        'non_hedgeable': non_hedgeable,
        'notional': hedge_notional,
        'max_premium': max_premium,
        'vol_z': vol_z,
        'tail_risk': tail_active
    }
```

---

## 9. Формат рекомендации в отчёте

### Когда хедж НЕ нужен (Score < 0.4)

```
🛡️ Хеджирование:
Статус: Не требуется
Dir: +0.15 | TailRisk: нет
Hedge Score: 0.15

Экспозиция:
  Хеджируемая: ETH $5.5K, BTC $5.5K
  Не хеджируемая: $13.3K (alt пары)
```

### Когда ждём (высокая IV)

```
🛡️ Хеджирование:
Статус: Ожидание
Dir: -0.55 | Hedge Score: 0.55
Vol_z: 1.8 (HIGH) — премии дорогие

Рекомендация: ждём vol_z < 1.0
```

### Когда рекомендуется

```
🛡️ Хеджирование:
Статус: Рекомендуется
Dir: -0.86 | TailRisk: Active ⚠️
Hedge Score: 0.86
Hedge Ratio: 60%

Хеджируемая экспозиция:
  ETH: $5,536 → хедж $3,322
  BTC: $5,536 → хедж $3,322
  
Не хеджируемая: $13,302 (alt пары)

Предложение #1 (ETH):
  PUT ETH $2,250 (-10%)
  Срок: 14d
  Notional: $3,322
  Max премия: $17 (0.5%)
  Площадка: Aevo

Предложение #2 (BTC):
  PUT BTC $76,500 (-10%)
  Срок: 14d
  Notional: $3,322
  Max премия: $17 (0.5%)
  Площадка: Aevo

⚠️ WBTC-WETH ($11K): частичный хедж — 
PUT на один актив не компенсирует IL полностью
```

---

## 10. Площадка: Aevo

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

## 11. Метрики эффективности

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
| 2.0 | 2025-02-23 | Количественная модель, интеграция с Regime Engine |
| 2.1 | 2025-02-23 | Исправления по аудиту: убран двойной счёт, классификация пар |

---

## Изменения v2.0 → v2.1 (по аудиту)

| Проблема | Было | Стало |
|----------|------|-------|
| Двойной счёт | Score = Dir + P(BEAR) + Momentum | Score = Dir only (+ TailRisk override) |
| Confidence парадокс | Низкая conf → меньше хеджа всегда | При TailRisk conf_adj = 1.0 |
| Типы пар | Все пары одинаково | Volatile/Stable, Volatile/Volatile, Alt |
| Premium budget | От fees (проциклично) | От TVL (0.5% от notional) |
| Exposure расчёт | Все активы суммарно | По типам пар |

---

## Ограничения модели (честно)

| Аспект | Статус |
|--------|--------|
| Архитектура | ✅ Есть |
| Интеграция с Regime | ✅ Есть |
| Классификация пар | ✅ Есть |
| Калибровка весов | ❌ Нет (нужен бэктест) |
| Monte Carlo | ❌ Нет |
| CVaR оптимизация | ❌ Нет |
| Delta V3 точная | ❌ Упрощённая |

**Это продвинутая эвристика, не full quant модель.
Для $30K портфеля — достаточно.**

---

## TODO

1. [ ] Реализовать `lp_hedge_engine.py`
2. [ ] Интегрировать Aevo API для получения цен
3. [ ] Добавить блок 🛡️ в `lp_system.py`
4. [ ] Тестирование на реальных данных
