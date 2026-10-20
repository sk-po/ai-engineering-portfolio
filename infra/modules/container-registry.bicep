@description('Globally unique Azure Container Registry name (alphanumeric only).')
param name string

@description('Azure region for the registry.')
param location string

@description('Registry SKU. Basic is sufficient for a single-environment portfolio.')
@allowed([
  'Basic'
  'Standard'
])
param skuName string = 'Basic'

@description('Principal IDs that receive the AcrPull role (application managed identities).')
param pullPrincipalIds array

param tags object

var acrPullRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '7f951dda-4ed3-4680-a7ca-43fe172d538d'
)

resource registry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: skuName
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

resource acrPullAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for principalId in pullPrincipalIds: {
    name: guid(registry.id, principalId, acrPullRoleId)
    scope: registry
    properties: {
      principalId: principalId
      principalType: 'ServicePrincipal'
      roleDefinitionId: acrPullRoleId
    }
  }
]

output id string = registry.id
output name string = registry.name
output loginServer string = registry.properties.loginServer
