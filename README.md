# gold-news

自分用の GOLD（XAU）朝イチまとめページ。  
取得は無料（Yahoo + RSS + 経済カレンダー）。**ニュースの日本語要約は Cursor Cloud Automation（Pro）**。

## できること

- 金 / DXY / 米10年の前日比を取得
- RSS から金関連ニュースを抽出
- 経済カレンダー自動取得（USD High 中心）
- ルールベースの簡易バイアス
- ニュース欄の **AI日本語要約**（Cloud が `brief.json` を埋めて再描画）
- `out/index.html` に1ページ出力

## セットアップ

```powershell
cd c:\Users\hband\Cursor\GoldenNews
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## ローカル生成（取得のみ・要約は空）

```powershell
.\.venv\Scripts\python.exe -m src.main
```

`out/brief.json` と `out/index.html` ができます。ニュースは「AI要約待ち」表示になります。

## AI要約の反映（Cloud または手動）

1. `out/brief.json` の各 `news[].ai_summary_ja` に日本語要約を入れる  
2. 再描画:

```powershell
.\.venv\Scripts\python.exe -m src.render_brief
```

Cloud の手順・Automation 用プロンプトは **[CLOUD_AUTOMATION.md](CLOUD_AUTOMATION.md)** を参照。

## カレンダー

- 自動: Fair Economy の Forex Factory 週次 XML（キー不要）
- 手追加: `calendar.json` の `manual_events`

強制再取得:

```powershell
.\.venv\Scripts\python.exe -m src.main --refresh-calendar
```

## メンテ

- `config.yaml` … 閾値・RSS・カレンダー
- `CLOUD_AUTOMATION.md` … Cloud 毎朝ジョブの指示文

## 注意

個人用メモです。投資助言ではありません。無料ソースは遅延・欠損があり得ます。Cloud 要約は Pro のクラウドエージェント枠を消費します。
