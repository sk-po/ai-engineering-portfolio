[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$CommonName,

    [string]$Thumbprint,

    [switch]$Force
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$certificateDirectory = Join-Path $projectRoot ".certs"
$outputPath = Join-Path $certificateDirectory "local-ca.crt"

if ((Test-Path -LiteralPath $outputPath) -and -not $Force) {
    throw "$outputPath already exists. Use -Force to replace it intentionally."
}

$certificates = @(
    Get-ChildItem Cert:\CurrentUser\Root, Cert:\LocalMachine\Root |
        Where-Object {
            $_.GetNameInfo([System.Security.Cryptography.X509Certificates.X509NameType]::SimpleName, $false) -eq $CommonName
        }
) | Sort-Object -Property Thumbprint -Unique

if ($Thumbprint) {
    $normalizedThumbprint = $Thumbprint.Replace(" ", "").ToUpperInvariant()
    $certificates = @($certificates | Where-Object Thumbprint -EQ $normalizedThumbprint)
}

if ($certificates.Count -eq 0) {
    throw "No trusted root certificate named '$CommonName' was found."
}

if ($certificates.Count -gt 1) {
    $availableThumbprints = ($certificates.Thumbprint -join ", ")
    throw "Multiple certificates matched. Re-run with -Thumbprint. Matches: $availableThumbprints"
}

New-Item -ItemType Directory -Path $certificateDirectory -Force | Out-Null

$base64 = [Convert]::ToBase64String(
    $certificates[0].RawData,
    [Base64FormattingOptions]::InsertLineBreaks
)
$pem = "-----BEGIN CERTIFICATE-----`n$base64`n-----END CERTIFICATE-----`n"
[IO.File]::WriteAllText($outputPath, $pem, [Text.UTF8Encoding]::new($false))

Write-Host "Exported trusted root certificate to $outputPath"
