@description('Globally unique Key Vault name.')
param name string

@description('Azure region for the Key Vault.')
param location string

@description('Principal IDs that receive the Key Vault Secrets User role (application managed identities).')
param secretsUserPrincipalIds array

@description('Optional Microsoft Entra object ID for a local developer who may read secrets.')
param localDeveloperPrincipalId string = ''

@description('Name of the secret holding the OpenAI API key used for answer generation.')
param openAiApiKeySecretName string = 'OPENAI-API-KEY'

@description('OpenAI API key value. Empty stores a placeholder; pass a real value at deploy time, or replace it in Key Vault afterward and restart the backend revision.')
@secure()
param openAiApiKeyValue string = ''

param tags object

var keyVaultSecretsUserRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '4633458b-17de-408a-b874-0445c86b69e6'
)

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    publicNetworkAccess: 'Enabled'
  }
}

// 値が渡されたときだけシークレットを作成/更新する。空のまま再デプロイしても、
// 既存の値をプレースホルダーへ上書きしない（incrementalモードでは未宣言リソースは削除されない）。
resource openAiApiKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(openAiApiKeyValue)) {
  parent: vault
  name: openAiApiKeySecretName
  properties: {
    value: openAiApiKeyValue
  }
}

resource applicationSecretsUserAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for principalId in secretsUserPrincipalIds: {
    name: guid(vault.id, principalId, keyVaultSecretsUserRoleId)
    scope: vault
    properties: {
      principalId: principalId
      principalType: 'ServicePrincipal'
      roleDefinitionId: keyVaultSecretsUserRoleId
    }
  }
]

resource localDeveloperSecretsUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(localDeveloperPrincipalId)) {
  name: guid(vault.id, localDeveloperPrincipalId, keyVaultSecretsUserRoleId)
  scope: vault
  properties: {
    principalId: localDeveloperPrincipalId
    principalType: 'User'
    roleDefinitionId: keyVaultSecretsUserRoleId
  }
}

output id string = vault.id
output name string = vault.name
output uri string = vault.properties.vaultUri
output openAiApiKeySecretName string = openAiApiKeySecretName
