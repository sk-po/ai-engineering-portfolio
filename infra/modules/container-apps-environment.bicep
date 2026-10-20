@description('Container Apps managed environment name.')
param name string

@description('Azure region for the environment.')
param location string

@description('Resource ID of the Log Analytics workspace used for app logs.')
param logAnalyticsWorkspaceId string

@description('Customer ID (workspace ID) of the Log Analytics workspace.')
param logAnalyticsCustomerId string

param tags object

resource managedEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsCustomerId
        sharedKey: listKeys(logAnalyticsWorkspaceId, '2023-09-01').primarySharedKey
      }
    }
  }
}

output id string = managedEnvironment.id
output name string = managedEnvironment.name
output defaultDomain string = managedEnvironment.properties.defaultDomain
