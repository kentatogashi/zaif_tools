# zaif_tools

## GeoIP Explorer

IP アドレスから位置情報を引くだけでなく、**ブラウザでそのまま使える Web アプリ**として公開できる `GeoIP Explorer` に改善しました。

### このアプリの独自性

一般的な GeoIP API は「国や都市を返して終わり」になりがちですが、このアプリは公開向けに次の差別化ポイントを持たせています。

- **Web アプリ UI 付き**: `/` を開くと検索フォーム付きのランディングページを表示します。
- **`insights` を自動生成**: 国旗絵文字、IP 種別、現地時刻、地図リンクを API 側で追加します。
- **PaaS 公開しやすい**: `PORT` 環境変数に対応しているため、Render / Railway などでそのまま動かしやすいです。
- **JSON API と画面の両立**: `/geoip?ip=...` と `/geoip/<ip>` は API 用、`/` は人間向け UI、`/health` はヘルスチェック用です。

### 追加でおすすめの独自機能案

さらに独自性を高めるなら、次の方向性がおすすめです。

1. **脅威インサイト表示**
   - VPN / Tor / Proxy / Hosting の推定
   - ログイン監視や不正アクセス検知向けに活用しやすい
2. **組織向けネットワーク要約**
   - ASN から「クラウド事業者 / ISP / モバイル回線」などのラベル付け
   - B2B SaaS の管理画面で使いやすい
3. **アクセス分析ダッシュボード**
   - 最近引いた IP を一覧表示
   - 国別件数、地図表示、簡易ヒートマップ
4. **日本向け UX 強化**
   - 県名の日本語変換、国内回線向けの見やすい表示
   - 海外 IP を検知したときのアラート用 UI
5. **Webhook / Slack 連携**
   - 特定条件の IP を引いたら通知
   - 既存の `alert_notify.py` と連動しやすい

### セットアップ

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 起動方法

```bash
python app.py
```

Render / Railway などでは `PORT` が自動付与されるため、そのままデプロイしやすい構成です。

### Docker で公開する場合

#### イメージをビルド

```bash
docker build -t geoip-explorer .
```

#### コンテナを起動

```bash
docker run --rm -p 8000:8000 -e PORT=8000 geoip-explorer
```

起動後の確認例:

```bash
curl http://127.0.0.1:8000/health
curl "http://127.0.0.1:8000/geoip?ip=8.8.8.8"
```

#### 公開時の考え方

- ローカルでは `-p 8000:8000` で十分です。
- PaaS やコンテナ基盤では、プラットフォームから渡される `PORT` をそのまま利用できます。
- Dockerfile は依存関係として `PyYAML` をインストールしてから起動します。

### GitHub Actions で Render にデプロイする場合

1. Render で Web Service を作成し、デプロイ方法は **Deploy Hook** を使える状態にします。
2. Render の **Deploy Hook URL** を取得します。
3. GitHub リポジトリの **Settings > Secrets and variables > Actions** で、`RENDER_DEPLOY_HOOK_URL` という secret 名で登録します。
4. このリポジトリには `.github/workflows/render-deploy.yml` を追加してあるので、`main` ブランチへ push するか、GitHub Actions の `workflow_dispatch` で手動実行すると Render へデプロイをトリガーできます。

ワークフローの概要:

- トリガー: `main` への push / 手動実行
- 必要 secret: `RENDER_DEPLOY_HOOK_URL`
- 実行内容: `curl --request POST "$RENDER_DEPLOY_HOOK_URL"`

Render 側の推奨設定:

- Runtime: Docker
- Health Check Path: `/health`
- Port: Render が渡す `PORT` をそのまま利用

### 画面と API

- Web UI: `http://127.0.0.1:8000/`
- Health check: `http://127.0.0.1:8000/health`
- API: `http://127.0.0.1:8000/geoip?ip=8.8.8.8`
- API: `http://127.0.0.1:8000/geoip/8.8.8.8`

### 返却例

```json
{
  "ip": "8.8.8.8",
  "continent": "North America",
  "continent_code": "NA",
  "country": "United States",
  "country_code": "US",
  "region": "California",
  "city": "Mountain View",
  "latitude": 37.386,
  "longitude": -122.0838,
  "timezone": "America/Los_Angeles",
  "utc_offset": "-08:00",
  "postal_code": "94035",
  "connection": {
    "asn": 15169,
    "organization": "Google LLC",
    "isp": "Google LLC"
  },
  "insights": {
    "ip_type": "public",
    "country_flag": "🇺🇸",
    "local_time": "2026-03-22T12:34:56-07:00",
    "queried_at_utc": "2026-03-22T19:34:56+00:00",
    "map_links": {
      "google_maps": "https://www.google.com/maps?q=37.386,-122.0838",
      "openstreetmap": "https://www.openstreetmap.org/?mlat=37.386&mlon=-122.0838#map=10/37.386/-122.0838"
    }
  }
}
```

### 公開方法

- Render / Railway / Fly.io などの PaaS に `python app.py` を起動コマンドとして設定します。
- ヘルスチェック先は `/health` を指定できます。
- ルート `/` はデモ画面として使えるため、営業・検証・紹介ページとしても流用できます。
- GeoIP データは `ipwho.is` から取得しています。
