# Cursor Cloud Automation — GOLD morning brief (AI news summaries)

This file is the runbook for a **Cursor Cloud Automation** (Pro).  
Data fetch stays free (Yahoo + RSS + economic calendar XML). **Only summarization** uses the Cloud Agent.

## Goal

Every morning:

1. Collect markets / calendar / news with the free pipeline.
2. Write Japanese AI summaries into each news item.
3. Refresh `out/index.html` so the ニュース欄 shows those summaries.

## Agent instructions (paste into Automation prompt)

```text
You are updating the gold-news morning brief in this repository.

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
6. Confirm out/index.html shows Japanese AI summaries under ニュース（AI要約）.
7. Commit out/brief.json and out/index.html (and archive HTML if present) with message:
   "chore: morning brief with AI news summaries"
8. Push to the default branch if a remote is configured.

If news is empty, still leave a valid brief and note that in the run summary.
Do not add paid API keys. Do not change scoring thresholds unless broken.
```

## Suggested Automation settings

| Field | Value |
|-------|--------|
| Name | GOLD morning brief + AI news |
| Trigger | Daily schedule (e.g. every day 06:30 JST — set cron in editor; confirm timezone) |
| Repository | This repo (`GoldenNews` / gold-news) on `main` |
| Tools | Default cloud tools; enable PR creation only if you want a PR instead of direct push |
| Model | A capable Pro-included model you prefer |

## Prerequisites

1. Initial git commit of the project.
2. Push to GitHub or Cursor-hosted remote (Cloud needs a cloneable repo).
3. Create the automation at https://cursor.com/automations (or Agents Window → Automations).

## Local check (without Cloud)

```powershell
.\.venv\Scripts\python.exe -m src.main
# Manually edit out/brief.json → fill ai_summary_ja
.\.venv\Scripts\python.exe -m src.render_brief
```
