@description('O nome do Resource Group onde os recursos serão criados.')
param location string = resourceGroup().location

@description('O nome da Conta de Armazenamento (deve ser único globalmente).')
param storageAccountName string = 'st${uniqueString(resourceGroup().id)}'

@description('O nome do contêiner de dados processados.')
param containerName string = 'processed-data'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS' 
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

resource processedContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: containerName
  properties: {
    publicAccess: 'None'
  }
}
