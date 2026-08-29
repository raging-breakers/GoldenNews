"""Generate the local GOLD morning brief page (RSS free; AI summaries via Cloud)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.calendar_fetch import resolve_calendar  # noqa: E402
from src.collect import collect_markets, collect_news, load_calendar_events  # noqa: E402
from src.render import render_html, write_outputs  # noqa: E402
from src.score import compute_bias  # noqa: E402


def _json_default(obj: object) -> object:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"not serializable: {type(obj)}")


def build_brief(
    *,
    cfg: dict,
    calendar_path: Path,
    refresh_calendar: bool,
) -> dict:
    tz_name = cfg.get("timezone") or "Asia/Tokyo"
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)

    calendar, cal_status = resolve_calendar(
        calendar_path,
        tz,
        cfg.get("calendar") or {},
        force_refresh=refresh_calendar,
    )
    print(f"Calendar: {cal_status}")

    markets = collect_markets(cfg["symbols"])
    news_cfg = cfg.get("news") or {}
    news = collect_news(
        news_cfg.get("feeds") or [],
        lookback_hours=int(news_cfg.get("lookback_hours") or 24),
        max_items=int(news_cfg.get("max_items") or 5),
    )
    cal_view = load_calendar_events(calendar, now, tz)
    bias = compute_bias(
        markets,
        news,
        cal_view["today"],
        cfg.get("thresholds") or {},
        news_cfg,
    )
    page_cfg = cfg.get("page") or {}
    return {
        "generated_at": now.isoformat(timespec="seconds"),
        "timezone": tz_name,
        "title": page_cfg.get("title") or "GOLD Morning Brief",
        "disclaimer": page_cfg.get("disclaimer") or "",
        "markets": markets,
        "calendar_view": cal_view,
        "news": news,
        "bias": bias,
        "ai_summaries_ready": False,
    }


def render_brief_dict(brief: dict) -> str:
    generated_at = datetime.fromisoformat(brief["generated_at"])
    return render_html(
        title=brief.get("title") or "GOLD Morning Brief",
        disclaimer=brief.get("disclaimer") or "",
        generated_at=generated_at,
        markets=brief.get("markets") or {},
        calendar_view=brief.get("calendar_view") or {},
        news=brief.get("news") or [],
        bias=brief.get("bias") or {},
    )


def write_brief_and_html(brief: dict, out_dir: Path, archive_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    brief_path = out_dir / "brief.json"
    brief_path.write_text(
        json.dumps(brief, ensure_ascii=False, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    day = datetime.fromisoformat(brief["generated_at"]).strftime("%Y-%m-%d")
    html = render_brief_dict(brief)
    return write_outputs(html, out_dir, archive_dir, day)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate GOLD morning brief HTML")
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument("--calendar", type=Path, default=ROOT / "calendar.json")
    parser.add_argument("--refresh-calendar", action="store_true")
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    brief = build_brief(
        cfg=cfg,
        calendar_path=args.calendar,
        refresh_calendar=args.refresh_calendar,
    )
    out_path = write_brief_and_html(brief, ROOT / "out", ROOT / "archive")
    n = len(brief.get("news") or [])
    print(f"Wrote {out_path}")
    print(f"Wrote {ROOT / 'out' / 'brief.json'} ({n} news; ai_summary_ja empty until Cloud)")
    print(f"Bias: {brief['bias']['direction']} (total={brief['bias']['total']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
