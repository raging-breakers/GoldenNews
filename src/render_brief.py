"""Re-render HTML from out/brief.json after Cloud fills ai_summary_ja fields."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.main import write_brief_and_html  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Render brief.json → index.html")
    parser.add_argument(
        "--brief",
        type=Path,
        default=ROOT / "out" / "brief.json",
        help="Path to brief.json",
    )
    args = parser.parse_args()

    if not args.brief.exists():
        print(f"Missing {args.brief}. Run: python -m src.main", file=sys.stderr)
        return 1

    brief = json.loads(args.brief.read_text(encoding="utf-8"))
    news = brief.get("news") or []
    filled = sum(1 for n in news if (n.get("ai_summary_ja") or "").strip())
    brief["ai_summaries_ready"] = filled == len(news) and len(news) > 0

    out_path = write_brief_and_html(brief, ROOT / "out", ROOT / "archive")
    print(f"Wrote {out_path}")
    print(f"AI summaries: {filled}/{len(news)}")
    if news and filled < len(news):
        print("Warning: some ai_summary_ja fields are still empty", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
