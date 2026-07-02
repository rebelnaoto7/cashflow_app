# 💰 Cashflow Dashboard (Django 版)

月次資金繰り＋3ヶ月予測・シナリオ分析アプリ。
元の **Streamlit 版 (`app.py`)** を **Django** に移植したもの。
計算ロジック（pandas / numpy）と Excel 出力（openpyxl）は元のまま、UI を Django + Bootstrap 5 + Plotly.js に置き換えています。

---

## 🎯 できること（結論）
- 3ヶ月先までの資金ショートを予測
- 楽観 / 基準 / 悲観の3シナリオでリスク比較
- 予実差異を分析し改善アクションを特定
- 資金繰り表＋実績表を Excel 出力

---

## 🚀 セットアップ & 起動

```bash
# 1. 仮想環境（任意）
python -m venv .venv
# Windows
.\.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate

# 2. 依存パッケージ
pip install -r requirements.txt

# 3. 起動（DB を使わないため migrate は不要）
python manage.py runserver
# → http://127.0.0.1:8000/
```

> セッション保持にファイルベースのセッション (`django.contrib.sessions.backends.file`) を使用しているため、データベースは不要です。

---

## 🧱 アーキテクチャ（移植対応表）

| Streamlit 版 | Django 版 | 場所 |
|---|---|---|
| `st.session_state` | Django セッション | `views.py`（`SK_STATE` / `SK_ACTUAL`） |
| `st.sidebar` の入力群 | `AssumptionsForm` | `dashboard/forms.py` |
| `st.tabs`（5タブ） | 1ページ + Bootstrap nav-tabs | `templates/dashboard/index.html` |
| `compute_plan` 他の計算 | 同名関数（pandas/numpy） | `dashboard/services.py` |
| `st.data_editor`（実績編集） | 編集可能 HTML グリッド | `index.html` Tab3 |
| Plotly グラフ | Plotly.js（CDN）+ Python が dict 生成 | `views.py` `_build_figures` |
| `st.download_button`（Excel） | ダウンロード用ビュー | `views.py` `download_excel` |
| Styler の配色 | CSS クラス | `base.html` |

### ディレクトリ構成
```
cashflow_dashboard/
├── manage.py
├── requirements.txt
├── cashflow_project/        # プロジェクト設定
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py / asgi.py
└── dashboard/               # アプリ本体
    ├── constants.py         # 既定値・ラベル・リネームマップ
    ├── services.py          # 計算ロジック（フレームワーク非依存）
    ├── forms.py             # 前提条件フォーム
    ├── views.py             # 画面 + Excel ダウンロード
    ├── urls.py
    └── templates/dashboard/
        ├── base.html
        └── index.html
```

---

## ✨ 画面構成（5タブ）

1. **📊 ダッシュボード** … 主要KPI（当月末／3ヶ月後／期間中最低／営業CF合計）、現金残高推移、月次CF構成
2. **📋 月次資金繰り表** … 計画ベースの資金繰り表（カラー強調）
3. **📝 実績入力 & 予実差異** … 実績を編集 →「再計算」で予実差異を自動評価（○ / △ / ×）
4. **🎯 シナリオ分析** … 楽観／基準／悲観の比較と推奨アクション
5. **📥 ダウンロード** … Excel 出力

---

## ⚠️ 設計上の注意

- **状態保持**：Streamlit は再実行のたびに `session_state` を参照するが、Django ではフォーム送信（POST）のたびにセッションを更新して全タブを再計算する。値を変えたら **「🔄 再計算する」** を押す。
- **タイムゾーン**：既定は `Asia/Tokyo`。zoneinfo が無い環境では環境変数 `TIME_ZONE` で上書き可能（`settings.py`）。
- **本番デプロイ**：`SECRET_KEY` を環境変数化し、`DEBUG=False`、`ALLOWED_HOSTS` を適切に設定すること。静的ファイルは CDN 配信のため `collectstatic` は不要。

---

## 💡 補足
本ツールは経営判断の補助であり、実際の意思決定は専門家にご相談ください。
