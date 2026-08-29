"""Economic calendar fetch (Forex Factory mirror via Fair Economy — no API key)."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

import requests

USER_AGENT = "gold-news/0.1 (personal morning brief)"

# Prefer XML: JSON endpoint is easily rate-limited (429)
DEFAULT_FEEDS = [
    "https://nfs.faireconomy.media/ff_calendar_thisweek.xml",
    "https://nfs.faireconomy.media/ff_calendar_nextweek.xml",
]

# Title substrings (case-insensitive) → gold relevance + Japanese note
GOLD_EVENT_HINTS: list[tuple[str, str, str]] = [
    ("non-farm", "high", "雇用・ドル・金利反応が大きい"),
    ("nonfarm", "high", "雇用・ドル・金利反応が大きい"),
    ("nfp", "high", "雇用・ドル・金利反応が大きい"),
    ("payroll", "high", "雇用・ドル・金利反応が大きい"),
    ("cpi", "high", "インフレ→金利期待→金に直結しやすい"),
    ("pce", "high", "Fed重視のインフレ指標。金利期待に影響"),
    ("fomc", "high", "金融政策。方向よりボラ拡大に注意"),
    ("interest rate", "high", "政策金利決定。金の重要材料"),
    ("fed ", "high", "Fed関連発言・決定はドル・金利経由で金に波及"),
    ("federal reserve", "high", "Fed関連。ドル・金利経由で金に波及"),
    ("jackson hole", "high", "主要中銀シンポジウム。ボラ注意"),
    ("gdp", "medium", "景気材料。ドル反応を通じて金に波及しうる"),
    ("ism", "medium", "景気・ドル材料"),
    ("retail sales", "medium", "景気材料"),
    ("unemployment", "high", "雇用・ドル材料"),
    ("jobless", "medium", "雇用関連"),
]


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, application/xml, text/xml, */*",
        }
    )
    return s


def _impact_norm(raw: str | None) -> str:
    v = (raw or "").strip().lower()
    if v == "high":
        return "high"
    if v == "medium":
        return "medium"
    return "low"


def _hint_for_title(title: str) -> tuple[str, str] | None:
    t = title.lower()
    for needle, relevance, note in GOLD_EVENT_HINTS:
        if needle in t:
            return relevance, note
    return None


def _parse_ff_xml_datetime(date_s: str, time_s: str | None) -> datetime | None:
    """FF XML dates are MM-DD-YYYY; times like 12:30pm are UTC."""
    date_s = (date_s or "").strip()
    if not date_s:
        return None
    try:
        d = datetime.strptime(date_s, "%m-%d-%Y").date()
    except ValueError:
        return None
    t = (time_s or "").strip().lower()
    utc = ZoneInfo("UTC")
    if not t or t in {"all day", "tentative", "day", "n/a"}:
        return datetime(d.year, d.month, d.day, 0, 0, tzinfo=utc)
    for fmt in ("%I:%M%p", "%I%p"):
        try:
            tm = datetime.strptime(t.replace(" ", ""), fmt).time()
            return datetime(d.year, d.month, d.day, tm.hour, tm.minute, tzinfo=utc)
        except ValueError:
            continue
    return datetime(d.year, d.month, d.day, 0, 0, tzinfo=utc)


def parse_ff_xml(content: bytes) -> list[dict[str, Any]]:
    root = ET.fromstring(content)
    out: list[dict[str, Any]] = []
    for node in root.findall("event"):
        title = (node.findtext("title") or "").strip()
        country = (node.findtext("country") or "").strip()
        date_s = (node.findtext("date") or "").strip()
        time_s = (node.findtext("time") or "").strip()
        dt = _parse_ff_xml_datetime(date_s, time_s)
        if not title or dt is None:
            continue
        out.append(
            {
                "title": title,
                "country": country,
                "date": dt.isoformat(),
                "impact": (node.findtext("impact") or "").strip(),
                "forecast": (node.findtext("forecast") or "").strip(),
                "previous": (node.findtext("previous") or "").strip(),
            }
        )
    return out


def normalize_ff_event(raw: dict[str, Any], tz: ZoneInfo) -> dict[str, Any] | None:
    title = (raw.get("title") or "").strip()
    if not title:
        return None
    country = (raw.get("country") or "").strip() or "—"
    impact = _impact_norm(raw.get("impact"))
    date_raw = raw.get("date")
    if not date_raw:
        return None
    try:
        dt = datetime.fromisoformat(str(date_raw))
    except ValueError:
        return None
    local = dt.astimezone(tz)
    hint = _hint_for_title(title)
    if hint:
        gold_relevance, note = hint
    else:
        gold_relevance = "high" if impact == "high" and country.upper() == "USD" else impact
        note = f"{country} / {impact} impact"
        if raw.get("forecast") or raw.get("previous"):
            bits = []
            if raw.get("forecast"):
                bits.append(f"予想 {raw['forecast']}")
            if raw.get("previous"):
                bits.append(f"前回 {raw['previous']}")
            note = note + " — " + "、".join(bits)

    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]
    return {
        "id": f"{local.strftime('%Y-%m-%d')}-{country.lower()}-{slug}",
        "date": local.strftime("%Y-%m-%d"),
        "time_jst": local.strftime("%H:%M"),
        "name": title,
        "country": country,
        "impact": impact,
        "gold_relevance": gold_relevance,
        "note": note,
        "source": "faireconomy",
        "forecast": raw.get("forecast") or "",
        "previous": raw.get("previous") or "",
    }


def fetch_ff_calendar_raw(
    urls: list[str],
    session: requests.Session | None = None,
    *,
    pause_s: float = 1.0,
    max_retries: int = 2,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return (events, errors). Skips 404; retries briefly on 429."""
    sess = session or _session()
    events: list[dict[str, Any]] = []
    errors: list[str] = []
    for i, url in enumerate(urls):
        if i:
            time.sleep(pause_s)
        for attempt in range(max_retries + 1):
            try:
                r = sess.get(url, timeout=25)
                if r.status_code == 404:
                    errors.append(f"404 {url}")
                    break
                if r.status_code == 429:
                    if attempt < max_retries:
                        time.sleep(5 * (attempt + 1))
                        continue
                    errors.append(f"429 rate-limited {url}")
                    break
                r.raise_for_status()
                ctype = (r.headers.get("Content-Type") or "").lower()
                body = r.content.lstrip()
                if body.startswith(b"<!DOCTYPE") or body.startswith(b"<html") or "text/html" in ctype:
                    errors.append(f"non-xml/html response (likely rate-limited) {url}")
                    break
                if url.endswith(".xml") or "xml" in ctype or body.startswith(b"<?xml"):
                    events.extend(parse_ff_xml(r.content))
                else:
                    payload = r.json()
                    if isinstance(payload, list):
                        events.extend(payload)
                    else:
                        errors.append(f"unexpected JSON shape from {url}")
                break
            except Exception as e:  # noqa: BLE001
                if attempt < max_retries:
                    time.sleep(2 * (attempt + 1))
                    continue
                errors.append(f"{url}: {e}")
                break
    return events, errors


def build_calendar_from_ff(
    *,
    tz: ZoneInfo,
    urls: list[str] | None = None,
    countries: list[str] | None = None,
    min_impact: str = "high",
    include_gold_keywords: bool = True,
) -> dict[str, Any]:
    countries = countries or ["USD", "All"]
    raw, errors = fetch_ff_calendar_raw(urls or DEFAULT_FEEDS)
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in raw:
        country = (item.get("country") or "").strip()
        impact = _impact_norm(item.get("impact"))
        title = (item.get("title") or "").strip()

        keep = False
        country_u = country.upper()
        allowed = {c.upper() for c in countries}
        if country_u in allowed:
            rank = {"low": 0, "medium": 1, "high": 2}
            if rank.get(impact, 0) >= rank.get(min_impact, 2):
                keep = True
        if not keep and include_gold_keywords and _hint_for_title(title):
            if impact in {"high", "medium"}:
                keep = True
        if not keep:
            continue

        ev = normalize_ff_event(item, tz)
        if not ev:
            continue
        if ev["id"] in seen:
            continue
        seen.add(ev["id"])
        normalized.append(ev)

    normalized.sort(key=lambda e: (e["date"], e.get("time_jst") or "99:99"))
    return {
        "timezone": str(tz),
        "source": "faireconomy",
        "fetched_at": datetime.now(tz).isoformat(timespec="seconds"),
        "fetch_errors": errors,
        "events": normalized,
        "manual_events": [],
    }


def merge_manual(auto: dict[str, Any], existing: dict[str, Any] | None) -> dict[str, Any]:
    """Preserve manual_events from previous calendar.json."""
    out = dict(auto)
    if existing:
        manual = existing.get("manual_events")
        if isinstance(manual, list):
            out["manual_events"] = manual
    return out


def load_calendar_file(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def save_calendar_file(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_calendar(
    path: Path,
    tz: ZoneInfo,
    cfg: dict[str, Any] | None = None,
    *,
    force_refresh: bool = False,
) -> tuple[dict[str, Any], str]:
    """
    Fetch and update calendar.json when due; otherwise use cache.
    Returns (calendar_dict, status_message).
    """
    cfg = cfg or {}
    existing = load_calendar_file(path)
    cache_hours = float(cfg.get("cache_hours", 6))
    enabled = cfg.get("auto_fetch", True)

    if not enabled:
        if existing:
            return existing, "auto_fetch disabled; using calendar.json"
        return {"timezone": str(tz), "events": [], "manual_events": []}, "no calendar"

    if existing and not force_refresh and existing.get("fetched_at"):
        try:
            fetched = datetime.fromisoformat(existing["fetched_at"])
            if fetched.tzinfo is None:
                fetched = fetched.replace(tzinfo=tz)
            age = datetime.now(tz) - fetched.astimezone(tz)
            # Treat empty auto-events as stale so we retry soon (e.g. weekend → Monday)
            has_auto = bool(existing.get("events"))
            if age <= timedelta(hours=cache_hours) and has_auto:
                return existing, f"cache hit (age {age})"
        except ValueError:
            pass

    try:
        auto = build_calendar_from_ff(
            tz=tz,
            urls=cfg.get("feeds") or DEFAULT_FEEDS,
            countries=cfg.get("countries") or ["USD", "All"],
            min_impact=(cfg.get("min_impact") or "high").lower(),
            include_gold_keywords=bool(cfg.get("include_gold_keywords", True)),
        )
        new_events = auto.get("events") or []
        errors = auto.get("fetch_errors") or []
        if not new_events and existing and (existing.get("events") or existing.get("manual_events")):
            if errors:
                existing = dict(existing)
                existing["fetch_errors"] = errors
                existing["last_fetch_attempt"] = datetime.now(tz).isoformat(timespec="seconds")
                save_calendar_file(path, existing)
                return existing, f"fetch empty ({'; '.join(errors)}); kept previous calendar.json"
        merged = merge_manual(auto, existing)
        save_calendar_file(path, merged)
        n = len(merged.get("events") or [])
        msg = f"fetched {n} events"
        if errors:
            msg += f" (warnings: {'; '.join(errors)})"
        return merged, msg
    except Exception as e:  # noqa: BLE001
        if existing:
            return existing, f"fetch failed ({e}); using calendar.json"
        return {
            "timezone": str(tz),
            "events": [],
            "manual_events": [],
            "fetch_errors": [str(e)],
        }, f"fetch failed ({e}); empty calendar"
