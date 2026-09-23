"""Render a single-page morning brief HTML."""

from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from typing import Any


def _esc(v: Any) -> str:
    # Unescape first so leftover entities like &nbsp; become real spaces,
    # then escape for safe HTML (avoids showing "&nbsp;" as literal text).
    text = html.unescape("" if v is None else str(v)).replace("\xa0", " ")
    return html.escape(text, quote=True)


def _fmt_num(v: float | None, digits: int = 2) -> str:
    if v is None:
        return "—"
    return f"{v:,.{digits}f}"


def _fmt_pct(v: float | None) -> str:
    if v is None:
        return "—"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.2f}%"


def _factor_label(v: int | None) -> str:
    if v is None:
        return "欠損"
    if v > 0:
        return "+1"
    if v < 0:
        return "−1"
    return "0"


def render_html(
    *,
    title: str,
    disclaimer: str,
    generated_at: datetime,
    markets: dict[str, dict[str, Any]],
    calendar_view: dict[str, list[dict[str, Any]]],
    news: list[dict[str, Any]],
    bias: dict[str, Any],
) -> str:
    gold = markets.get("gold", {})
    dxy = markets.get("dxy", {})
    us10y = markets.get("us10y", {})
    factors = bias.get("factors") or {}

    def market_row(label: str, m: dict[str, Any], is_yield: bool = False) -> str:
        last = _fmt_num(m.get("last"), 3 if is_yield else 2)
        chg = _fmt_pct(m.get("change_pct")) if not is_yield else (
            "—" if m.get("change") is None else f"{m['change']:+.3f}"
        )
        status = "ok" if m.get("ok") else "err"
        err = f' <span class="err">({_esc(m.get("error"))})</span>' if m.get("error") else ""
        return (
            f'<tr class="{status}"><td>{_esc(label)}</td><td>{last}</td>'
            f"<td>{chg}</td><td>{'取得OK' if m.get('ok') else '失敗'}{err}</td></tr>"
        )

    today_ev = calendar_view.get("today") or []
    week_ev = calendar_view.get("week") or []

    def ev_li(e: dict[str, Any]) -> str:
        t = e.get("time_jst") or ""
        name = e.get("name", "")
        note = e.get("note") or ""
        return f"<li><strong>{_esc(t)} {_esc(name)}</strong> — {_esc(note)}</li>"

    news_html = ""
    if news:
        parts = []
        for n in news:
            link = _esc(n.get("link") or "#")
            title_n = _esc(n.get("title") or "")
            source = _esc(n.get("source") or "")
            ai = (n.get("ai_summary_ja") or "").strip()
            rss = (n.get("summary") or "").strip()
            if ai:
                body = f'<div class="ai">{_esc(ai)}</div>'
                if rss:
                    body += f'<div class="sum muted">{_esc(rss)}</div>'
            elif rss:
                body = (
                    f'<div class="ai pending">AI要約待ち（Cursor Cloud）</div>'
                    f'<div class="sum">{_esc(rss)}</div>'
                )
            else:
                body = '<div class="ai pending">AI要約待ち（Cursor Cloud）</div>'
            parts.append(
                f'<li><a href="{link}" target="_blank" rel="noopener">{title_n}</a>'
                f' <span class="src">{source}</span>{body}</li>'
            )
        news_html = "<ol>" + "".join(parts) + "</ol>"
    else:
        news_html = "<p class=\"muted\">直近の金関連ニュースを取得できませんでした。</p>"

    direction = bias.get("direction", "中立")
    dir_class = {
        "強気寄り": "bull",
        "弱気寄り": "bear",
        "中立": "neutral",
    }.get(direction, "neutral")

    reasons = "、".join(bias.get("reasons") or [])
    ts = generated_at.strftime("%Y-%m-%d %H:%M %Z")
    ai_done = sum(1 for n in news if (n.get("ai_summary_ja") or "").strip())
    ai_meta = f" · AI要約 {ai_done}/{len(news)}" if news else ""

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_esc(title)} — {generated_at.strftime("%Y-%m-%d")}</title>
  <style>
    :root {{
      --bg: #f3efe6;
      --ink: #1c1914;
      --muted: #6b6358;
      --line: #d4cbb8;
      --card: #fffdf8;
      --bull: #1f6b4a;
      --bear: #8b2e2e;
      --neutral: #5c5346;
      --accent: #b08d3c;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Hiragino Sans", "Noto Sans JP", sans-serif;
      background:
        radial-gradient(ellipse at top left, #efe6d4 0%, transparent 50%),
        linear-gradient(180deg, #f7f2e8 0%, var(--bg) 100%);
      color: var(--ink);
      line-height: 1.55;
    }}
    main {{
      max-width: 720px;
      margin: 0 auto;
      padding: 2rem 1.25rem 3rem;
    }}
    header h1 {{
      font-size: 1.75rem;
      letter-spacing: 0.02em;
      margin: 0 0 0.35rem;
      font-weight: 700;
    }}
    .meta {{ color: var(--muted); font-size: 0.9rem; margin-bottom: 1.5rem; }}
    .disclaimer {{
      font-size: 0.85rem;
      color: var(--muted);
      border-left: 3px solid var(--accent);
      padding-left: 0.75rem;
      margin-bottom: 1.75rem;
    }}
    section {{
      margin-bottom: 1.75rem;
    }}
    h2 {{
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      margin: 0 0 0.65rem;
      font-weight: 600;
    }}
    .bias {{
      background: var(--card);
      border: 1px solid var(--line);
      padding: 1.1rem 1.2rem;
    }}
    .bias .dir {{
      font-size: 1.6rem;
      font-weight: 700;
      margin-bottom: 0.5rem;
    }}
    .bias .dir.bull {{ color: var(--bull); }}
    .bias .dir.bear {{ color: var(--bear); }}
    .bias .dir.neutral {{ color: var(--neutral); }}
    .bias p {{ margin: 0.35rem 0; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--card);
      border: 1px solid var(--line);
      font-size: 0.95rem;
    }}
    th, td {{
      text-align: left;
      padding: 0.55rem 0.7rem;
      border-bottom: 1px solid var(--line);
    }}
    th {{ color: var(--muted); font-weight: 600; font-size: 0.8rem; }}
    tr:last-child td {{ border-bottom: none; }}
    .err {{ color: var(--bear); font-size: 0.8rem; }}
    .muted {{ color: var(--muted); }}
    ul, ol {{ padding-left: 1.2rem; margin: 0; }}
    li {{ margin-bottom: 0.85rem; }}
    a {{ color: #2a4d6e; }}
    .src {{ color: var(--muted); font-size: 0.8rem; }}
    .ai {{
      margin-top: 0.35rem;
      font-size: 0.95rem;
      line-height: 1.5;
      color: var(--ink);
    }}
    .ai.pending {{
      color: var(--muted);
      font-style: italic;
      font-size: 0.85rem;
    }}
    .sum {{ color: var(--muted); font-size: 0.8rem; margin-top: 0.2rem; }}
    .factors {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 0.5rem;
      margin-top: 0.75rem;
    }}
    .factors div {{
      background: var(--card);
      border: 1px solid var(--line);
      padding: 0.5rem 0.6rem;
      font-size: 0.85rem;
      text-align: center;
    }}
    .factors span {{ display: block; color: var(--muted); font-size: 0.75rem; }}
    @media (max-width: 560px) {{
      .factors {{ grid-template-columns: repeat(2, 1fr); }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{_esc(title)}</h1>
      <div class="meta">生成: {_esc(ts)}{ai_meta}</div>
      <p class="disclaimer">{_esc(disclaimer)}</p>
    </header>

    <section class="bias">
      <h2>簡易バイアス</h2>
      <div class="dir {dir_class}">{_esc(direction)}</div>
      <p><strong>理由</strong> {_esc(reasons)}</p>
      <p><strong>注意</strong> {_esc(bias.get("caution", ""))}</p>
      <div class="factors">
        <div><span>金</span>{_factor_label(factors.get("gold"))}</div>
        <div><span>DXY</span>{_factor_label(factors.get("dxy"))}</div>
        <div><span>米10年</span>{_factor_label(factors.get("us10y"))}</div>
        <div><span>ニュース</span>{_factor_label(factors.get("news"))}</div>
      </div>
    </section>

    <section>
      <h2>価格・指標</h2>
      <table>
        <thead><tr><th>銘柄</th><th>直近</th><th>変化</th><th>状態</th></tr></thead>
        <tbody>
          {market_row("金 (GC=F)", gold)}
          {market_row("DXY", dxy)}
          {market_row("米10年 (^TNX)", us10y, is_yield=True)}
        </tbody>
      </table>
    </section>

    <section>
      <h2>今日のイベント</h2>
      {"<ul>" + "".join(ev_li(e) for e in today_ev) + "</ul>" if today_ev else '<p class="muted">本日の登録イベントなし</p>'}
      <h2 style="margin-top:1.2rem">今週の注目 (high)</h2>
      {"<ul>" + "".join(ev_li(e) for e in week_ev) + "</ul>" if week_ev else '<p class="muted">直近数日の high イベントは未登録、または来週フィードが未公開です</p>'}
    </section>

    <section>
      <h2>ニュース（AI要約）</h2>
      {news_html}
    </section>
  </main>
</body>
</html>
"""


def write_outputs(html: str, out_dir: Path, archive_dir: Path, day: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)
    index_path = out_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")
    (archive_dir / f"{day}.html").write_text(html, encoding="utf-8")
    return index_path
