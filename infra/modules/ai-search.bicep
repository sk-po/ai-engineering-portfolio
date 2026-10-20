@description('Globally unique Azure AI Search service name.')
param name string

@description('Azure region for the search service.')
param location string

@allowed([
  'free'
  'basic'
])
param skuName string

@description('Whether API-key authentication remains enabled in addition to Microsoft Entra ID authentication.')
param enableLocalAuthentication bool

@description('Optional Microsoft Entra object ID that receives local development roles.')
param localDeveloperPrincipalId string

@description('Optional application managed identity principal ID that receives read-only index access for query.')
param applicationPrincipalId string = ''

param tags object

var searchServiceContributorRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
)
var searchIndexDataContributorRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
)
var searchIndexDataReaderRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '1407120a-92aa-4202-b7e9-c0e197c71c8f'
)
var assignLocalDeveloperRoles = !empty(localDeveloperPrincipalId)
var assignApplicationRole = !empty(applicationPrincipalId)

resource searchService 'Microsoft.Search/searchServices@2025-05-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: skuName
  }
  properties: {
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
    disableLocalAuth: !enableLocalAuthentication
    hostingMode: 'Default'
    partitionCount: 1
    publicNetworkAccess: 'Enabled'
    replicaCount: 1
  }
}

resource searchServiceContributorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (assignLocalDeveloperRoles) {
  name: guid(searchService.id, localDeveloperPrincipalId, searchServiceContributorRoleId)
  scope: searchService
  properties: {
    principalId: localDeveloperPrincipalId
    principalType: 'User'
    roleDefinitionId: searchServiceContributorRoleId
  }
}

resource searchIndexDataContributorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (assignLocalDeveloperRoles) {
  name: guid(searchService.id, localDeveloperPrincipalId, searchIndexDataContributorRoleId)
  scope: searchService
  properties: {
    principalId: localDeveloperPrincipalId
    principalType: 'User'
    roleDefinitionId: searchIndexDataContributorRoleId
  }
}

resource searchIndexDataReaderAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (assignApplicationRole) {
  name: guid(searchService.id, applicationPrincipalId, searchIndexDataReaderRoleId)
  scope: searchService
  properties: {
    principalId: applicationPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: searchIndexDataReaderRoleId
  }
}

output id string = searchService.id
output name string = searchService.name
output endpoint string = 'https://${searchService.name}.search.windows.net'
