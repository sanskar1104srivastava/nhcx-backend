<#
.SYNOPSIS
Deploy the NHCX backend container image to the bridge Lambdas.

.DESCRIPTION
This repo has two AWS Lambda functions and both use the same Docker image:

- nhcx-bridge-<stage>-api      -> nhcx.main.handler, API Gateway/FastAPI
- nhcx-bridge-<stage>-consumer -> nhcx.consumer.handler, SQS inbound worker

By default this script performs the known-good code deployment path for the
existing stack: build the Lambda image, push it to ECR, update both Lambda
functions to that image, wait for successful updates, then call /health.

Use -FullStack only when changing serverless.yml resources, IAM, queues,
tables, API Gateway, or Lambda environment values. It requires a working
Serverless Framework login/license.
#>

[CmdletBinding()]
param(
    [string]$Profile = "algoflow",
    [string]$Region = "ap-south-1",
    [string]$Stage = "dev",
    [string]$RepositoryName = "serverless-nhcx-bridge-dev",
    [string]$ApiFunctionName = "nhcx-bridge-dev-api",
    [string]$ConsumerFunctionName = "nhcx-bridge-dev-consumer",
    [string]$Tag = "",
    [string]$ImageUri = "",
    [string]$HealthCheckUrl = "",
    [string]$EnvFile = ".env",
    [int]$TimeoutSeconds = 300,

    [ValidateSet("all", "api", "consumer")]
    [string]$Function = "all",

    [switch]$SkipTests,
    [switch]$SkipDockerBuild,
    [switch]$SkipWait,
    [switch]$SkipHealthCheck,
    [switch]$NoEnvFile,
    [switch]$FullStack
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message"
}

function Test-Blank {
    param([AllowNull()][string]$Value)
    return [string]::IsNullOrWhiteSpace($Value)
}

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found on PATH."
    }
}

function Invoke-External {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [switch]$Capture,
        [switch]$AllowFailure
    )

    $display = "$FilePath $($Arguments -join ' ')"
    Write-Host "> $display"

    if ($Capture -or $AllowFailure) {
        $output = & $FilePath @Arguments 2>&1
        $exitCode = $LASTEXITCODE
        $text = (($output | Out-String).Trim())
        if ($exitCode -ne 0 -and -not $AllowFailure) {
            throw "Command failed with exit code $exitCode`: $display`n$text"
        }
        return [pscustomobject]@{
            ExitCode = $exitCode
            Output = $text
        }
    }

    & $FilePath @Arguments
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw "Command failed with exit code $exitCode`: $display"
    }
    return [pscustomobject]@{
        ExitCode = $exitCode
        Output = ""
    }
}

function Invoke-Aws {
    param(
        [string[]]$Arguments,
        [switch]$Capture,
        [switch]$AllowFailure
    )

    $awsArgs = @($Arguments)
    if (-not (Test-Blank $Profile)) {
        $awsArgs += @("--profile", $Profile)
    }
    if (-not (Test-Blank $Region)) {
        $awsArgs += @("--region", $Region)
    }
    return Invoke-External -FilePath "aws" -Arguments $awsArgs -Capture:$Capture -AllowFailure:$AllowFailure
}

function Import-DotEnv {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    foreach ($rawLine in Get-Content -LiteralPath $Path) {
        $line = $rawLine.Trim()
        if ($line.Length -eq 0 -or $line.StartsWith("#")) {
            continue
        }

        $match = [regex]::Match($line, "^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$")
        if (-not $match.Success) {
            continue
        }

        $name = $match.Groups[1].Value
        $value = $match.Groups[2].Value.Trim()
        $isQuoted = (
            ($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))
        )

        if ($isQuoted -and $value.Length -ge 2) {
            $value = $value.Substring(1, $value.Length - 2)
        } elseif ($value -match "\s+#") {
            $value = ($value -replace "\s+#.*$", "").TrimEnd()
        }

        [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }

    Write-Host "Loaded environment variables from $Path"
}

function Get-PythonPath {
    $venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython) {
        return $venvPython
    }
    return "python"
}

function Get-ServerlessCommand {
    $serverless = Get-Command "serverless" -ErrorAction SilentlyContinue
    if ($serverless) {
        return $serverless.Source
    }

    $sls = Get-Command "sls" -ErrorAction SilentlyContinue
    if ($sls) {
        return $sls.Source
    }

    throw "Serverless Framework command was not found. Install/configure it before using -FullStack."
}

if (-not $NoEnvFile) {
    Import-DotEnv -Path (Join-Path $RepoRoot $EnvFile)
}

if (Test-Blank $RepositoryName) {
    $RepositoryName = "serverless-nhcx-bridge-$Stage"
}
if (Test-Blank $ApiFunctionName) {
    $ApiFunctionName = "nhcx-bridge-$Stage-api"
}
if (Test-Blank $ConsumerFunctionName) {
    $ConsumerFunctionName = "nhcx-bridge-$Stage-consumer"
}

$FunctionsToDeploy = switch ($Function) {
    "api" { @("api") }
    "consumer" { @("consumer") }
    default { @("api", "consumer") }
}

Write-Step "Deployment target"
Write-Host "Profile:        $Profile"
Write-Host "Region:         $Region"
Write-Host "Stage:          $Stage"
Write-Host "ECR repository: $RepositoryName"
Write-Host "Functions:      $($FunctionsToDeploy -join ', ')"
Write-Host "Timeout:        $TimeoutSeconds seconds"

if (-not $SkipTests) {
    Write-Step "Running local verification"
    $python = Get-PythonPath
    Invoke-External -FilePath $python -Arguments @("-m", "compileall", "nhcx", "scripts", "test_smoke.py") | Out-Null
    Invoke-External -FilePath $python -Arguments @("test_smoke.py") | Out-Null
    Invoke-External -FilePath $python -Arguments @("-m", "unittest", "scripts.test_payer_side_samples") | Out-Null
} else {
    Write-Step "Skipping local verification"
}

if ($FullStack) {
    Write-Step "Running Serverless full-stack deploy"
    Require-Command "aws"
    $serverlessCommand = Get-ServerlessCommand
    $env:AWS_PROFILE = $Profile
    $env:AWS_REGION = $Region
    Invoke-External -FilePath $serverlessCommand -Arguments @("deploy", "--stage", $Stage) | Out-Null
    Write-Host "Full-stack deploy finished."
    exit 0
}

Require-Command "aws"
if (Test-Blank $ImageUri) {
    Require-Command "docker"
}

Write-Step "Resolving AWS account"
$accountResult = Invoke-Aws -Arguments @("sts", "get-caller-identity", "--query", "Account", "--output", "text") -Capture
$AccountId = $accountResult.Output.Trim()
if (Test-Blank $AccountId) {
    throw "Could not resolve AWS account id."
}

$Registry = "$AccountId.dkr.ecr.$Region.amazonaws.com"
$RepositoryUri = "$Registry/$RepositoryName"

if (Test-Blank $ImageUri) {
    if (Test-Blank $Tag) {
        $gitResult = Invoke-External -FilePath "git" -Arguments @("rev-parse", "--short", "HEAD") -Capture -AllowFailure
        $shortSha = if ($gitResult.ExitCode -eq 0 -and -not (Test-Blank $gitResult.Output)) { $gitResult.Output.Trim() } else { "nogit" }
        $Tag = "backend-apis-$(Get-Date -Format 'yyyyMMdd-HHmm')-$shortSha"
    }

    $LocalImage = "nhcx-bridge-backend:$Tag"
    $ImageUri = "$RepositoryUri`:$Tag"

    Write-Step "Checking ECR repository"
    $repoCheck = Invoke-Aws -Arguments @("ecr", "describe-repositories", "--repository-names", $RepositoryName, "--output", "json") -Capture -AllowFailure
    if ($repoCheck.ExitCode -ne 0) {
        Write-Host "ECR repository not found; creating $RepositoryName"
        Invoke-Aws -Arguments @("ecr", "create-repository", "--repository-name", $RepositoryName, "--image-scanning-configuration", "scanOnPush=true", "--output", "json") | Out-Null
    }

    Write-Step "Logging in to ECR"
    $passwordResult = Invoke-Aws -Arguments @("ecr", "get-login-password") -Capture
    Write-Host "> docker login --username AWS --password-stdin $Registry"
    $passwordResult.Output | docker login --username AWS --password-stdin $Registry
    if ($LASTEXITCODE -ne 0) {
        throw "Docker login failed for $Registry."
    }

    if (-not $SkipDockerBuild) {
        Write-Step "Building Lambda image"
        Invoke-External -FilePath "docker" -Arguments @("build", "--platform", "linux/amd64", "-t", $LocalImage, ".") | Out-Null
    } else {
        Write-Step "Skipping Docker build; expecting local image $LocalImage"
    }

    Write-Step "Pushing Lambda image"
    Invoke-External -FilePath "docker" -Arguments @("tag", $LocalImage, $ImageUri) | Out-Null
    Invoke-External -FilePath "docker" -Arguments @("push", $ImageUri) | Out-Null

    $digestResult = Invoke-Aws -Arguments @("ecr", "describe-images", "--repository-name", $RepositoryName, "--image-ids", "imageTag=$Tag", "--query", "imageDetails[0].imageDigest", "--output", "text") -Capture
    if (-not (Test-Blank $digestResult.Output)) {
        Write-Host "Pushed digest: $($digestResult.Output)"
    }
} else {
    Write-Step "Using supplied image"
    Write-Host "Image URI: $ImageUri"
}

Write-Step "Validating Lambda functions"
$FunctionNames = @{
    api = $ApiFunctionName
    consumer = $ConsumerFunctionName
}
$ExpectedCommands = @{
    api = "nhcx.main.handler"
    consumer = "nhcx.consumer.handler"
}

foreach ($logicalName in $FunctionsToDeploy) {
    $lambdaName = $FunctionNames[$logicalName]
    $configResult = Invoke-Aws -Arguments @("lambda", "get-function-configuration", "--function-name", $lambdaName, "--output", "json") -Capture
    $config = $configResult.Output | ConvertFrom-Json
    if ($config.PackageType -ne "Image") {
        throw "$lambdaName is PackageType '$($config.PackageType)', expected 'Image'."
    }

    $actualCommand = ""
    $hasImageConfig = $config.PSObject.Properties.Name -contains "ImageConfig"
    $hasImageCommand = $hasImageConfig -and $config.ImageConfig -and ($config.ImageConfig.PSObject.Properties.Name -contains "Command")
    if ($hasImageCommand -and $config.ImageConfig.Command) {
        $actualCommand = ($config.ImageConfig.Command -join ",")
    }
    if ($actualCommand -ne $ExpectedCommands[$logicalName]) {
        Write-Warning "$lambdaName image command is '$actualCommand', expected '$($ExpectedCommands[$logicalName])'. The code update will preserve the existing command."
    }
}

Write-Step "Updating Lambda code"
foreach ($logicalName in $FunctionsToDeploy) {
    $lambdaName = $FunctionNames[$logicalName]
    Invoke-Aws -Arguments @("lambda", "update-function-code", "--function-name", $lambdaName, "--image-uri", $ImageUri, "--output", "json") | Out-Null
}

if (-not $SkipWait) {
    Write-Step "Waiting for Lambda updates"
    foreach ($logicalName in $FunctionsToDeploy) {
        $lambdaName = $FunctionNames[$logicalName]
        Invoke-Aws -Arguments @("lambda", "wait", "function-updated", "--function-name", $lambdaName) | Out-Null
    }
}

Write-Step "Updating Lambda timeout"
foreach ($logicalName in $FunctionsToDeploy) {
    $lambdaName = $FunctionNames[$logicalName]
    Invoke-Aws -Arguments @("lambda", "update-function-configuration", "--function-name", $lambdaName, "--timeout", "$TimeoutSeconds", "--output", "json") | Out-Null
}

if (-not $SkipWait) {
    Write-Step "Waiting for timeout updates"
    foreach ($logicalName in $FunctionsToDeploy) {
        $lambdaName = $FunctionNames[$logicalName]
        Invoke-Aws -Arguments @("lambda", "wait", "function-updated", "--function-name", $lambdaName) | Out-Null
    }
}

Write-Step "Lambda deployment status"
foreach ($logicalName in $FunctionsToDeploy) {
    $lambdaName = $FunctionNames[$logicalName]
    $status = Invoke-Aws -Arguments @(
        "lambda", "get-function-configuration",
        "--function-name", $lambdaName,
        "--query", "{FunctionName:FunctionName,State:State,LastUpdateStatus:LastUpdateStatus,Timeout:Timeout,CodeSha256:CodeSha256,LastModified:LastModified}",
        "--output", "json"
    ) -Capture
    Write-Host $status.Output
}

if (-not $SkipHealthCheck) {
    Write-Step "Health check"
    if (Test-Blank $HealthCheckUrl) {
        $stackName = "nhcx-bridge-$Stage"
        $stackResult = Invoke-Aws -Arguments @(
            "cloudformation", "describe-stacks",
            "--stack-name", $stackName,
            "--query", "Stacks[0].Outputs[?OutputKey=='HttpApiUrl'].OutputValue | [0]",
            "--output", "text"
        ) -Capture -AllowFailure

        if ($stackResult.ExitCode -eq 0 -and -not (Test-Blank $stackResult.Output) -and $stackResult.Output -ne "None") {
            $HealthCheckUrl = $stackResult.Output.TrimEnd("/")
        }
    }

    if (Test-Blank $HealthCheckUrl) {
        Write-Warning "Could not resolve the API Gateway URL; skipping /health. Pass -HealthCheckUrl to force it."
    } else {
        $healthUri = "$($HealthCheckUrl.TrimEnd('/'))/health"
        Write-Host "> GET $healthUri"
        $health = Invoke-RestMethod -Uri $healthUri -Method Get -TimeoutSec 30
        Write-Host "Health response: $($health | ConvertTo-Json -Compress)"
    }
}

Write-Step "Done"
Write-Host "Deployed image: $ImageUri"
