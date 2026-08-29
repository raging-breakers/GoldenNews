"""Rule-based gold bias scoring (no API keys / no ML required)."""

from __future__ import annotations

from typing import Any


REASON_PLUS = {
    "gold": "金の前日比がプラス",
    "dxy": "ドル指数が弱い",
    "us10y": "米金利が低下",
    "news": "セーフヘイブン/利下げ系の話題が多め",
}
REASON_MINUS = {
    "gold": "金の前日比がマイナス",
    "dxy": "ドル指数が強い",
    "us10y": "米金利が上昇",
    "news": "ドル高・タカ派系の話題が多め",
}


def _tri(value: float | None, hi: float, lo: float | None = None) -> int | None:
    """Return +1 / 0 / -1, or None if value missing."""
    if value is None:
        return None
    lower = -hi if lo is None else lo
    if value >= hi:
        return 1
    if value <= lower:
        return -1
    return 0


def score_news_polarity(
    items: list[dict[str, Any]],
    bullish_keywords: list[str],
    bearish_keywords: list[str],
) -> tuple[int | None, dict[str, int]]:
    if not items:
        return None, {"bull": 0, "bear": 0}
    bull = bear = 0
    bulls = [k.lower() for k in bullish_keywords]
    bears = [k.lower() for k in bearish_keywords]
    for it in items:
        blob = f"{it.get('title', '')} {it.get('summary', '')}".lower()
        if any(k in blob for k in bulls):
            bull += 1
        if any(k in blob for k in bears):
            bear += 1
    diff = bull - bear
    if diff >= 2:
        s = 1
    elif diff <= -2:
        s = -1
    else:
        s = 0
    return s, {"bull": bull, "bear": bear}


def compute_bias(
    markets: dict[str, dict[str, Any]],
    news_items: list[dict[str, Any]],
    today_events: list[dict[str, Any]],
    thresholds: dict[str, float],
    news_cfg: dict[str, Any],
) -> dict[str, Any]:
    factors: dict[str, int | None] = {}

    gold_pct = markets.get("gold", {}).get("change_pct")
    dxy_pct = markets.get("dxy", {}).get("change_pct")
    us10y_change = None
    us10y = markets.get("us10y", {})
    if us10y.get("ok") and us10y.get("last") is not None and us10y.get("prev") is not None:
        us10y_change = us10y["last"] - us10y["prev"]

    # Gold: higher = bullish for gold
    factors["gold"] = _tri(gold_pct, thresholds.get("gold_pct", 0.3))

    # DXY: higher dollar = bearish for gold → invert
    raw_dxy = _tri(dxy_pct, thresholds.get("dxy_pct", 0.2))
    factors["dxy"] = (-raw_dxy) if raw_dxy is not None else None

    # US10Y: higher yields = bearish for gold → invert
    raw_y = _tri(us10y_change, thresholds.get("us10y_pts", 0.03))
    factors["us10y"] = (-raw_y) if raw_y is not None else None

    news_score, news_counts = score_news_polarity(
        news_items,
        news_cfg.get("bullish_keywords") or [],
        news_cfg.get("bearish_keywords") or [],
    )
    factors["news"] = news_score

    valid = {k: v for k, v in factors.items() if v is not None}
    if len(valid) < 2:
        direction = "中立"
        total = 0
        data_insufficient = True
    else:
        total = sum(valid.values())
        data_insufficient = False
        if total >= 2:
            direction = "強気寄り"
        elif total <= -2:
            direction = "弱気寄り"
        else:
            direction = "中立"

    reasons: list[str] = []
    for key, val in valid.items():
        if val > 0 and key in REASON_PLUS:
            reasons.append(REASON_PLUS[key])
        elif val < 0 and key in REASON_MINUS:
            reasons.append(REASON_MINUS[key])
        if len(reasons) >= 2:
            break

    if not reasons:
        reasons.append("材料が拮抗、または閾値内の変動")

    caution = "短期材料ベース。継続は要確認"
    high_events = [
        e for e in today_events if e.get("gold_relevance") == "high" or e.get("impact") == "high"
    ]
    if high_events:
        ev = high_events[0]
        t = ev.get("time_jst") or ""
        note = ev.get("note") or "イベント前後はノイズ大・過信禁物"
        label = f"{t + ' ' if t else ''}{ev.get('name', '重要イベント')}"
        caution = f"{label}。{note}"
    if data_insufficient:
        caution = "データ不足のため中立。" + caution
    missing = [k for k, v in factors.items() if v is None]
    if missing and not data_insufficient:
        caution += f"（欠損: {', '.join(missing)}）"

    return {
        "direction": direction,
        "total": total,
        "factors": factors,
        "reasons": reasons,
        "caution": caution,
        "news_counts": news_counts,
        "data_insufficient": data_insufficient,
    }
