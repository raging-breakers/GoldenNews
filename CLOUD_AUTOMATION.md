# Cursor Cloud Automation — GoldenNews (AI summaries + Slack)

This file is the runbook for a **Cursor Cloud Automation** (Pro).  
Data fetch stays free (Yahoo + RSS + economic calendar XML).  
**AI summarization + Slack notify** use the Cloud Agent.

## Goal

Every morning:

1. Collect markets / calendar / news with the free pipeline.
2. Write Japanese AI summaries into each news item.
3. Refresh `out/index.html`.
4. Post a short digest to Slack **`#golden-news`**.

## Slack setup (do once in Slack + Cursor UI)

1. In Slack, create a **private** channel named **`golden-news`** (shows as `#golden-news`). Add only yourself.
2. Connect Slack to Cursor: [Automations](https://cursor.com/automations) or [Cloud Agents dashboard](https://cursor.com/dashboard?tab=cloud-agents) → Slack.
3. Invite / allow the Cursor bot into `#golden-news` if Slack asks (otherwise Send to Slack may fail).
4. Edit your Automation:
   - **Repository:** `raging-breakers/GoldenNews` / `main`
   - **Tools:** enable **Send to Slack** → destination **`#golden-news`**
   - **Prompt:** replace with the block below
   - Save & keep Enabled
5. Optional: **Run now** once and confirm a message appears in `#golden-news`.

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
6. Confirm out/index.html shows Japanese AI summaries under ニュース（AI要約）.
7. Commit out/brief.json and out/index.html (and archive HTML if present) with message:
   "chore: morning brief with AI news summaries"
8. Push to the default branch (main) if a remote is configured. Prefer direct push to main; use a PR only if push is blocked.
9. Send a Slack message to channel #golden-news with:
   - Title line: GoldenNews | {date JST}
   - Bias: direction + one-line reason (from brief.json bias)
   - Up to 3 short Japanese news bullets (from ai_summary_ja; truncate to ~80 chars each if long)
   - Link: https://github.com/raging-breakers/GoldenNews/blob/main/out/index.html
   - Footer: 個人用メモ。投資助言ではありません。
   Keep the Slack message concise (under ~1500 characters).

If news is empty, still leave a valid brief, note that in Slack, and include the GitHub link.
Do not add paid API keys. Do not change scoring thresholds unless broken.
```

## Suggested Automation settings

| Field | Value |
|-------|--------|
| Name | GoldenNews morning brief |
| Trigger | Daily schedule (e.g. 06:30 JST — confirm cron timezone in editor) |
| Repository | [raging-breakers/GoldenNews](https://github.com/raging-breakers/GoldenNews) on `main` |
| Tools | Default cloud tools + **Send to Slack** → `#golden-news` |
| Model | A capable Pro-included model you prefer |

## Prerequisites

1. ~~Initial git commit~~ done
2. ~~Push to GitHub~~ done: https://github.com/raging-breakers/GoldenNews
3. Automation at https://cursor.com/automations
4. Cloud Agents can access this GitHub repo
5. Slack channel `#golden-news` + Send to Slack tool configured

## Local check (without Cloud)

```powershell
.\.venv\Scripts\python.exe -m src.main
# Manually edit out/brief.json → fill ai_summary_ja
.\.venv\Scripts\python.exe -m src.render_brief
```
