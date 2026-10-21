# ASVS Requirement Finder

OWASP ASVS 5.0.0のセキュリティ要件を日本語で検索し、英語原文と要件IDを確認できるアプリケーションです。

## Current demo

- 日本語の質問からASVS要件を検索
- Level 1–3による対象要件の絞り込み
- コミュニティ邦訳ドラフトと正式英語原文を併記
- 要件ID、章、節、検索スコアを表示
- APIキーなしで動くローカル検索ベースライン
- 検索結果だけを根拠にOpenAI APIで回答し、根拠要件も示すAI回答画面
- 具体化済みの機能要件を確認し、根拠付きの追加セキュリティ要件を返すガイド付きセキュリティレビュー

データはOWASP ASVS 5.0.0に準拠し、日本語はコミュニティ邦訳ドラフト、英語は正式原文です。ライセンスはCC BY-SA 4.0です。画面の利用方法はアプリ内の「使い方」ページを参照してください。

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

- Frontend: Node.js 24 / Next.js / React
- Backend: Python 3.13 / FastAPI / uv

## Container development

Docker Desktopを起動し、プロジェクトルートで次を実行するとfrontendとbackendをまとめて起動できます。

```powershell
.\scripts\start-containers.ps1
```

このスクリプトは `docker compose up --build` を実行します。PyCharmでは `scripts/start-containers.ps1` を右クリックし、`Run 'start-containers.ps1'` を選択できます。バックグラウンドで起動する場合は次を実行します。

```powershell
.\scripts\start-containers.ps1 -Detach
```

起動後のログは、プロジェクトルートで次のコマンドを実行して確認できます。直近100行を表示し、その後のログをリアルタイムで追跡します。

```powershell
# frontend・backend両方のログ
docker compose logs -f --tail 100

# backendだけのログ
docker compose logs -f --tail 100 backend

# frontendだけのログ
docker compose logs -f --tail 100 frontend
```

ログ表示は `Ctrl+C` で終了できます。このログ確認コマンドを終了してもコンテナは停止しません。`-Detach` なしで起動した場合は、起動したターミナル（PyCharmではRun画面）にもログが表示されます。

backendはstructlogでJSON形式のaccess logを出力し、全HTTP応答へ`X-Request-ID`を付与します。共通processorが時刻、`log_level`、logger名、request IDを付与します。このIDで、HTTP要求とAzure検索の`rag_search`、回答生成の`rag_generation`ログを関連付けられます。Azure検索では各段階の成否・所要時間・検索結果の要件ID、回答生成では成否・所要時間・根拠件数と要件IDを記録します。入力本文、検索query、要件本文、生成回答、認証情報、ベクトル、SDK例外本文は記録しません。CSV検索と文書登録batchは`rag_search`ログの対象外です。

- Frontend: `http://127.0.0.1:3000`
- Backend: `http://127.0.0.1:8000`
- OpenAPI: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

ソースコードはread-onlyでコンテナへbind mountされます。frontendはNext.jsの開発サーバー、backendはUvicornのreload modeで変更を検知します。依存ファイルまたはDockerfileを変更した場合は、`docker compose up --build` でイメージを再ビルドしてください。

停止とコンテナ内テストは次のコマンドで実行します。

```powershell
docker compose down
docker compose run --rm frontend npm test
docker compose run --rm -e ASVS_SEARCH_BACKEND=csv backend python -m unittest discover -s tests -v
```

ホスト側のポートを変更する場合は `.env.example` を `.env` へコピーし、`FRONTEND_PORT` と `BACKEND_PORT` を変更します。

既定はCSV検索のため、**APIキーなしで「要件検索」が動きます**。「AI回答」と「ガイド付きセキュリティレビュー」を試す場合は、`.env` に各自の `OPENAI_API_KEY` と `OPENAI_CHAT_MODEL`（例: `gpt-4o-mini`）を設定してください（生成分のOpenAI利用料は各自負担）。Azure AI Searchによるベクトル検索版はホスト側のAzure設定が必要で、フル機能はライブデモで確認できます。

## Frontend

Next.js App RouterとReactによる画面です。「要件検索」「AI回答」「ガイド付きセキュリティレビュー」をタブで切り替えます。AI回答では、検索されたASVS要件だけを根拠にした生成文と、モデルへ渡された根拠要件を表示します。Next.jsのRoute HandlerがFastAPIの検索・AI回答APIへsame-originで中継し、接続先はサーバー側の `BACKEND_URL` で指定します。

```powershell
cd frontend
npm ci
$env:BACKEND_URL="http://127.0.0.1:8000"
npm run dev
```

`http://127.0.0.1:3000` を開いて確認します。

```powershell
npm run lint
npm test
npm run build
```

本番モードは `npm run build` 後に `npm start` で起動します。`BACKEND_URL` は起動時にも設定してください。

## Backend

ファイル名は役割を表す接尾辞で統一しています。検索処理は`asvs_router.py` → `search_requirements_use_case.py` → 各`*_repository.py`の順に追えます。接続の組み立ては`api_dependencies.py`、入出力の型は`asvs_schema.py`です。

Clean Architecture Liteを採用し、domain、application、infrastructure、presentationの依存方向を分離しています。ASVS英語版・日本語版CSVを要件IDで結合し、`POST /api/v1/requirements/search` で検索します。`POST /api/v1/requirements/answer`は検索結果をOpenAI APIへ渡し、回答と実際の根拠を返します。

```powershell
cd backend
uv sync --locked
uv run uvicorn app.main:app --reload
```

uvが未導入の場合は、Windowsでは`winget install --id=astral-sh.uv -e`でインストールできます。`uv sync`はPython 3.13の`backend/.venv/`を作成し、`uv.lock`に固定した本番・開発依存を同期します。

バックエンドの環境設定は`backend/app/settings/`のPydantic Settingsで用途別に型検証します。コンテナ起動ではプロジェクトルートの`.env`をDocker Composeが読み、許可した値をコンテナ環境変数として渡します。Pythonアプリケーションは`.env`を直接読み込みません。CSV検索、Azure検索、OpenAI回答生成は必要な設定クラスだけを生成するため、未使用機能の認証情報は要求しません。

- API: `http://127.0.0.1:8000/`
- OpenAPI: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

フォーマット、lint、型検査、テストは次のコマンドで実行します。CIではRuffによる
自動変更を行わず、フォーマット済みかどうかを検証します。

```powershell
uv run --locked ruff format --check app scripts tests
uv run --locked ruff check app scripts tests
uv run --locked mypy app scripts tests
uv run python -m unittest discover -s tests -v
```

ローカルでRuffの安全な自動修正とフォーマットを適用する場合は、次を実行します。

```powershell
uv run ruff check --fix app scripts tests
uv run ruff format app scripts tests
```

### ASVS文書のIndex登録batch

`backend/scripts/index_asvs_documents.py`は、英語・日本語CSVの対応と345件の件数を検証し、1要件を1 chunkへ変換します。通常実行はAzureを呼ばないdry-runです。

```powershell
uv run --directory .\backend python .\scripts\index_asvs_documents.py
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
uv run python -m uvicorn app.main:app --reload
```

認証ユーザーにはSearch側の`Search Index Data Reader`、Foundry側の`Cognitive Services OpenAI User`が必要です。登録時と同じEmbedding Deployment（1536次元）を指定してください。`.env`はアプリから自動読み込みされません。また、ホストのAzure CLI認証はDockerコンテナへ自動共有されないため、この手順はホスト起動用です。

`/docs`から既存の`POST /api/v1/requirements/search`を実行できます。検索ごとにEmbedding APIを呼ぶため利用料金が発生します。Azureの認証・通信障害や不正な検索結果は503を返し、CSVへ自動で切り替えません。CSVへ戻す場合は`ASVS_SEARCH_BACKEND=csv`としてプロセスを再起動します。設定はプロセス内でキャッシュするため、その他の接続設定変更後も再起動してください。

ベクトル検索では要件IDの完全一致を優先する保証はありません。検索スコアは同じ検索応答内の比較に使い、CSV検索のスコアと比較しません。hybrid検索は未実装です。

### OpenAI APIによる根拠付き回答

回答生成にはOpenAI PlatformのAPIキーと、Chat Completionsに対応するモデルIDが必要です。ホスト起動では次を指定します。

```powershell
$env:OPENAI_API_KEY="<openai-project-api-key>"
$env:OPENAI_CHAT_MODEL="<openai-model-id>"
$env:OPENAI_CHAT_TIMEOUT_SECONDS="30"
$env:OPENAI_CHAT_MAX_COMPLETION_TOKENS="800"
```

回答生成のOpenAI APIキーは、Azure検索用のEntra ID認証とは独立しています。`ASVS_SEARCH_BACKEND=csv`でも回答生成は利用できますが、生成段階ではOpenAI APIへの通信と料金が発生します。`.env`からDocker Composeを起動する場合はこれらの値がコンテナへ渡されます。ホストで直接起動する場合、Pythonアプリケーションは`.env`を自動読み込みしないため、シェル環境変数として設定してください。APIキーはソースコード、ログ、公開文書へ記録しないでください。

`/docs`から`POST /api/v1/requirements/answer`を実行できます。質問と検索で取得した日本語・英語のASVS本文がOpenAI APIへ送られます。生成失敗は内部情報を含まない503となり、検索結果が0件なら生成APIを呼ばずに根拠不足を返します。

## Azure infrastructure

Azure AI Search、Microsoft Foundry、および`text-embedding-3-small`のモデルDeploymentはBicepで管理します。Azure AI SearchのIndex schemaは、Git管理するJSONをインフラ用Python CLIからデータプレーンへ反映します。サブスクリプションと既存リソースグループをコマンド引数で指定するため、テンプレートには個人のAzure識別子を含めません。検証とデプロイ手順は [infra runbook](infra/README.md) を参照してください。

## Git

Gitリポジトリはルートの1つだけを使用し、`frontend/` と `backend/` では初期化しません。
