# Azure infrastructure

Azure AI Search、Microsoft Foundry、Embeddingモデルに加え、frontend/backendのホスティング基盤（Azure Container Apps）をBicepでデプロイします。テンプレートは既存のリソースグループを対象とし、リソースグループ自体は作成しません。

## Structure

```text
infra/
├── main.bicep                  # resource group scopeのcomposition root
├── environments/
│   └── dev.bicepparam         # 環境ごとの差分（秘密情報は置かない）
├── modules/
│   ├── ai-foundry.bicep
│   ├── ai-search.bicep
│   ├── observability.bicep              # Log Analytics + Application Insights
│   ├── container-registry.bicep         # ACR + AcrPull
│   ├── key-vault.bicep                  # Key Vault + Secrets User
│   ├── container-apps-environment.bicep # Container Apps Environment
│   └── container-app.bicep              # frontend/backendで再利用
├── search/
│   └── security-docs-v1.json  # version管理するIndex schema
├── scripts/
│   └── deploy_search_index.py # schemaをSearch data planeへ反映
└── tests/
    └── test_deploy_search_index.py
```

リソースを追加するときは個別モジュールを`modules/`へ追加し、`main.bicep`で組み合わせます。サブスクリプションID、リソースグループ名、ユーザー固有値はBicepへ固定しません。

## Quick start（Bicep実行コマンド）

以下はリポジトリルートから実行します。`<resource-group-name>`を既存のリソースグループ名へ置き換えてください。現在Azure CLIで選択しているサブスクリプションへ、Azure AI Search、Microsoft Foundry、および`text-embedding-3-small`をデプロイします。

まず、Azureに反映される差分を確認します。

```powershell
az deployment group what-if `
  --resource-group '<resource-group-name>' `
  --template-file .\infra\main.bicep `
  --parameters .\infra\environments\dev.bicepparam
```

差分に問題がなければデプロイします。

```powershell
az deployment group create `
  --name 'asvs-rag-dev' `
  --resource-group '<resource-group-name>' `
  --template-file .\infra\main.bicep `
  --parameters .\infra\environments\dev.bicepparam
```

使用するサブスクリプションを明示する場合は、両方のコマンドへ`--subscription '<subscription-id-or-name>'`を追加します。

## Prerequisites

- Azure CLIへサインイン済みであること
- 対象サブスクリプションに既存のリソースグループがあること
- `Microsoft.Search`と`Microsoft.CognitiveServices`リソースプロバイダーを利用できること
- FreeのAzure AI Searchは1サブスクリプションにつき1つまでであること
- Japan Eastで`text-embedding-3-small` version `1`の`GlobalStandard` deploymentを利用できること
- 対象SubscriptionにEmbedding deployment用のquotaとcapacityがあること

ローカル開発者へデータプレーンのRBACロールも割り当てる場合は、オブジェクトIDをローカル変数へ取得します。個人の識別子は`dev.bicepparam`へ保存しません。

```powershell
$developerObjectId = az ad signed-in-user show --query id -o tsv
```

ロール割り当てもデプロイするには、実行ユーザーに`Owner`または`Role Based Access Control Administrator`相当の権限が必要です。権限がない場合は空文字のままデプロイできます。

## Validate

```powershell
az bicep build --file .\infra\main.bicep --stdout | Out-Null
```

Azureへ変更を加えず、対象スコープでテンプレートを検証する場合は次を実行します。

```powershell
$subscriptionId = '<subscription-id>'
$resourceGroupName = '<resource-group-name>'

az deployment group validate `
  --subscription $subscriptionId `
  --resource-group $resourceGroupName `
  --template-file .\infra\main.bicep `
  --parameters .\infra\environments\dev.bicepparam `
  localDeveloperPrincipalId=$developerObjectId
```

差分を確認します。

```powershell
az deployment group what-if `
  --subscription $subscriptionId `
  --resource-group $resourceGroupName `
  --template-file .\infra\main.bicep `
  --parameters .\infra\environments\dev.bicepparam `
  localDeveloperPrincipalId=$developerObjectId
```

## Deploy

`what-if`の結果を確認してから、同じサブスクリプションとリソースグループへデプロイします。

```powershell
az deployment group create `
  --name 'asvs-rag-dev' `
  --subscription $subscriptionId `
  --resource-group $resourceGroupName `
  --template-file .\infra\main.bicep `
  --parameters .\infra\environments\dev.bicepparam `
  localDeveloperPrincipalId=$developerObjectId
```

同じスコープ、パラメーター、テンプレートで再実行した場合、Bicepは同じリソース名を解決して宣言状態へ収束させます。リソース名のサフィックスにはサブスクリプションIDとリソースグループIDから生成した決定的な値を使用しています。

## Deploy the Search index schema

Azure AI SearchのIndexはARM/Bicepリソースではないため、Bicep完了後にPythonスクリプトからSearch data-plane APIへ反映します。この処理はIndex schemaだけを作成または更新し、Embedding生成とDocument登録は行いません。

最初に、ローカル検証を実行します。Azureへの接続や変更は行いません。

```powershell
$searchServiceName = az deployment group show `
  --resource-group '<resource-group-name>' `
  --name 'asvs-rag-dev' `
  --query 'properties.outputs.searchServiceName.value' `
  --output tsv

uv run --directory .\backend python `
  ..\infra\scripts\deploy_search_index.py `
  --service-name $searchServiceName `
  --dry-run
```

検証後、同じschemaをAzureへ反映します。Azure CLIで`az login`済みであり、実行ユーザーに対象Searchサービスの`Search Service Contributor`ロールが必要です。

```powershell
uv run --directory .\backend python `
  ..\infra\scripts\deploy_search_index.py `
  --service-name $searchServiceName
```

特定のSubscriptionを利用する場合は、`--subscription '<subscription-id-or-name>'`を追加します。スクリプトはAzure CLIから`https://search.azure.com/.default` scopeのアクセストークンを取得するため、APIキーをファイルやコマンドラインへ渡しません。

現在のschemaは`security-docs-v1`を作成し、次のvector設定を使用します。

| 設定 | 値 |
| --- | --- |
| Vector field | `content_vector` / `Collection(Edm.Single)` |
| Dimensions | `1536` |
| Algorithm | `HNSW` |
| Metric | `cosine` |
| Profile | `vector-profile-default` |
| HNSW parameters | `m=4`, `efConstruction=400`, `efSearch=500` |

既存Indexへ適用できない破壊的なschema変更は、自動削除や再作成を行わずAzureのエラーとして停止します。その場合は`security-docs-v2`のような新しいschemaを追加し、Document投入と検索検証後にAliasを切り替えます。

dev環境では次のEmbedding deploymentを作成します。

| 設定 | 値 |
| --- | --- |
| Deployment name | `text-embedding-3-small` |
| Model | `text-embedding-3-small` |
| Model version | `1` |
| Deployment SKU | `GlobalStandard` |
| Capacity | `10`（TPM quota割り当て。固定料金ではない） |
| Output dimensions | `1536`（Index schemaとPythonのEmbedding要求で指定） |

`GlobalStandard`はpay-per-tokenであり、deploymentを作成しただけでは推論Token料金は発生しません。`embeddingDeploymentCapacity`は処理可能なTPM/RPM quotaの割り当てであり、Provisioned Throughputの予約購入ではありません。ただし、推論データはJapan East以外で処理される可能性があります。単一Region内の処理が必要になった場合は`embeddingDeploymentSkuName`を`Standard`へ変更し、対応するquotaとcapacityを確認します。

モデルversionは再現性のため明示し、`NoAutoUpgrade`で自動更新を無効化しています。version変更時は検索品質を評価し、登録済みDocumentをすべて再Embeddingします。`embeddingDeploymentCapacity`は課金予約ではなく、このStandard deploymentへ割り当てるrate-limit quotaです。

デプロイはresource group scopeのincremental modeを使用します。テンプレートからリソースを削除してもAzure上の既存リソースは自動削除されません。削除は別の明示的な運用として扱います。

## Deploy the container apps

Container Appはイメージを必要とするため、**2段階**でデプロイします。ACRが空の初回でもアプリが起動するよう、イメージ引数は公開プレースホルダーを既定にしています。

### 1. 初回デプロイ（プレースホルダーイメージ）

上の `az deployment group create` をそのまま実行すると、ACR・Key Vault・Container Apps基盤が作成され、2つのアプリは公開のhello-worldイメージで起動します。OpenAI APIキーは未指定なら、Bicepはシークレットを作成・上書きしません（`key-vault.bicep` の `if (!empty(openAiApiKeyValue))`）。本プロジェクトはシークレット `OPENAI-API-KEY` を手動投入して正本とする運用を採用しており、backendはManaged Identityで実行時に解決します。

### 2. イメージをビルドしてACRへpush

`az acr build` はローカルのDockerを使わずACR上でビルドします。レジストリ名はデプロイ出力から取得します。

```powershell
$registryName = az deployment group show `
  --resource-group '<resource-group-name>' --name 'asvs-rag-dev' `
  --query 'properties.outputs.containerRegistryName.value' -o tsv

az acr build --registry $registryName --image asvs-backend:v1 ..\backend
az acr build --registry $registryName --image asvs-frontend:v1 ..\frontend
```

### 3. 実イメージとAPIキーで再デプロイ

ログインサーバーを取得し、実イメージとOpenAI APIキーを渡して再デプロイします。`openAiApiKey` はGitへ保存せず、CLIから渡します。

```powershell
$loginServer = az deployment group show `
  --resource-group '<resource-group-name>' --name 'asvs-rag-dev' `
  --query 'properties.outputs.containerRegistryLoginServer.value' -o tsv

az deployment group create `
  --name 'asvs-rag-dev' `
  --resource-group '<resource-group-name>' `
  --template-file .\infra\main.bicep `
  --parameters .\infra\environments\dev.bicepparam `
  backendImage="$loginServer/asvs-backend:v1" `
  frontendImage="$loginServer/asvs-frontend:v1" `
  openAiApiKey='<openai-api-key>'
```

APIキーを再デプロイで渡さずに運用する場合は、Key Vaultのシークレット `OPENAI-API-KEY` を直接更新し、backendのrevisionを再起動します。

### 4. 公開URLの確認

```powershell
az deployment group show `
  --resource-group '<resource-group-name>' --name 'asvs-rag-dev' `
  --query 'properties.outputs.frontendUrl.value' -o tsv
```

backendは `backendInternalFqdn`（Environment内部）で、直接インターネット公開されません。frontendは実行時に `BACKEND_URL` で内部FQDNへ中継します。

### コストメモ

- Container Appsは既定で**scale-to-zero**（`minReplicas = 0`）。アイドル時のコンピュート課金を避けます。コールドスタートが問題なら `minReplicas = 1` に上げます。
- Log Analyticsは**日次取り込み上限**（既定1GB）で従量課金を抑えます。
- ACRは`Basic`。予算アラートは通知であり、支出の強制上限ではありません。

## CI/CD（GitHub Actions → Azure, OIDC）

`.github/workflows/deploy.yml` が、ACRでのイメージビルドとBicepデプロイを行います。認証はOIDC（federated credential）で、client secretを保存しません。コスト配慮で**手動実行（workflow_dispatch）のみ**です。CI（lint/test）は `backend.yml` / `frontend.yml` が担当します。

### 一度だけのAzure側セットアップ

```powershell
# 1. アプリ登録とサービスプリンシパル
$appId = az ad app create --display-name 'gh-asvs-rag-deploy' --query appId -o tsv
az ad sp create --id $appId

# 2. GitHub用 federated credential（例: production環境）
#    PowerShellの単一引用符内はリテラルなので、JSONの二重引用符はそのまま書く。
az ad app federated-credential create --id $appId --parameters '{
  "name": "gh-production",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:<owner>/<repo>:environment:production",
  "audiences": ["api://AzureADTokenExchange"]
}'

# 3. リソースグループへ権限（デプロイ＋ロール割り当て作成の両方が必要）
$rgId = az group show -n 'portfolio-1' --query id -o tsv
az role assignment create --assignee $appId --role 'Contributor' --scope $rgId
az role assignment create --assignee $appId --role 'Role Based Access Control Administrator' --scope $rgId
```

`subject` はワークフローの実行文脈と一致させます。`deploy.yml` は `environment: production` を使うため、GitHub側に`production`環境を作るか、`subject` を `repo:<owner>/<repo>:ref:refs/heads/main` に変えてジョブの`environment`行を外します。テンプレートがロール割り当てを作成するため、`Contributor` だけでは不足で `Role Based Access Control Administrator`（またはOwner）が要ります。

### GitHubの設定

| 種別 | キー | 値 |
| --- | --- | --- |
| Variable | `AZURE_RESOURCE_GROUP` | `portfolio-1` |
| Variable | `AZURE_CONTAINER_REGISTRY` | ACR名（例 `acrasvsragdev...`） |
| Variable | `AZURE_DEPLOYMENT_NAME` | `asvs-rag-dev`（任意） |
| Secret | `AZURE_CLIENT_ID` | アプリ登録の appId |
| Secret | `AZURE_TENANT_ID` | テナントID |
| Secret | `AZURE_SUBSCRIPTION_ID` | サブスクリプションID |
| Secret | `OPENAI_API_KEY` | OpenAI APIキー（任意。空ならKey Vaultの既存値を温存） |

### 実行

GitHubの Actions タブで **Deploy to Azure** を実行します。`deploy_apps=true`（既定）でイメージをビルド・pushし、`deployContainerApps=true` としてアプリまでデプロイします。`image_tag` を空にするとコミットSHAをタグに使います。基盤だけ更新したいときは `deploy_apps=false`。

## Authentication bootstrap

初回は`enableLocalAuthentication = true`としてAPIキーとMicrosoft Entra IDの両方を利用可能にしています。`localDeveloperPrincipalId`を設定すると、次のロールが対象リソースのスコープで冪等に追加されます。

- Azure AI Search: `Search Service Contributor`
- Azure AI Search: `Search Index Data Contributor`
- Microsoft Foundry: `Cognitive Services OpenAI User`

ローカルからMicrosoft Entra ID認証で接続できることを確認した後、`enableLocalAuthentication = false`へ変更して再デプロイするとキー認証を無効化できます。将来のApp ServiceにはManaged Identityを有効化し、そのprincipal IDへ必要最小限のデータプレーンロールを割り当てます。

## Scope of this deployment

このテンプレートが作るものは次のとおりです。

- Azure AI Search service（devではFree）
- Microsoft Foundry account（`AIServices` / `S0`）
- Microsoft Foundry project
- Azure OpenAI `text-embedding-3-small` version `1` deployment（`GlobalStandard`）
- Log Analytics workspace（日次取り込み上限付き）と Application Insights
- Azure Container Registry（`Basic`、admin無効）
- Key Vault（RBAC認可、OpenAI APIキー用シークレット）
- Container Apps Environment
- Container App ×2（frontend=外部HTTPS / backend=Environment内部ingress、Consumption・既定でscale-to-zero）
- User-assigned Managed Identity ×2（backend / frontend）と最小権限RBAC
- 指定した場合のみ、ローカル開発者用のデータプレーンRBAC

### Managed Identityと権限（最小権限）

| Identity | 役割 |
| --- | --- |
| backend | `AcrPull` / `Key Vault Secrets User` / `Search Index Data Reader` / `Cognitive Services OpenAI User` |
| frontend | `AcrPull` のみ |

frontendには生成用の認可やAzure認証情報を渡しません。backendは`AZURE_CLIENT_ID`で自分のidentityを指定し、`DefaultAzureCredential`でSearch/Embeddingへアクセスします。OpenAI APIキーはKey Vaultのシークレットをコンテナのsecret参照（identity経由）で解決します。

Azure AI SearchのIndex schemaはARMリソースではないため、`infra/scripts/deploy_search_index.py`からデータプレーンへ反映します。文書登録は[バックエンドの専用batch](../backend/scripts/README.md)から明示的に実行します。Indexのvector fieldとPythonのEmbedding要求では、`text-embedding-3-small`の出力に合わせて`dimensions = 1536`を使用します。
