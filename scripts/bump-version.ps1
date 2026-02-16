#Requires -Version 5.1
<#
.SYNOPSIS
    IoTDevSim - Version Bump Script (PowerShell)
    Automates version bumping, changelog updates, and git commits

.DESCRIPTION
    This script automates the version bump process:
    - Calculates new version based on type (major, minor, patch)
    - Updates VERSION file
    - Updates package.json (frontend)
    - Updates pyproject.toml (api-service, transmission-service)
    - Updates CHANGELOG.md
    - Creates git commit with changes

.PARAMETER Type
    Type of version bump: major, minor, or patch

.PARAMETER Message
    Description of the changes for the changelog

.PARAMETER DryRun
    Simulate without making actual changes

.EXAMPLE
    .\scripts\bump-version.ps1 -Type patch -Message "Corregir ventana CMD del backend visible"
    
    Bumps patch version (e.g., 1.0.0 -> 1.0.1)

.EXAMPLE
    .\scripts\bump-version.ps1 -Type minor -Message "Añadir módulo de gestión de proveedores"
    
    Bumps minor version (e.g., 1.0.1 -> 1.1.0)

.EXAMPLE
    .\scripts\bump-version.ps1 -Type major -Message "Migración a PostgreSQL - BREAKING CHANGE"
    
    Bumps major version (e.g., 1.1.0 -> 2.0.0)

.EXAMPLE
    .\scripts\bump-version.ps1 -Type patch -Message "Fix bug" -DryRun
    
    Simulates the bump without making changes

.NOTES
    File Name      : bump-version.ps1
    Author         : IoT-DevSim Team
    Prerequisite   : PowerShell 5.1 or later, git
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("major", "minor", "patch")]
    [string]$Type,

    [Parameter(Mandatory = $true, Position = 1)]
    [string]$Message,

    [Parameter()]
    [switch]$DryRun
)

# Error handling
$ErrorActionPreference = "Stop"

# Colors for output
$Colors = @{
    Success = "Green"
    Warning = "Yellow"
    Error = "Red"
    Info = "Cyan"
    Step = "White"
}

function Write-Step {
    param([string]$Message)
    Write-Host "▶ $Message" -ForegroundColor $Colors.Step -Bold
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor $Colors.Success
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor $Colors.Warning
}

function Write-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor $Colors.Error
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ️  $Message" -ForegroundColor $Colors.Info
}

# Get project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")

# File paths
$VersionFile = Join-Path $ProjectRoot "VERSION"
$PackageJson = Join-Path $ProjectRoot "frontend\package.json"
$ApiPyproject = Join-Path $ProjectRoot "api-service\pyproject.toml"
$TransmissionPyproject = Join-Path $ProjectRoot "transmission-service\pyproject.toml"
$ChangelogFile = Join-Path $ProjectRoot "CHANGELOG.md"

function Get-CurrentVersion {
    if (Test-Path $VersionFile) {
        $version = Get-Content $VersionFile -Raw
        return $version.Trim()
    }
    return "0.0.0"
}

function Bump-Version {
    param(
        [string]$CurrentVersion,
        [string]$BumpType
    )
    
    # Parse version (handle prerelease versions like 1.0.0-beta.1)
    if ($CurrentVersion -match "^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.-]+))?(?:\+([a-zA-Z0-9.-]+))?$") {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]
        $patch = [int]$matches[3]
    }
    else {
        throw "Invalid version format: $CurrentVersion"
    }
    
    switch ($BumpType.ToLower()) {
        "major" {
            $major++
            $minor = 0
            $patch = 0
        }
        "minor" {
            $minor++
            $patch = 0
        }
        "patch" {
            $patch++
        }
    }
    
    return "$major.$minor.$patch"
}

function Update-VersionFile {
    param([string]$NewVersion)
    
    Write-Step "Updating VERSION file..."
    
    if ($DryRun) {
        Write-Info "[DRY RUN] Would write '$NewVersion' to VERSION"
        return
    }
    
    $NewVersion | Set-Content $VersionFile -NoNewline
    Write-Success "VERSION file updated to $NewVersion"
}

function Update-PackageJson {
    param([string]$NewVersion)
    
    if (-not (Test-Path $PackageJson)) {
        Write-Warning "frontend/package.json not found"
        return
    }
    
    Write-Step "Updating frontend/package.json..."
    
    if ($DryRun) {
        Write-Info "[DRY RUN] Would update version in package.json"
        return
    }
    
    $content = Get-Content $PackageJson -Raw | ConvertFrom-Json
    $content.version = $NewVersion
    $content | ConvertTo-Json -Depth 10 | Set-Content $PackageJson
    
    Write-Success "package.json updated to $NewVersion"
}

function Update-PyprojectToml {
    param(
        [string]$FilePath,
        [string]$NewVersion
    )
    
    if (-not (Test-Path $FilePath)) {
        Write-Warning "$(Split-Path $FilePath -Leaf) not found"
        return
    }
    
    Write-Step "Updating $(Split-Path $FilePath -Leaf)..."
    
    if ($DryRun) {
        Write-Info "[DRY RUN] Would update version in $(Split-Path $FilePath -Leaf)"
        return
    }
    
    $content = Get-Content $FilePath -Raw
    # Replace version line using regex
    $content = $content -replace '^(version = ")[0-9.]+(".*)$', "`${1}$NewVersion`$2"
    $content | Set-Content $FilePath -NoNewline
    
    Write-Success "$(Split-Path $FilePath -Leaf) updated to $NewVersion"
}

function Update-Changelog {
    param(
        [string]$NewVersion,
        [string]$ChangeMessage,
        [string]$ChangeType
    )
    
    Write-Step "Updating CHANGELOG.md..."
    
    # Determine section based on bump type
    $section = switch ($ChangeType.ToLower()) {
        "major" { "### ⚠️ BREAKING CHANGES" }
        "minor" { "### Added" }
        "patch" { "### Fixed" }
    }
    
    $date = Get-Date -Format "yyyy-MM-dd"
    $newEntry = @"

## [$NewVersion] - $date

$section
- $ChangeMessage

"@
    
    if ($DryRun) {
        Write-Info "[DRY RUN] Would add changelog entry:"
        Write-Info $newEntry
        return
    }
    
    if (Test-Path $ChangelogFile) {
        $content = Get-Content $ChangelogFile -Raw
        
        # Find the position after the header
        if ($content -match "(.*?## \[Unreleased\].*?

)([\s\S]*)" -or $content -match "^(.*?# Changelog.*?

)([\s\S]*)$") {
            $before = $matches[1]
            $after = $matches[2]
            $newContent = $before + $newEntry + $after
            $newContent | Set-Content $ChangelogFile -NoNewline
        }
        else {
            # Append to beginning
            $newEntry + $content | Set-Content $ChangelogFile -NoNewline
        }
    }
    else {
        # Create new changelog
        $header = @"# Changelog

Todas las modificaciones notables de este proyecto se documentarán en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/spec/v2.0.0.html).

## [Unreleased]

"@
        ($header + $newEntry) | Set-Content $ChangelogFile -NoNewline
    }
    
    Write-Success "CHANGELOG.md updated"
}

function Invoke-GitCommit {
    param(
        [string]$Version,
        [string]$ChangeType,
        [string]$Message
    )
    
    Write-Step "Creating git commit..."
    
    # Check if we're in a git repo
    $gitDir = git rev-parse --git-dir 2>$null
    if (-not $gitDir) {
        Write-Warning "Not a git repository, skipping git commit"
        return
    }
    
    if ($DryRun) {
        Write-Info "[DRY RUN] Would execute:"
        Write-Info "  git add VERSION CHANGELOG.md"
        Write-Info "  git add frontend/package.json"
        Write-Info "  git add api-service/pyproject.toml"
        Write-Info "  git add transmission-service/pyproject.toml"
        Write-Info "  git commit -m \"chore(release): bump version to $Version\""
        return
    }
    
    # Stage files
    git add $VersionFile 2>$null
    git add $ChangelogFile 2>$null
    git add $PackageJson 2>$null
    git add $ApiPyproject 2>$null
    git add $TransmissionPyproject 2>$null
    
    # Create commit
    $commitMessage = switch ($ChangeType.ToLower()) {
        "major" { "chore(release): bump major version to $Version - BREAKING CHANGES`n`n$Message" }
        "minor" { "chore(release): bump minor version to $Version`n`n$Message" }
        "patch" { "chore(release): bump patch version to $Version`n`n$Message" }
    }
    
    git commit -m $commitMessage
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Git commit created"
    }
    else {
        Write-Error "Failed to create git commit"
    }
}

# Main execution
function Main {
    Write-Host ""
    Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor $Colors.Info
    Write-Host "║         IoT-DevSim - Version Bump (PowerShell)           ║" -ForegroundColor $Colors.Info
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor $Colors.Info
    Write-Host ""
    
    if ($DryRun) {
        Write-Warning "DRY RUN MODE - No changes will be made"
        Write-Host ""
    }
    
    # Get current version
    $CurrentVersion = Get-CurrentVersion
    Write-Info "Current version: $CurrentVersion"
    
    # Calculate new version
    $NewVersion = Bump-Version -CurrentVersion $CurrentVersion -BumpType $Type
    Write-Info "New version: $NewVersion (type: $Type)"
    Write-Host ""
    
    # Confirm if not dry run
    if (-not $DryRun) {
        $confirm = Read-Host "Continue with version bump? (y/N)"
        if ($confirm -ne 'y' -and $confirm -ne 'Y') {
            Write-Warning "Version bump cancelled"
            exit 0
        }
    }
    
    # Update all files
    Update-VersionFile -NewVersion $NewVersion
    Update-PackageJson -NewVersion $NewVersion
    Update-PyprojectToml -FilePath $ApiPyproject -NewVersion $NewVersion
    Update-PyprojectToml -FilePath $TransmissionPyproject -NewVersion $NewVersion
    Update-Changelog -NewVersion $NewVersion -ChangeMessage $Message -ChangeType $Type
    
    # Git commit
    Invoke-GitCommit -Version $NewVersion -ChangeType $Type -Message $Message
    
    Write-Host ""
    Write-Success "Version bump complete: $CurrentVersion → $NewVersion"
    Write-Host ""
    
    if (-not $DryRun) {
        Write-Info "Next steps:"
        Write-Info "  1. Review the changes: git show HEAD"
        Write-Info "  2. Push to remote: git push origin <branch>"
        Write-Info "  3. Create release: .\scripts\git-release.ps1 $NewVersion"
    }
    else {
        Write-Info "This was a dry run. No changes were made."
        Write-Info "Run without -DryRun to apply changes."
    }
}

# Run main
try {
    Main
}
catch {
    Write-Error "Error: $_"
    exit 1
}
