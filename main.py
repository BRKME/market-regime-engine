"""
Market Regime Engine v3.3 — Entry Point

Usage:
  python main.py              # Full run: fetch data → compute → send Telegram
  python main.py --dry-run    # Compute and print, no Telegram
  python main.py --reset      # Reset state to defaults
"""

import sys
import json
import logging
from pathlib import Path

# Load .env if exists (local dev)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.data_pipeline import fetch_all_data
from src.engine import RegimeEngine, default_state, save_state, STATE_FILE
from src.telegram_bot import send_telegram, format_output

# ── Logging ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def main():
    args = set(sys.argv[1:])

    # Reset state
    if "--reset" in args:
        logger.info("Resetting engine state...")
        save_state(default_state())
        logger.info("Done. State reset to defaults.")
        return

    dry_run = "--dry-run" in args

    # ── 1. Fetch data ─────────────────────────────────────
    logger.info("=" * 50)
    logger.info("MARKET REGIME ENGINE v3.3")
    logger.info("=" * 50)

    raw_data = fetch_all_data()

    # ── 2. Run engine ─────────────────────────────────────
    engine = RegimeEngine()
    output = engine.process(raw_data)

    # ── 3. Print output ───────────────────────────────────
    print("\n" + format_output(output))

    # Save full JSON output for debugging
    output_file = Path("state/last_output.json")
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2, default=str)
    logger.info(f"Full output saved to {output_file}")

    # ── 4. Send Telegram ──────────────────────────────────
    if dry_run:
        logger.info("Dry run — skipping Telegram")
    else:
        send_telegram(output)

    # ── 5. Summary ────────────────────────────────────────
    regime = output["regime"]
    conf = output["confidence"]["quality_adjusted"]
    flags = output.get("risk_flags", [])

    logger.info(f"Result: {regime} (conf={conf:.2f}, flags={len(flags)})")

    if flags:
        for f in flags:
            logger.warning(f"  FLAG: {f}")

    logger.info("Done.")


if __name__ == "__main__":
    main()
