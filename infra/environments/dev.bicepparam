using '../main.bicep'

param location = 'japaneast'
param workloadName = 'asvs-rag'
param environmentName = 'dev'
param searchSku = 'free'
param embeddingDeploymentName = 'text-embedding-3-small'
param embeddingModelName = 'text-embedding-3-small'
param embeddingModelVersion = '1'
param embeddingDeploymentSkuName = 'GlobalStandard'
param embeddingDeploymentCapacity = 10

param searchIndexName = 'security-docs-v1'
param openAiChatModel = 'gpt-4o-mini'
param acrSku = 'Basic'

// Two-phase deploy:
//   1st deploy: keep false → platform only (ACR/KV/env/identities/observability)
//   push images to ACR, then redeploy with: deployContainerApps=true backendImage=... frontendImage=...
param deployContainerApps = false

// 公開デモ期間はcold startを避けるためminReplicas=1で常時起動する。
// アイドルコストは小さい。活動終了後にコスト最小化したい場合は0へ戻す。
param minReplicas = 1
param maxReplicas = 1

// First deploy uses the public placeholder image so the apps provision before any
// ACR push. After `az acr build` + push, redeploy with the ACR image references, e.g.:
//   backendImage=<loginServer>/asvs-backend:<tag>
//   frontendImage=<loginServer>/asvs-frontend:<tag>
// OpenAI API key is stored in Key Vault. Leave it out of Git; pass at deploy via
//   --parameters openAiApiKey=<value>
// or set the secret in Key Vault afterward and restart the backend revision.

// Keep keys available for the first deployment. After assigning and testing
// Microsoft Entra roles, change this to false and redeploy.
param enableLocalAuthentication = true

// Keep personal identifiers out of Git. Override this parameter from the CLI.
param localDeveloperPrincipalId = ''

param tags = {
  purpose: 'fde-portfolio'
  workload: 'owasp-asvs-rag'
}
