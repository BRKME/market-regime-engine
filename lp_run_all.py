"""
LP Intelligence System - Unified Runner
Version: 1.0.0

Запускает все 3 этапа последовательно:
1. lp_monitor.py - Мониторинг текущих позиций
2. lp_opportunities.py - Поиск лучших пулов
3. lp_advisor.py - AI рекомендации
"""

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_monitor():
    """Этап 1: Мониторинг позиций"""
    logger.info("\n" + "=" * 70)
    logger.info("ЭТАП 1: LP MONITOR")
    logger.info("=" * 70)
    
    try:
        from lp_monitor import main as monitor_main
        result = monitor_main()
        if result:
            logger.info("✓ Этап 1 завершён успешно")
            return True
        else:
            logger.warning("⚠️ Этап 1: нет позиций или ошибка подключения")
            return False
    except Exception as e:
        logger.error(f"✗ Этап 1 ошибка: {e}")
        return False


def run_opportunities():
    """Этап 2: Поиск возможностей"""
    logger.info("\n" + "=" * 70)
    logger.info("ЭТАП 2: LP OPPORTUNITIES")
    logger.info("=" * 70)
    
    try:
        from lp_opportunities import main as opportunities_main
        result = opportunities_main()
        if result:
            logger.info("✓ Этап 2 завершён успешно")
            return True
        else:
            logger.warning("⚠️ Этап 2: нет возможностей")
            return False
    except Exception as e:
        logger.error(f"✗ Этап 2 ошибка: {e}")
        return False


def run_advisor():
    """Этап 3: AI рекомендации"""
    logger.info("\n" + "=" * 70)
    logger.info("ЭТАП 3: LP ADVISOR")
    logger.info("=" * 70)
    
    try:
        from lp_advisor import main as advisor_main
        result = advisor_main()
        if result:
            logger.info("✓ Этап 3 завершён успешно")
            return True
        else:
            logger.warning("⚠️ Этап 3: ошибка генерации отчёта")
            return False
    except Exception as e:
        logger.error(f"✗ Этап 3 ошибка: {e}")
        return False


def main():
    """Run all stages"""
    logger.info("=" * 70)
    logger.info("LP INTELLIGENCE SYSTEM v1.0.0")
    logger.info("=" * 70)
    
    results = {
        "monitor": False,
        "opportunities": False,
        "advisor": False,
    }
    
    # Этап 1: Мониторинг (опционально - может не быть RPC)
    results["monitor"] = run_monitor()
    
    # Этап 2: Возможности
    results["opportunities"] = run_opportunities()
    
    # Этап 3: Advisor (работает даже без свежих данных)
    results["advisor"] = run_advisor()
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("ИТОГО")
    logger.info("=" * 70)
    
    for stage, success in results.items():
        status = "✓" if success else "✗"
        logger.info(f"  {status} {stage}")
    
    success_count = sum(results.values())
    logger.info(f"\nУспешно: {success_count}/3 этапов")
    
    return 0 if success_count >= 2 else 1


if __name__ == "__main__":
    sys.exit(main())
