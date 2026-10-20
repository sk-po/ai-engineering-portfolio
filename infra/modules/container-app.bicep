@description('Container App name.')
param name string

@description('Azure region for the container app.')
param location string

@description('Resource ID of the Container Apps managed environment.')
param environmentId string

@description('Resource ID of the user-assigned managed identity used for ACR pull and secret access.')
param identityId string

@description('Container image reference. Use a public placeholder for the first deploy, then the ACR image after pushing.')
param image string

@description('Container listen port exposed through ingress.')
param targetPort int

@description('Whether ingress is reachable from the public internet. Backend stays false (environment-internal only).')
param external bool

@description('Minimum replicas. 0 enables scale-to-zero for the lowest idle cost.')
@minValue(0)
param minReplicas int = 0

@description('Maximum replicas.')
@minValue(1)
param maxReplicas int = 1

@description('vCPU per replica as a string, converted to a number (e.g. 0.5).')
param cpu string = '0.5'

@description('Memory per replica (e.g. 1Gi).')
param memory string = '1Gi'

@description('Environment variables. Each item is {name, value} or {name, secretRef}.')
param environmentVariables array = []

@description('Secret definitions resolved from Key Vault. Each item is {name, keyVaultUrl, identity}.')
param secrets array = []

@description('ACR login server used as a registry with the managed identity. Empty skips registry configuration.')
param registryServer string = ''

@description('HTTP path used for liveness and readiness probes.')
param healthPath string = '/'

param tags object

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: external
        targetPort: targetPort
        transport: 'auto'
        allowInsecure: false
      }
      registries: empty(registryServer)
        ? []
        : [
            {
              server: registryServer
              identity: identityId
            }
          ]
      secrets: secrets
    }
    template: {
      containers: [
        {
          name: name
          image: image
          resources: {
            cpu: json(cpu)
            memory: memory
          }
          env: environmentVariables
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: healthPath
                port: targetPort
              }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
            {
              type: 'Readiness'
              httpGet: {
                path: healthPath
                port: targetPort
              }
              initialDelaySeconds: 3
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
      }
    }
  }
}

output id string = containerApp.id
output name string = containerApp.name
output fqdn string = containerApp.properties.configuration.ingress.fqdn
