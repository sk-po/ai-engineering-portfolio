# ASVS document indexing batch

## Azure RAG retrieval evaluation

`evaluate_rag_retrieval.py`は公開HTTP APIを経由せず、同じAzure検索ユースケースを内部で実行して評価JSONLの検索順位と指標を出力します。生成回答は呼びません。Composeで起動したbackendコンテナでは、`.env`から注入済みのAzure接続設定をそのまま利用します。

```powershell
$env:ASVS_SEARCH_BACKEND = 'azure'
uv run --directory .\backend python .\backend\scripts\evaluate_rag_retrieval.py --concurrency 3
```

Composeを使う場合は、`.env`で`ASVS_SEARCH_BACKEND=azure`とAzure接続・認証値を設定して`docker compose up -d --build`を実行した後、次を実行します。

```powershell
docker compose exec backend python scripts/evaluate_rag_retrieval.py --concurrency 3
```

Composeでは評価ケースを`./docs/public:/docs/public:ro`としてread-only mountする。実行ごとに`backend/test-results/rag-retrieval-evaluation-*.json`へ履歴を保存します。`./backend/test-results:/app/test-results`のvolume mountにより、コンテナを作り直してもホスト側の履歴を保持できます。`--concurrency`は同時にAzure AI Searchへ送る検索数であり、レート制限時は小さくしてください。

## Azure RAGAS answer evaluation

`evaluate_ragas.py`は、Azure AI Searchで取得した根拠を使って既存の回答生成ユースケースを実行し、その実回答をRAGASで評価します。公開HTTP APIは経由しません。同じRAG実行の検索結果から`Recall@k`、`Precision@k`、`HitRate@k`、`MRR@k`、`nDCG@k`も計算し、`Faithfulness`、`AnswerRelevancy`、`ContextPrecision`、`ContextRecall`とともに、ケースごととマクロ平均で出力します。

`ContextPrecision`と`ContextRecall`の参照回答は、各ケースの`expected_requirement_ids`から固定したASVS 5.0.0原文を組み立てます。生成回答を参照回答として再利用しないため、評価対象の回答で自己採点しません。

RAG回答の生成、RAGASのLLM判定、AnswerRelevancy用Embeddingで外部APIを呼ぶため料金が発生します。最初は1件で通信とコストを確認してください。RAGAS 0.3.1と互換性を固定した開発用依存を使うため、Docker imageは一度rebuildします。

```powershell
docker compose up -d --build
docker compose exec backend python scripts/evaluate_ragas.py --case-id ST-RAG-FILE-L1
```

全件を評価する場合は次を実行します。`--concurrency`はRAG回答生成の同時数であり、RAGAS判定自体は全回答の生成後に実行します。Azure/OpenAIのレート制限がある場合は`1`のままにしてください。

```powershell
docker compose exec backend python scripts/evaluate_ragas.py --concurrency 1
```

RAGASの内部評価は、既定で1並列・retryなし・1要求120秒timeoutです。これはRAGAS標準の16並列・最大10回retryによるレート制限と長時間待機を避けるためです。応答が長いEvaluatorモデルだけ、次のようにtimeoutを延長できます。

```powershell
docker compose exec backend python scripts/evaluate_ragas.py `
  --case-id ST-RAG-FILE-L1 `
  --evaluator-timeout-seconds 180 `
  --ragas-concurrency 1
```

判定用モデルを回答生成モデルと分ける場合だけ、Composeの`.env`に`RAGAS_EVALUATOR_MODEL`を設定するか、次のように指定します。未指定時は既存の`OPENAI_CHAT_MODEL`を使用します。

```powershell
docker compose exec backend python scripts/evaluate_ragas.py `
  --evaluator-model <openai-model-id> `
  --evaluator-embedding-model text-embedding-3-small
```

出力はホストの`backend/test-results/ragas-evaluation-*.json`です。履歴JSONにはケースID、正解／検索要件ID、検索5指標、生成4指標、timeout・並列数を含む実行条件だけを保存し、質問、生成回答、要件本文、APIキーは保存しません。実行条件には再現性メタデータとして`code_sha`（実行時のコミット）、`code_dirty`（未コミット変更の有無）、`dataset_fingerprint`（評価ケースJSONLのSHA-256先頭12桁）をベストエフォートで記録します。gitが無いコンテナ実行では`code_sha`/`code_dirty`はnullになります。`macro_average.retrieval`と`macro_average.generation`を分けるため、検索品質と回答品質を同じ実行条件で比較できます。`--case-id`は複数回指定でき、`--max-cases 3`は全件実行前の小規模確認に使えます。

このbatchは、固定したOWASP ASVS 5.0.0の英語・日本語CSVから345個のchunkを作成し、`text-embedding-3-small`で1536次元のEmbeddingを生成して、Azure AI Searchの`security-docs-v1`へ登録します。FastAPIの起動やHTTP requestからは実行しません。

## Prerequisites

- [infra runbook](../../infra/README.md)に従い、BicepとIndex schemaの登録が完了していること
- uvをインストールし、`backend/uv.lock`から依存を同期できること
- `az login`済みで、Bicep実行時に指定したユーザーへ次のロールが反映されていること
  - Foundry account: `Cognitive Services OpenAI User`
  - Azure AI Search: `Search Index Data Contributor`

## 1. Dry-run

リポジトリルートから実行します。CSVの対応、345件の件数、chunk IDの重複を検証します。Azure接続、Embedding生成、Document更新は行いません。

```powershell
uv run --directory .\backend python .\scripts\index_asvs_documents.py
```

成功時は`Dry run succeeded: 345 documents prepared`と表示されます。

## 2. Environment variables

`<resource-group-name>`をBicepを実行したリソースグループへ置き換えます。値はBicep deploymentのoutputから取得するため、リソース名をソースコードへ固定しません。

```powershell
$resourceGroupName = '<resource-group-name>'
$deploymentName = 'asvs-rag-dev'

$foundryAccountName = az deployment group show `
  --resource-group $resourceGroupName `
  --name $deploymentName `
  --query 'properties.outputs.foundryAccountName.value' `
  --output tsv

$env:AZURE_OPENAI_BASE_URL = "https://$foundryAccountName.openai.azure.com/openai/v1/"
$env:AZURE_OPENAI_EMBEDDING_DEPLOYMENT = 'text-embedding-3-small'
$env:AZURE_SEARCH_ENDPOINT = az deployment group show `
  --resource-group $resourceGroupName `
  --name $deploymentName `
  --query 'properties.outputs.searchEndpoint.value' `
  --output tsv
$env:AZURE_SEARCH_INDEX_NAME = 'security-docs-v1'
```

APIキーは使用しません。`DefaultAzureCredential`がローカルではAzure CLIのログイン情報を、Azure上ではManaged Identityを利用できます。

## 3. One-document smoke test

`--execute`を付けると、Embedding APIのToken料金が発生し、Search Indexを更新します。最初は1件だけで認証・次元数・schemaの整合を確認します。

```powershell
uv run --directory .\backend python `
  .\scripts\index_asvs_documents.py `
  --execute `
  --limit 1
```

同じ`chunk_id`へ`merge_or_upload`するため、このコマンドを再実行しても重複Documentは作られません。

## 4. Full indexing

1件の登録をAzure PortalのSearch explorerで確認後、全345件を登録します。

```powershell
uv run --directory .\backend python `
  .\scripts\index_asvs_documents.py `
  --execute
```

既定では、疎通確認で成功している16件ずつEmbedding生成とDocument登録を行います。処理中は完了したbatchとDocument件数を表示します。429が返った場合はAzureの`Retry-After`、ヘッダーがない場合は60秒に5秒の余裕を加えて待機し、最大10回再試行します。OpenAI SDK側の自動retryは無効化し、短時間にretryが重なることを防ぎます。

## Processing contract

- Chunk単位: 1 ASVS requirement = 1 chunk
- `chunk_id`: `asvs-5-0-0-v1-1-1`形式。Azure AI SearchのDocument keyで利用できない`.`を`-`へ変換
- Embedding入力: 要件ID、日英の章・節、Level、日英の要件本文をラベル付きで結合
- Vector: `text-embedding-3-small` / 1536次元
- Write action: `merge_or_upload`による冪等なupsert
- Source guard: 英語・日本語CSVのID一致と全345件を、`--limit`適用前に検証

モデルまたは次元数を変える場合は、先にIndex schemaの`content_vector.dimensions`とbatchの`vector_dimensions`を同時に変更し、全Documentを再Embeddingします。
