# Cursor Cloud Automation — GoldenNews (AI summaries + GitHub Pages)

This file is the runbook for a **Cursor Cloud Automation** (Pro).  
Data fetch stays free (Yahoo + RSS + economic calendar XML).  
**AI summarization** uses the Cloud Agent. The brief is viewed on **GitHub Pages** (no Slack).

## Goal

Every morning:

1. Collect markets / calendar / news with the free pipeline.
2. Write Japanese AI summaries into each news item.
3. Refresh `out/index.html` and root `index.html` (for Pages).
4. Push to `main` so https://raging-breakers.github.io/GoldenNews/ updates.

## Agent instructions (paste into Automation prompt)

```text
You are updating the GoldenNews morning brief in this repository.

Steps (do in order):
1. Install deps if needed: python -m pip install -r requirements.txt
2. Run: python -m src.main
3. Open out/brief.json. For each object in "news", write "ai_summary_ja":
   - Japanese
   - About 200–350 characters
   - Neutral tone; facts only from title + summary (+ link text if needed)
   - Do NOT give investment advice or buy/sell recommendations
   - Keep the existing "id", "title", "link", "source", "summary"
4. Set "ai_summaries_ready" to true when all news items have ai_summary_ja.
5. Run: python -m src.render_brief
   (This writes out/index.html, archive/{date}.html, and root index.html for GitHub Pages.)
6. Confirm root index.html and out/index.html show Japanese AI summaries under ニュース（AI要約）.
7. Commit out/brief.json, out/index.html, index.html (and archive HTML if present) with message:
   "chore: morning brief with AI news summaries"
8. Push to the default branch (main) if a remote is configured. Prefer direct push to main; use a PR only if push is blocked.
9. Viewing is via GitHub Pages:
   https://raging-breakers.github.io/GoldenNews/

If news is empty, still leave a valid brief and push so Pages stays up to date.
Do not add paid API keys. Do not change scoring thresholds unless broken.
```

## Suggested Automation settings

| Field | Value |
|-------|--------|
| Name | GoldenNews morning brief |
| Trigger | Daily schedule (e.g. 06:30 JST — confirm cron timezone in editor) |
| Repository | [raging-breakers/GoldenNews](https://github.com/raging-breakers/GoldenNews) on `main` |
| Tools | Default cloud tools (**Send to Slack** OFF) |
| Model | A capable Pro-included model you prefer |

## Prerequisites

1. Public repo: https://github.com/raging-breakers/GoldenNews
2. GitHub Pages: Settings → Pages → Deploy from branch `main` / `/` (root)
3. Live URL: https://raging-breakers.github.io/GoldenNews/
4. Automation at https://cursor.com/automations
5. Cloud Agents can access this GitHub repo

## Viewing the brief

| How to view | Works as a page? |
|-------------|------------------|
| [GitHub Pages](https://raging-breakers.github.io/GoldenNews/) | Yes (recommended) |
| Local `index.html` or `out\index.html` in a browser | Yes |
| GitHub blob URL | No (source only) |

**After Cloud runs:** open the Pages URL (or `git pull` then open local HTML).

```powershell
cd c:\Users\hband\Cursor\GoldenNews
git pull
start index.html
```

## Local check (without Cloud)

```powershell
.\.venv\Scripts\python.exe -m src.main
# Manually edit out/brief.json → fill ai_summary_ja
.\.venv\Scripts\python.exe -m src.render_brief
```
