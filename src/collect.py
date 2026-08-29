"""Collect gold price, related symbols, and news via free sources (no API keys)."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import feedparser
import requests

YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
USER_AGENT = "GoldenNews/0.1 (personal morning brief)"


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def fetch_yahoo_daily(symbol: str, session: requests.Session | None = None) -> dict[str, Any]:
    """Return last close, previous close, and change metrics. Missing fields stay None."""
    sess = session or _session()
    url = YAHOO_CHART.format(symbol=requests.utils.quote(symbol, safe=""))
    out: dict[str, Any] = {
        "symbol": symbol,
        "last": None,
        "prev": None,
        "change": None,
        "change_pct": None,
        "ok": False,
        "error": None,
    }
    try:
        r = sess.get(url, params={"interval": "1d", "range": "5d"}, timeout=20)
        r.raise_for_status()
        result = r.json()["chart"]["result"][0]
        quotes = result["indicators"]["quote"][0]["close"]
        closes = [c for c in quotes if c is not None]
        if len(closes) < 2:
            out["error"] = "not enough closes"
            return out
        last, prev = closes[-1], closes[-2]
        change = last - prev
        out.update(
            {
                "last": last,
                "prev": prev,
                "change": change,
                "change_pct": (change / prev) * 100 if prev else None,
                "ok": True,
            }
        )
    except Exception as e:  # noqa: BLE001 — keep page generation resilient
        out["error"] = str(e)
    return out


def collect_markets(symbols: dict[str, str]) -> dict[str, dict[str, Any]]:
    sess = _session()
    return {name: fetch_yahoo_daily(sym, sess) for name, sym in symbols.items()}


def _entry_time(entry: Any) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        t = getattr(entry, key, None)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def collect_news(
    feeds: list[dict[str, str]],
    *,
    lookback_hours: int = 24,
    max_items: int = 5,
    gold_keywords: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Pull RSS items, filter roughly to gold-related, dedupe, keep newest."""
    sess = _session()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    keywords = [k.lower() for k in (gold_keywords or ["gold", "xau", "bullion", "precious metal"])]
    seen: set[str] = set()
    items: list[dict[str, Any]] = []

    for feed in feeds:
        name = feed.get("name", "feed")
        url = feed["url"]
        try:
            # Prefer requests so we control UA; feedparser can parse the body
            resp = sess.get(url, timeout=20)
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
        except Exception:  # noqa: BLE001
            continue

        for entry in parsed.entries:
            title = (entry.get("title") or "").strip()
            link = (entry.get("link") or "").strip()
            summary = (entry.get("summary") or entry.get("description") or "").strip()
            summary = re.sub(r"<[^>]+>", " ", summary)
            summary = re.sub(r"\s+", " ", summary).strip()
            if not title:
                continue
            blob = f"{title} {summary}".lower()
            if not any(k in blob for k in keywords):
                # Keep general macro feeds from drowning the page, but allow Kitco-all
                if "kitco" not in name.lower():
                    continue
            key = link or title.lower()
            if key in seen:
                continue
            when = _entry_time(entry)
            if when and when < cutoff:
                continue
            seen.add(key)
            nid = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
            items.append(
                {
                    "id": nid,
                    "title": title,
                    "link": link,
                    "source": name,
                    "summary": summary[:280],
                    "published": when.isoformat() if when else None,
                    # Filled later by Cursor Cloud Automation (Japanese AI summary)
                    "ai_summary_ja": None,
                }
            )

    items.sort(key=lambda x: x["published"] or "", reverse=True)
    return items[:max_items]


def load_calendar_events(
    calendar: dict[str, Any],
    today: datetime,
    tz: ZoneInfo,
) -> dict[str, list[dict[str, Any]]]:
    """Split events into today / week ahead (high impact)."""
    local_today = today.astimezone(tz).date()
    events = list(calendar.get("events") or [])
    events.extend(calendar.get("manual_events") or [])

    today_events: list[dict[str, Any]] = []
    week_events: list[dict[str, Any]] = []

    for ev in events:
        try:
            d = datetime.strptime(ev["date"], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            continue
        delta = (d - local_today).days
        if delta == 0:
            today_events.append(ev)
        if 0 <= delta <= 4 and ev.get("impact") == "high":
            week_events.append(ev)

    today_events.sort(key=lambda e: e.get("time_jst") or "99:99")
    week_events.sort(key=lambda e: (e.get("date"), e.get("time_jst") or "99:99"))
    return {"today": today_events, "week": week_events[:3]}
