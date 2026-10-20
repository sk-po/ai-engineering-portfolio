targetScope = 'resourceGroup'

@description('Azure region in which the resources are deployed.')
param location string = resourceGroup().location

@description('Short workload identifier used in resource names.')
@minLength(2)
@maxLength(20)
param workloadName string = 'asvs-rag'

@description('Deployment environment identifier, such as dev, stg, or prod.')
@minLength(2)
@maxLength(12)
param environmentName string = 'dev'

@description('Azure AI Search SKU. Use free for the portfolio MVP and basic when network isolation or scaling is required.')
@allowed([
  'free'
  'basic'
])
param searchSku string = 'free'

@description('Name used by applications when invoking the embedding model deployment.')
param embeddingDeploymentName string = 'text-embedding-3-small'

@description('Embedding model deployed to Microsoft Foundry.')
@allowed([
  'text-embedding-3-small'
])
param embeddingModelName string = 'text-embedding-3-small'

@description('Pinned embedding model version.')
param embeddingModelVersion string = '1'

@description('Embedding deployment SKU. GlobalStandard is pay-per-token and can process data outside the resource region.')
@allowed([
  'GlobalStandard'
  'Standard'
])
param embeddingDeploymentSkuName string = 'GlobalStandard'

@description('Embedding deployment capacity in model-specific quota units.')
@minValue(1)
param embeddingDeploymentCapacity int = 10

@description('Keep local API-key authentication available during bootstrap. Set to false after RBAC access has been verified.')
param enableLocalAuthentication bool = true

@description('Optional Microsoft Entra object ID for a local developer. Leave empty to skip data-plane role assignments.')
param localDeveloperPrincipalId string = ''

@description('Azure AI Search index name used by the backend for query.')
param searchIndexName string = 'security-docs-v1'

@description('OpenAI chat model used for answer generation.')
param openAiChatModel string = 'gpt-4o-mini'

@description('OpenAI API key stored in Key Vault. Leave empty to store a placeholder; pass a real value at deploy, or replace it in Key Vault afterward and restart the backend revision.')
@secure()
param openAiApiKey string = ''

@description('Backend container image. Use the public placeholder for the first deploy, then the ACR image after pushing.')
param backendImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('Frontend container image. Use the public placeholder for the first deploy, then the ACR image after pushing.')
param frontendImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('Azure Container Registry SKU.')
@allowed([
  'Basic'
  'Standard'
])
param acrSku string = 'Basic'

@description('Deploy the two container apps. Keep false for the first (platform-only) deploy, push images to ACR, then set true with real image references.')
param deployContainerApps bool = false

@description('vCPU per replica for each container app.')
param containerCpu string = '0.5'

@description('Memory per replica for each container app.')
param containerMemory string = '1Gi'

@description('Minimum replicas per app. 0 enables scale-to-zero for the lowest idle cost.')
@minValue(0)
param minReplicas int = 0

@description('Maximum replicas per app.')
@minValue(1)
param maxReplicas int = 1

@description('Log Analytics retention in days.')
@minValue(30)
param logAnalyticsRetentionDays int = 30

@description('Log Analytics daily ingestion cap in GB. -1 disables the cap.')
param logAnalyticsDailyQuotaGb int = 1

@description('Tags applied to every resource.')
param tags object = {}

var resourceSuffix = uniqueString(subscription().subscriptionId, resourceGroup().id)
var resourceNamePrefix = '${workloadName}-${environmentName}'
var commonTags = union(tags, {
  application: workloadName
  environment: environmentName
  managedBy: 'bicep'
})

var acrName = toLower(replace('acr${workloadName}${environmentName}${resourceSuffix}', '-', ''))
var keyVaultName = take(toLower('kv${environmentName}${resourceSuffix}'), 24)

resource backendIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-backend-${resourceNamePrefix}'
  location: location
  tags: commonTags
}

resource frontendIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-frontend-${resourceNamePrefix}'
  location: location
  tags: commonTags
}

module search 'modules/ai-search.bicep' = {
  name: 'ai-search-${environmentName}'
  params: {
    name: 'search-${resourceNamePrefix}-${resourceSuffix}'
    location: location
    skuName: searchSku
    enableLocalAuthentication: enableLocalAuthentication
    localDeveloperPrincipalId: localDeveloperPrincipalId
    applicationPrincipalId: backendIdentity.properties.principalId
    tags: commonTags
  }
}

module foundry 'modules/ai-foundry.bicep' = {
  name: 'ai-foundry-${environmentName}'
  params: {
    accountName: 'ai-${resourceNamePrefix}-${resourceSuffix}'
    projectName: '${resourceNamePrefix}-project'
    projectDisplayName: '${workloadName} ${environmentName}'
    location: location
    enableLocalAuthentication: enableLocalAuthentication
    localDeveloperPrincipalId: localDeveloperPrincipalId
    embeddingDeploymentName: embeddingDeploymentName
    embeddingModelName: embeddingModelName
    embeddingModelVersion: embeddingModelVersion
    embeddingDeploymentSkuName: embeddingDeploymentSkuName
    embeddingDeploymentCapacity: embeddingDeploymentCapacity
    applicationPrincipalId: backendIdentity.properties.principalId
    tags: commonTags
  }
}

module observability 'modules/observability.bicep' = {
  name: 'observability-${environmentName}'
  params: {
    logAnalyticsName: 'log-${resourceNamePrefix}-${resourceSuffix}'
    appInsightsName: 'appi-${resourceNamePrefix}-${resourceSuffix}'
    location: location
    retentionInDays: logAnalyticsRetentionDays
    dailyQuotaGb: logAnalyticsDailyQuotaGb
    tags: commonTags
  }
}

module registry 'modules/container-registry.bicep' = {
  name: 'acr-${environmentName}'
  params: {
    name: acrName
    location: location
    skuName: acrSku
    pullPrincipalIds: [
      backendIdentity.properties.principalId
      frontendIdentity.properties.principalId
    ]
    tags: commonTags
  }
}

module keyVault 'modules/key-vault.bicep' = {
  name: 'key-vault-${environmentName}'
  params: {
    name: keyVaultName
    location: location
    secretsUserPrincipalIds: [
      backendIdentity.properties.principalId
    ]
    localDeveloperPrincipalId: localDeveloperPrincipalId
    openAiApiKeyValue: openAiApiKey
    tags: commonTags
  }
}

module containerEnvironment 'modules/container-apps-environment.bicep' = {
  name: 'container-env-${environmentName}'
  params: {
    name: 'cae-${resourceNamePrefix}-${resourceSuffix}'
    location: location
    logAnalyticsWorkspaceId: observability.outputs.workspaceId
    logAnalyticsCustomerId: observability.outputs.workspaceCustomerId
    tags: commonTags
  }
}

module backendApp 'modules/container-app.bicep' = if (deployContainerApps) {
  name: 'backend-app-${environmentName}'
  params: {
    name: 'backend-${resourceNamePrefix}'
    location: location
    environmentId: containerEnvironment.outputs.id
    identityId: backendIdentity.id
    image: backendImage
    targetPort: 8000
    external: false
    minReplicas: minReplicas
    maxReplicas: maxReplicas
    cpu: containerCpu
    memory: containerMemory
    registryServer: registry.outputs.loginServer
    healthPath: '/health'
    secrets: [
      {
        name: 'openai-api-key'
        keyVaultUrl: '${keyVault.outputs.uri}secrets/${keyVault.outputs.openAiApiKeySecretName}'
        identity: backendIdentity.id
      }
    ]
    environmentVariables: [
      {
        name: 'ASVS_SEARCH_BACKEND'
        value: 'azure'
      }
      {
        name: 'AZURE_SEARCH_ENDPOINT'
        value: search.outputs.endpoint
      }
      {
        name: 'AZURE_SEARCH_INDEX_NAME'
        value: searchIndexName
      }
      {
        name: 'AZURE_OPENAI_BASE_URL'
        value: 'https://${foundry.outputs.accountName}.openai.azure.com/openai/v1/'
      }
      {
        name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT'
        value: foundry.outputs.embeddingDeploymentName
      }
      {
        name: 'OPENAI_CHAT_MODEL'
        value: openAiChatModel
      }
      {
        name: 'OPENAI_API_KEY'
        secretRef: 'openai-api-key'
      }
      {
        name: 'AZURE_CLIENT_ID'
        value: backendIdentity.properties.clientId
      }
      {
        name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
        value: observability.outputs.appInsightsConnectionString
      }
    ]
    tags: commonTags
  }
}

module frontendApp 'modules/container-app.bicep' = if (deployContainerApps) {
  name: 'frontend-app-${environmentName}'
  params: {
    name: 'frontend-${resourceNamePrefix}'
    location: location
    environmentId: containerEnvironment.outputs.id
    identityId: frontendIdentity.id
    image: frontendImage
    targetPort: 3000
    external: true
    minReplicas: minReplicas
    maxReplicas: maxReplicas
    cpu: containerCpu
    memory: containerMemory
    registryServer: registry.outputs.loginServer
    healthPath: '/'
    environmentVariables: [
      {
        name: 'BACKEND_URL'
        value: 'https://${backendApp.?outputs.fqdn ?? ''}'
      }
    ]
    tags: commonTags
  }
}

output searchServiceName string = search.outputs.name
output searchEndpoint string = search.outputs.endpoint
output foundryAccountName string = foundry.outputs.accountName
output foundryEndpoint string = foundry.outputs.endpoint
output foundryProjectName string = foundry.outputs.projectName
output embeddingDeploymentName string = foundry.outputs.embeddingDeploymentName
output embeddingModelName string = foundry.outputs.embeddingModelName
output embeddingModelVersion string = foundry.outputs.embeddingModelVersion
output containerRegistryLoginServer string = registry.outputs.loginServer
output containerRegistryName string = registry.outputs.name
output keyVaultName string = keyVault.outputs.name
output keyVaultUri string = keyVault.outputs.uri
output backendIdentityClientId string = backendIdentity.properties.clientId
output backendAppName string = backendApp.?outputs.name ?? ''
output backendInternalFqdn string = backendApp.?outputs.fqdn ?? ''
output frontendAppName string = frontendApp.?outputs.name ?? ''
output frontendUrl string = empty(frontendApp.?outputs.fqdn ?? '')
  ? ''
  : 'https://${frontendApp!.outputs.fqdn}'
output appInsightsConnectionString string = observability.outputs.appInsightsConnectionString
