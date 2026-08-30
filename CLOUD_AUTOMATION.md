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
3. **Invite the Cursor bot into `#golden-news`** (required for private channels):
   - Open `#golden-news` in Slack
   - In the message box, type: `/invite @Cursor` and press Enter
   - Or: channel name → **メンバーを追加** → **Cursor**（アプリ）を追加
4. Edit your Automation:
   - **Repository:** `raging-breakers/GoldenNews` / `main`
   - **Tools:** enable **Send to Slack** → destination **`#golden-news`**（プロンプトに書くだけでは不十分。ツールでチャンネルを明示選択）
   - **Prompt:** replace with the block below（先頭に Slack 必須の一文あり）
   - Save & keep Enabled
5. **Run now** once and confirm a message appears in `#golden-news`.

## Slack が届かないとき

| 確認 | 対処 |
|------|------|
| Automation は成功（`main` に commit がある） | ブリーフ生成はOK。Slack 設定を疑う |
| Tools に **Send to Slack** が ON か | ON にして `#golden-news` を**固定選択**して Save |
| private チャンネル | `/invite @Cursor` を `#golden-news` で実行 |
| Cursor と Slack が同じワークスペースか | Automations で Slack Connect を再確認 |
| Agent ログに `Send to Slack` があるか | 無い → プロンプト先頭の **MUST** 文を入れて再実行 |
| メッセージはあるが通知だけ来ない | Slack アプリで `#golden-news` を直接開く（通知設定の問題のことも） |

**Android 10 の端末:** Slack 公式アプリは非対応のことが多い。スマホブラウザで [slack.com](https://slack.com) から `#golden-news` を開く。

## Agent instructions (paste into Automation prompt)

```text
IMPORTANT: You MUST use the Send to Slack tool to post to #golden-news before finishing. Do not mark the run complete without a successful Slack post.

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
   - Note: 詳細ページはローカルで out/index.html を開く（git pull 後）。GitHub の blob URL は HTML ソース表示のみでページとしては見られない。
   - Optional link (source only): https://github.com/raging-breakers/GoldenNews/blob/main/out/index.html
   - Footer: 個人用メモ。投資助言ではありません。
   Keep the Slack message concise (under ~1500 characters). Put the useful content IN Slack; do not rely on the GitHub link as a rendered page.

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

## Viewing the brief (important)

GitHub **`/blob/.../index.html`** shows **HTML source code** (`<html>...`), not a rendered page. That is normal.

| How to view | Works as a page? |
|-------------|------------------|
| Local `out\index.html` in a browser | Yes (recommended) |
| GitHub blob URL | No (source only) |
| GitHub Pages | Yes (needs public repo on Free, or Pro for private) |
| Slack digest | Yes for summary text |
| Slack mobile app | Android 11+（Android 10 はブラウザ版 slack.com を利用） |

**After Cloud runs:** `git pull` then open:

```powershell
cd c:\Users\hband\Cursor\GoldenNews
git pull
start out\index.html
```

## Local check (without Cloud)

```powershell
.\.venv\Scripts\python.exe -m src.main
# Manually edit out/brief.json → fill ai_summary_ja
.\.venv\Scripts\python.exe -m src.render_brief
```
