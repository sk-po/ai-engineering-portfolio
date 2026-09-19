# FDE Portfolio

Forward Deployed Engineer（FDE）への転職を目的としたポートフォリオです。現在は、OWASP ASVS 5.0.0のセキュリティ要件を日本語で検索し、英語原文と要件IDを確認できるアプリケーションを実装しています。

## Current demo

- 日本語の質問からASVS要件を検索
- Level 1–3による対象要件の絞り込み
- コミュニティ邦訳ドラフトと正式英語原文を併記
- 要件ID、章、節、検索スコアを表示
- APIキーなしで動くローカル検索ベースライン

データの出典、翻訳ステータス、ライセンスは [OWASP ASVS data policy](docs/public/asvs-data.md)、HTTP契約は [Public API](docs/public/api.md) を参照してください。

## ディレクトリ構成

```text
.
├── frontend/                  # フロントエンド
├── backend/                   # FastAPIバックエンド
├── infra/                     # AzureリソースのBicepテンプレート
├── docs/                      # 成果物ドキュメント
├── scripts/                   # 開発支援スクリプト
├── .run/                      # PyCharm共有起動設定
├── .github/workflows/         # GitHub Actions
├── .gitignore
├── README.md
├── AGENTS.md                  # 生成AI向け共通作業ルール
└── CLAUDE.md                  # Claude CodeからAGENTS.mdを参照
```

## Runtime

- Frontend: Node.js 24
- Backend: Python 3.13 / FastAPI

## Container development

Docker Desktopを起動し、プロジェクトルートで次を実行するとfrontendとbackendをまとめて起動できます。

```powershell
.\scripts\start-containers.ps1
```

このスクリプトは `docker compose up --build` を実行します。PyCharmでは `scripts/start-containers.ps1` を右クリックし、`Run 'start-containers.ps1'` を選択できます。バックグラウンドで起動する場合は次を実行します。

```powershell
.\scripts\start-containers.ps1 -Detach
```

- Frontend: `http://127.0.0.1:3000`
- Backend: `http://127.0.0.1:8000`
- OpenAPI: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

ソースコードはread-onlyでコンテナへbind mountされます。frontendはNode.jsのwatch mode、backendはUvicornのreload modeで変更を検知します。依存ファイルまたはDockerfileを変更した場合は、`docker compose up --build` でイメージを再ビルドしてください。

停止とコンテナ内テストは次のコマンドで実行します。

```powershell
docker compose down
docker compose run --rm frontend npm test
docker compose run --rm backend python -m unittest discover -s tests -v
```

ホスト側のポートを変更する場合は `.env.example` を `.env` へコピーし、`FRONTEND_PORT` と `BACKEND_PORT` を変更します。コンテナ構成の判断は [Container Development](docs/public/container-development.md) を参照してください。

## Frontend

追加パッケージに依存しない、Node.js製の静的WebサーバーとASVS検索画面です。Node.js serverがバックエンドAPIをsame-originでproxyします。

```powershell
cd frontend
npm install
$env:BACKEND_URL="http://127.0.0.1:8000"
npm start
```

`http://127.0.0.1:3000` を開いて確認します。

```powershell
npm run lint
npm test
npm run build
```

## Backend

ファイル名は役割を表す接尾辞で統一しています。検索処理は`asvs_router.py` → `search_requirements_use_case.py` → 各`*_repository.py`の順に追えます。接続の組み立ては`api_dependencies.py`、入出力の型は`asvs_schema.py`です。命名規則の一覧は [File naming convention](docs/public/architecture/backend.md#file-naming-convention) を参照してください。

Clean Architecture Liteを採用し、domain、application、infrastructure、presentationの依存方向を分離しています。ASVS英語版・日本語版CSVを要件IDで結合し、`POST /api/v1/requirements/search` で検索します。詳細は [Backend Architecture](docs/public/architecture/backend.md) を参照してください。

```powershell
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

- API: `http://127.0.0.1:8000/`
- OpenAPI: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

テストは次のコマンドで実行します。

```powershell
python -m unittest discover -s tests -v
```

### ASVS文書のIndex登録batch

`backend/scripts/index_asvs_documents.py`は、英語・日本語CSVの対応と345件の件数を検証し、1要件を1 chunkへ変換します。通常実行はAzureを呼ばないdry-runです。

```powershell
.\backend\.venv\Scripts\python.exe .\backend\scripts\index_asvs_documents.py
```

Azureへ登録するときは、Microsoft Entra IDで認証します。詳細な環境変数の取得方法と、1件だけの疎通確認から全件登録へ進む手順は [document indexing runbook](backend/scripts/README.md) を参照してください。`--execute`を付けた実行だけがEmbedding APIを呼び、Azure AI Searchを更新します。

### Azure AI Searchによる検索

既定はCSV検索です。登録済みIndexをベクトル検索する場合は、ホスト側のPowerShellで以下を設定して起動します。接続先の取得方法は上記の登録batch手順と共通です。

```powershell
az login
$env:ASVS_SEARCH_BACKEND="azure"
$env:AZURE_SEARCH_ENDPOINT="https://<search-service-name>.search.windows.net"
$env:AZURE_SEARCH_INDEX_NAME="security-docs-v1"
$env:AZURE_OPENAI_BASE_URL="https://<foundry-account-name>.openai.azure.com/openai/v1/"
$env:AZURE_OPENAI_EMBEDDING_DEPLOYMENT="text-embedding-3-small"
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

認証ユーザーにはSearch側の`Search Index Data Reader`、Foundry側の`Cognitive Services OpenAI User`が必要です。登録時と同じEmbedding Deployment（1536次元）を指定してください。`.env`はアプリから自動読み込みされません。また、ホストのAzure CLI認証はDockerコンテナへ自動共有されないため、この手順はホスト起動用です。

`/docs`から既存の`POST /api/v1/requirements/search`を実行できます。検索ごとにEmbedding APIを呼ぶため利用料金が発生します。Azureの認証・通信障害や不正な検索結果は503を返し、CSVへ自動で切り替えません。CSVへ戻す場合は`ASVS_SEARCH_BACKEND=csv`としてプロセスを再起動します。設定はプロセス内でキャッシュするため、その他の接続設定変更後も再起動してください。

ベクトル検索では要件IDの完全一致を優先する保証はありません。検索スコアは同じ検索応答内の比較に使い、CSV検索のスコアと比較しません。hybrid検索は未実装です。

## Azure infrastructure

Azure AI Search、Microsoft Foundry、および`text-embedding-3-small`のモデルDeploymentはBicepで管理します。Azure AI SearchのIndex schemaは、Git管理するJSONをインフラ用Python CLIからデータプレーンへ反映します。サブスクリプションと既存リソースグループをコマンド引数で指定するため、テンプレートには個人のAzure識別子を含めません。設計判断は [Azure infrastructure](docs/public/azure-infrastructure.md)、検証とデプロイ手順は [infra runbook](infra/README.md) を参照してください。

## Git

Gitリポジトリはルートの1つだけを使用し、`frontend/` と `backend/` では初期化しません。
