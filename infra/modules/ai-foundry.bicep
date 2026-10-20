@description('Globally unique Microsoft Foundry account name.')
param accountName string

@description('Foundry project resource name.')
param projectName string

@description('Foundry project display name.')
param projectDisplayName string

@description('Azure region for the Foundry account and project.')
param location string

@description('Whether API-key authentication remains enabled in addition to Microsoft Entra ID authentication.')
param enableLocalAuthentication bool

@description('Optional Microsoft Entra object ID that receives model inference permission.')
param localDeveloperPrincipalId string

@description('Optional application managed identity principal ID that receives model inference permission.')
param applicationPrincipalId string = ''

@description('Name used by applications when invoking the embedding model deployment.')
param embeddingDeploymentName string

@description('OpenAI embedding model name.')
param embeddingModelName string

@description('Pinned embedding model version.')
param embeddingModelVersion string

@description('Embedding model deployment SKU.')
@allowed([
  'GlobalStandard'
  'Standard'
])
param embeddingDeploymentSkuName string

@description('Embedding model deployment capacity in model-specific quota units.')
@minValue(1)
param embeddingDeploymentCapacity int

param tags object

var cognitiveServicesOpenAIUserRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
)
var assignLocalDeveloperRole = !empty(localDeveloperPrincipalId)
var assignApplicationRole = !empty(applicationPrincipalId)

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: accountName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  properties: {
    allowProjectManagement: true
    customSubDomainName: accountName
    disableLocalAuth: !enableLocalAuthentication
    publicNetworkAccess: 'Enabled'
  }
}

resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: account
  name: embeddingDeploymentName
  sku: {
    name: embeddingDeploymentSkuName
    capacity: embeddingDeploymentCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: embeddingModelName
      version: embeddingModelVersion
    }
    versionUpgradeOption: 'NoAutoUpgrade'
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: account
  name: projectName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    description: 'Microsoft Foundry project for the OWASP ASVS RAG portfolio.'
    displayName: projectDisplayName
  }
}

resource cognitiveServicesOpenAIUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (assignLocalDeveloperRole) {
  name: guid(account.id, localDeveloperPrincipalId, cognitiveServicesOpenAIUserRoleId)
  scope: account
  properties: {
    principalId: localDeveloperPrincipalId
    principalType: 'User'
    roleDefinitionId: cognitiveServicesOpenAIUserRoleId
  }
}

resource cognitiveServicesOpenAIUserAppAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (assignApplicationRole) {
  name: guid(account.id, applicationPrincipalId, cognitiveServicesOpenAIUserRoleId)
  scope: account
  properties: {
    principalId: applicationPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: cognitiveServicesOpenAIUserRoleId
  }
}

output accountId string = account.id
output accountName string = account.name
output endpoint string = account.properties.endpoint
output projectId string = project.id
output projectName string = project.name
output embeddingDeploymentName string = embeddingDeployment.name
output embeddingModelName string = embeddingModelName
output embeddingModelVersion string = embeddingModelVersion
