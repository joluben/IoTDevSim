#!/bin/bash
#
# IoTDevSim - Git Release Script
# Automates the entire release process: version bump, changelog, tag, push
#
# Usage: ./scripts/git-release.sh <version> [options]
#   version: Semantic version (e.g., 2.1.0, 2.1.0-beta.1)
#   options:
#     -d, --dry-run    Simulate without executing
#     -f, --force      Skip confirmations
#     -n, --no-push    Don't push to remote (local only)
#     -h, --help       Show help
#
# Examples:
#   ./scripts/git-release.sh 2.1.0
#   ./scripts/git-release.sh 2.1.0-beta.1 --dry-run
#   ./scripts/git-release.sh 2.2.0 --force
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DRY_RUN=false
FORCE=false
NO_PUSH=false
VERSION=""

# Helper functions
print_header() {
    echo -e "${BLUE}${BOLD}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║         IoT-DevSim v2 - Git Release Script                 ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

print_step() {
    echo -e "${BOLD}▶ $1${NC}"
}

# Show help
show_help() {
    cat << EOF
${BOLD}IoT-DevSim v2 - Git Release Script${NC}

Automates the entire release process:
  1. Validates version format (SemVer)
  2. Updates version in all project files
  3. Generates changelog from commits
  4. Creates release branch
  5. Commits version changes
  6. Merges to main and develop
  7. Creates annotated git tag
  8. Pushes to remote
  9. Creates GitHub Release (optional)

${BOLD}Usage:${NC}
  $(basename "$0") <version> [options]

${BOLD}Arguments:${NC}
  version    Semantic version (e.g., 2.1.0, 2.1.0-beta.1)

${BOLD}Options:${NC}
  -d, --dry-run     Simulate without executing
  -f, --force       Skip all confirmations
  -n, --no-push     Don't push to remote (local only)
  -h, --help        Show this help message

${BOLD}Examples:${NC}
  $(basename "$0") 2.1.0              # Standard release
  $(basename "$0") 2.1.0-beta.1      # Pre-release
  $(basename "$0") 2.2.0 --dry-run   # Dry run simulation
  $(basename "$0") 2.1.1 --force     # Skip confirmations

${BOLD}Requirements:${NC}
  - Git repository with origin remote configured
  - GitHub CLI (gh) installed for release creation
  - Write access to main and develop branches
  - All changes committed before running

EOF
}

# Validate semantic version
validate_version() {
    local version="$1"
    # SemVer regex: MAJOR.MINOR.PATCH[-prerelease][+build]
    local semver_regex="^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$"
    
    if [[ ! "$version" =~ $semver_regex ]]; then
        print_error "Invalid version format: $version"
        print_info "Expected format: MAJOR.MINOR.PATCH[-prerelease][+build]"
        print_info "Examples: 2.1.0, 2.1.0-beta.1, 2.0.0+build.123"
        exit 1
    fi
    
    print_success "Version format valid: $version"
}

# Check prerequisites
check_prerequisites() {
    print_step "Checking prerequisites..."
    
    # Check git
    if ! command -v git &> /dev/null; then
        print_error "Git is not installed"
        exit 1
    fi
    
    # Check if in git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_error "Not in a git repository"
        exit 1
    fi
    
    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        print_error "You have uncommitted changes"
        print_info "Please commit or stash your changes before releasing"
        git status -s
        exit 1
    fi
    
    # Check remote
    if ! git remote get-url origin > /dev/null 2>&1; then
        print_warning "No 'origin' remote configured"
        print_info "Releases can only be created locally (use --no-push)"
    fi
    
    print_success "Prerequisites check passed"
}

# Get the latest tag
get_latest_tag() {
    git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0"
}

# Generate changelog section
generate_changelog() {
    local from_tag="$1"
    local to_ref="HEAD"
    
    print_step "Generating changelog..."
    
    # Get commits since last tag, categorized
    local features=$(git log "${from_tag}..${to_ref}" --pretty=format:"%s" | grep -E "^feat(\(.+\))?:" || true)
    local fixes=$(git log "${from_tag}..${to_ref}" --pretty=format:"%s" | grep -E "^fix(\(.+\))?:" || true)
    local other=$(git log "${from_tag}..${to_ref}" --pretty=format:"%s" | grep -vE "^(feat|fix)(\(.+\))?:" || true)
    
    local changelog=""
    
    if [[ -n "$features" ]]; then
        changelog+="### Added\n"
        while IFS= read -r line; do
            [[ -n "$line" ]] && changelog+="- ${line}\n"
        done <<< "$features"
        changelog+="\n"
    fi
    
    if [[ -n "$fixes" ]]; then
        changelog+="### Fixed\n"
        while IFS= read -r line; do
            [[ -n "$line" ]] && changelog+="- ${line}\n"
        done <<< "$fixes"
        changelog+="\n"
    fi
    
    if [[ -n "$other" ]]; then
        changelog+="### Other Changes\n"
        while IFS= read -r line; do
            [[ -n "$line" ]] && changelog+="- ${line}\n"
        done <<< "$other"
        changelog+="\n"
    fi
    
    echo -e "$changelog"
}

# Update version in files
update_versions() {
    local version="$1"
    
    print_step "Updating version to $version..."
    
    if [[ "$DRY_RUN" == true ]]; then
        print_info "[DRY RUN] Would update version in:"
        print_info "  - VERSION file"
        print_info "  - frontend/package.json"
        print_info "  - api-service/pyproject.toml"
        print_info "  - transmission-service/pyproject.toml"
        return
    fi
    
    # Update VERSION file
    echo "$version" > "${PROJECT_ROOT}/VERSION"
    
    # Update frontend package.json if exists
    if [[ -f "${PROJECT_ROOT}/frontend/package.json" ]]; then
        if command -v jq &> /dev/null; then
            jq --arg v "$version" '.version = $v' "${PROJECT_ROOT}/frontend/package.json" > tmp.json && mv tmp.json "${PROJECT_ROOT}/frontend/package.json"
        else
            print_warning "jq not installed, skipping frontend/package.json update"
        fi
    fi
    
    # Update Python pyproject.toml files (basic sed replacement)
    for toml in "${PROJECT_ROOT}/api-service/pyproject.toml" "${PROJECT_ROOT}/transmission-service/pyproject.toml"; do
        if [[ -f "$toml" ]]; then
            sed -i.bak "s/^version = \"[0-9.]*\"/version = \"$version\"/" "$toml" && rm -f "${toml}.bak"
        fi
    done
    
    print_success "Version updated to $version"
}

# Execute git commands with dry-run support
git_cmd() {
    if [[ "$DRY_RUN" == true ]]; then
        print_info "[DRY RUN] git $*"
    else
        git "$@"
    fi
}

# Create release
create_release() {
    local version="$1"
    local tag="v${version}"
    local latest_tag=$(get_latest_tag)
    
    print_step "Creating release ${tag}..."
    
    # Generate changelog
    local changelog=$(generate_changelog "$latest_tag")
    
    if [[ "$DRY_RUN" == true ]]; then
        print_info "[DRY RUN] Changelog preview:"
        echo -e "$changelog"
    fi
    
    # Create release branch
    local release_branch="release/${tag}"
    print_step "Creating release branch: ${release_branch}"
    
    git_cmd checkout develop
    git_cmd pull origin develop || print_warning "Could not pull from origin/develop"
    git_cmd checkout -b "$release_branch"
    
    # Update versions
    update_versions "$version"
    
    # Commit version changes
    git_cmd add .
    git_cmd commit -m "chore(release): prepare ${tag}

## Version ${version}

${changelog}"
    
    # Merge to main
    print_step "Merging to main..."
    git_cmd checkout main
    git_cmd pull origin main || print_warning "Could not pull from origin/main"
    git_cmd merge --no-ff "$release_branch" -m "Merge release ${tag} into main"
    
    # Create annotated tag
    print_step "Creating annotated tag..."
    local tag_message="Release ${tag}

## Version ${version}

${changelog}

Full changelog: https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]//' | sed 's/.git$//')/blob/main/CHANGELOG.md"
    
    if [[ "$DRY_RUN" == true ]]; then
        print_info "[DRY RUN] Would create tag ${tag}"
    else
        git tag -a "$tag" -m "$tag_message"
        print_success "Tag ${tag} created"
    fi
    
    # Merge to develop
    print_step "Merging to develop..."
    git_cmd checkout develop
    git_cmd merge --no-ff "$release_branch" -m "Merge release ${tag} into develop"
    
    # Delete release branch
    git_cmd branch -d "$release_branch"
    
    print_success "Release ${tag} prepared successfully"
    
    # Push to remote
    if [[ "$NO_PUSH" == false && "$DRY_RUN" == false ]]; then
        print_step "Pushing to remote..."
        
        if [[ "$FORCE" == false ]]; then
            echo -ne "${YELLOW}Push to origin? (y/N): ${NC}"
            read -r confirm
            if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
                print_warning "Push cancelled. Manual push required:"
                print_info "  git push origin main develop --tags"
                return
            fi
        fi
        
        git push origin main
        git push origin develop
        git push origin --tags
        print_success "Pushed to origin"
        
        # Create GitHub Release
        if command -v gh &> /dev/null; then
            print_step "Creating GitHub Release..."
            
            # Create release notes file
            local release_notes=$(mktemp)
            echo -e "## Version ${version}\n\n${changelog}" > "$release_notes"
            
            if gh release create "$tag" \
                --title "IoT-DevSim ${tag}" \
                --notes-file "$release_notes" \
                --draft=false; then
                print_success "GitHub Release created: https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]//' | sed 's/.git$//')/releases/tag/${tag}"
            else
                print_warning "Could not create GitHub Release. Create manually:"
                print_info "  gh release create ${tag} --title 'IoT-DevSim ${tag}' --generate-notes"
            fi
            
            rm -f "$release_notes"
        else
            print_warning "GitHub CLI (gh) not installed. Create release manually:"
            print_info "  https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]//' | sed 's/.git$//')/releases/new?tag=${tag}"
        fi
    elif [[ "$DRY_RUN" == true ]]; then
        print_info "[DRY RUN] Would push to origin:"
        print_info "  git push origin main develop --tags"
    else
        print_info "Skipping push (--no-push specified). Manual push required:"
        print_info "  git push origin main develop --tags"
    fi
}

# Main execution
main() {
    print_header
    
    # Parse arguments
    if [[ $# -eq 0 ]]; then
        show_help
        exit 0
    fi
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -d|--dry-run)
                DRY_RUN=true
                print_info "DRY RUN MODE - No changes will be made"
                shift
                ;;
            -f|--force)
                FORCE=true
                shift
                ;;
            -n|--no-push)
                NO_PUSH=true
                shift
                ;;
            -*)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
            *)
                if [[ -z "$VERSION" ]]; then
                    VERSION="$1"
                else
                    print_error "Multiple versions specified"
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    if [[ -z "$VERSION" ]]; then
        print_error "Version argument required"
        show_help
        exit 1
    fi
    
    # Validate version
    validate_version "$VERSION"
    
    # Check prerequisites
    check_prerequisites
    
    # Confirmation
    if [[ "$FORCE" == false && "$DRY_RUN" == false ]]; then
        echo ""
        print_warning "You are about to create release v${VERSION}"
        echo ""
        echo -ne "${YELLOW}Continue? (y/N): ${NC}"
        read -r confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            print_info "Release cancelled"
            exit 0
        fi
    fi
    
    # Create release
    create_release "$VERSION"
    
    echo ""
    print_success "Release v${VERSION} completed successfully! 🎉"
    echo ""
    print_info "Next steps:"
    print_info "  1. Verify the release on GitHub"
    print_info "  2. Deploy to staging: ./scripts/deploy.sh staging"
    print_info "  3. Deploy to production: ./scripts/deploy.sh production"
    print_info "  4. Announce the release to the team"
}

# Run main
main "$@"
