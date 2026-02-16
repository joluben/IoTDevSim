#Requires -Version 5.1
<#
.SYNOPSIS
    IoTDevSim - Git Release Script (PowerShell)
    Automates the entire release process: version bump, changelog, tag, push

.DESCRIPTION
    This script automates the complete release process:
    - Validates version format (SemVer)
    - Creates release branch
    - Updates version in all project files
    - Generates changelog from commits
    - Commits version changes
    - Merges to main and develop
    - Creates annotated git tag
    - Pushes to remote
    - Creates GitHub Release (optional)

.PARAMETER Version
    Semantic version (e.g., 2.1.0, 2.1.0-beta.1)

.PARAMETER DryRun
    Simulate without executing

.PARAMETER Force
    Skip confirmations

.PARAMETER NoPush
    Don't push to remote (local only)

.EXAMPLE
    .\scripts\git-release.ps1 2.1.0
    
    Creates release v2.1.0 with full automation

.EXAMPLE
    .\scripts\git-release.ps1 2.1.0-beta.1
    
    Creates pre-release v2.1.0-beta.1

.EXAMPLE
    .\scripts\git-release.ps1 2.2.0 -DryRun
    
    Simulates the release without making changes

.EXAMPLE
    .\scripts\git-release.ps1 2.1.1 -Force
    
    Creates release without confirmations

.NOTES
    File Name      : git-release.ps1
    Author         : IoT-DevSim Team
    Prerequisite   : PowerShell 5.1 or later, git, GitHub CLI (optional)
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Version,

    [Parameter()]
    [switch]$DryRun,

    [Parameter()]
    [switch]$Force,

    [Parameter()]
    [switch]$NoPush
)

# Error handling
$ErrorActionPreference = "Stop"

# Colors for output
$Colors = @{
    Success = "Green"
    Warning = "Yellow"
    Error = "Red"
    Info = "Cyan"
    Header = "Blue"
}

function Write-Header {
    Write-Host ""
    Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor $Colors.Header
    Write-Host "║         IoT-DevSim - Git Release Script                  ║" -ForegroundColor $Colors.Header
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor $Colors.Header
    Write-Host ""
}

function Write-Step {
    param([string]$Message)
    Write-Host "▶ $Message" -ForegroundColor White
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

function Test-SemanticVersion {
    param([string]$Version)
    
    $semverRegex = "^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$"
    return $Version -match $semverRegex
}

function Test-Prerequisites {
    Write-Step "Checking prerequisites..."
    
    # Check git
    $git = Get-Command git -ErrorAction SilentlyContinue
    if (-not $git) {
        Write-Error "Git is not installed"
        exit 1
    }
    
    # Check if in git repository
    $gitDir = git rev-parse --git-dir 2>$null
    if (-not $gitDir) {
        Write-Error "Not in a git repository"
        exit 1
    }
    
    # Check for uncommitted changes
    $status = git status --porcelain
    if ($status) {
        Write-Error "You have uncommitted changes"
        Write-Info "Please commit or stash your changes before releasing"
        git status -s
        exit 1
    }
    
    Write-Success "Prerequisites check passed"
}

function Get-LatestTag {
    $tag = git describe --tags --abbrev=0 2>$null
    if (-not $tag) {
        return "v0.0.0"
    }
    return $tag
}

function Generate-Changelog {
    param([string]$FromTag)
    
    Write-Step "Generating changelog..."
    
    # Get commits since last tag
    $features = git log "$FromTag..HEAD" --pretty=format:"%s" | Where-Object { $_ -match "^feat(\(.+\))?:" }
    $fixes = git log "$FromTag..HEAD" --pretty=format:"%s" | Where-Object { $_ -match "^fix(\(.+\))?:" }
    $others = git log "$FromTag..HEAD" --pretty=format:"%s" | Where-Object { $_ -notmatch "^(feat|fix)(\(.+\))?:" }
    
    $changelog = ""
    
    if ($features) {
        $changelog += "### Added`n"
        foreach ($line in $features) {
            if ($line) {
                $changelog += "- $line`n"
            }
        }
        $changelog += "`n"
    }
    
    if ($fixes) {
        $changelog += "### Fixed`n"
        foreach ($line in $fixes) {
            if ($line) {
                $changelog += "- $line`n"
            }
        }
        $changelog += "`n"
    }
    
    if ($others) {
        $changelog += "### Other Changes`n"
        foreach ($line in $others) {
            if ($line) {
                $changelog += "- $line`n"
            }
        }
        $changelog += "`n"
    }
    
    return $changelog
}

function Update-VersionFiles {
    param([string]$NewVersion)
    
    Write-Step "Updating version to $NewVersion..."
    
    if ($DryRun) {
        Write-Info "[DRY RUN] Would update version in:"
        Write-Info "  - VERSION file"
        Write-Info "  - frontend/package.json"
        Write-Info "  - api-service/pyproject.toml"
        Write-Info "  - transmission-service/pyproject.toml"
        return
    }
    
    # Update VERSION file
    $NewVersion | Set-Content $VersionFile -NoNewline
    
    # Update package.json
    if (Test-Path $PackageJson) {
        $content = Get-Content $PackageJson -Raw | ConvertFrom-Json
        $content.version = $NewVersion
        $content | ConvertTo-Json -Depth 10 | Set-Content $PackageJson
    }
    
    # Update pyproject.toml files
    foreach ($toml in @($ApiPyproject, $TransmissionPyproject)) {
        if (Test-Path $toml) {
            $content = Get-Content $toml -Raw
            $content = $content -replace '^(version = ")[0-9.]+(".*)$', "`${1}$NewVersion`$2"
            $content | Set-Content $toml -NoNewline
        }
    }
    
    Write-Success "Version updated to $NewVersion"
}

function Invoke-GitCommand {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )
    
    if ($DryRun) {
        Write-Info "[DRY RUN] git $Arguments"
    }
    else {
        & git $Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Git command failed: git $Arguments"
        }
    }
}

function New-Release {
    param([string]$NewVersion)
    
    $tag = "v$NewVersion"
    $latestTag = Get-LatestTag
    $changelog = Generate-Changelog -FromTag $latestTag
    
    if ($DryRun) {
        Write-Info "[DRY RUN] Changelog preview:"
        Write-Host $changelog
    }
    
    # Create release branch
    $releaseBranch = "release/$tag"
    Write-Step "Creating release branch: $releaseBranch"
    
    Invoke-GitCommand checkout develop
    Invoke-GitCommand pull origin develop 2>$null
    Invoke-GitCommand checkout -b $releaseBranch
    
    # Update versions
    Update-VersionFiles -NewVersion $NewVersion
    
    # Commit version changes
    Invoke-GitCommand add .
    Invoke-GitCommand commit -m "chore(release): prepare $tag`n`n## Version $NewVersion`n`n$changelog"
    
    # Merge to main
    Write-Step "Merging to main..."
    Invoke-GitCommand checkout main
    Invoke-GitCommand pull origin main 2>$null
    Invoke-GitCommand merge --no-ff $releaseBranch -m "Merge release $tag into main"
    
    # Create annotated tag
    Write-Step "Creating annotated tag..."
    $tagMessage = "Release $tag`n`n## Version $NewVersion`n`n$changelog`n`nFull changelog: CHANGELOG.md"
    
    if ($DryRun) {
        Write-Info "[DRY RUN] Would create tag $tag"
    }
    else {
        git tag -a $tag -m $tagMessage
        Write-Success "Tag $tag created"
    }
    
    # Merge to develop
    Write-Step "Merging to develop..."
    Invoke-GitCommand checkout develop
    Invoke-GitCommand merge --no-ff $releaseBranch -m "Merge release $tag into develop"
    
    # Delete release branch
    Invoke-GitCommand branch -d $releaseBranch
    
    Write-Success "Release $tag prepared successfully"
    
    # Push to remote
    if (-not $NoPush -and -not $DryRun) {
        Write-Step "Pushing to remote..."
        
        if (-not $Force) {
            $confirm = Read-Host "Push to origin? (y/N)"
            if ($confirm -ne 'y' -and $confirm -ne 'Y') {
                Write-Warning "Push cancelled. Manual push required:"
                Write-Info "  git push origin main develop --tags"
                return
            }
        }
        
        git push origin main
        git push origin develop
        git push origin --tags
        
        Write-Success "Pushed to origin"
        
        # Create GitHub Release
        $gh = Get-Command gh -ErrorAction SilentlyContinue
        if ($gh) {
            Write-Step "Creating GitHub Release..."
            
            $releaseNotes = [System.IO.Path]::GetTempFileName()
            "## Version $NewVersion`n`n$changelog" | Set-Content $releaseNotes
            
            $repo = git remote get-url origin 2>$null
            if ($repo -match "github.com[:/](.+?)(\.git)?$") {
                $repoName = $matches[1]
                
                gh release create $tag `
                    --title "IoT-DevSim $tag" `
                    --notes-file $releaseNotes
                
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "GitHub Release created: https://github.com/$repoName/releases/tag/$tag"
                }
                else {
                    Write-Warning "Could not create GitHub Release"
                }
            }
            
            Remove-Item $releaseNotes -ErrorAction SilentlyContinue
        }
        else {
            Write-Warning "GitHub CLI (gh) not installed. Create release manually."
        }
    }
    elseif ($DryRun) {
        Write-Info "[DRY RUN] Would push to origin:"
        Write-Info "  git push origin main develop --tags"
    }
    else {
        Write-Info "Skipping push (--NoPush specified). Manual push required:"
        Write-Info "  git push origin main develop --tags"
    }
}

# Main execution
Write-Header

if ($DryRun) {
    Write-Warning "DRY RUN MODE - No changes will be made"
    Write-Host ""
}

# Validate version format
if (-not (Test-SemanticVersion -Version $Version)) {
    Write-Error "Invalid version format: $Version"
    Write-Info "Expected format: MAJOR.MINOR.PATCH[-prerelease][+build]"
    Write-Info "Examples: 2.1.0, 2.1.0-beta.1, 2.0.0+build.123"
    exit 1
}

Write-Success "Version format valid: $Version"

# Check prerequisites
Test-Prerequisites

# Confirmation
if (-not $Force -and -not $DryRun) {
    Write-Warning "You are about to create release v$Version"
    $confirm = Read-Host "Continue? (y/N)"
    if ($confirm -ne 'y' -and $confirm -ne 'Y') {
        Write-Info "Release cancelled"
        exit 0
    }
}

# Create release
try {
    New-Release -NewVersion $Version
    
    Write-Host ""
    Write-Success "Release v$Version completed successfully! 🎉"
    Write-Host ""
    
    if (-not $DryRun) {
        Write-Info "Next steps:"
        Write-Info "  1. Verify the release on GitHub"
        Write-Info "  2. Deploy to staging"
        Write-Info "  3. Deploy to production"
        Write-Info "  4. Announce the release to the team"
    }
}
catch {
    Write-Error "Error during release: $_"
    exit 1
}
