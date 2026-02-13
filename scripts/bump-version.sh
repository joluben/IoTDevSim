#!/bin/bash
#
# IoTDevSim - Version Bump Script
# Updates version across all project files
#
# Usage: ./scripts/bump-version.sh <version>
#   version: New version (e.g., 2.1.0)
#
# Examples:
#   ./scripts/bump-version.sh 2.1.0
#   ./scripts/bump-version.sh 2.1.0-beta.1
#

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VERSION=""

# Helper functions
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_step() { echo -e "${BOLD}▶ $1${NC}"; }

show_help() {
    cat << EOF
${BOLD}IoT-DevSim v2 - Version Bump Script${NC}

Updates version in:
  - VERSION file
  - frontend/package.json
  - api-service/pyproject.toml
  - transmission-service/pyproject.toml
  - docker-compose.yml (image tags)

${BOLD}Usage:${NC}
  $(basename "$0") <version>

${BOLD}Examples:${NC}
  $(basename "$0") 2.1.0
  $(basename "$0") 2.1.0-beta.1

EOF
}

# Validate semantic version
validate_version() {
    local version="$1"
    local semver_regex="^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$"
    
    if [[ ! "$version" =~ $semver_regex ]]; then
        print_error "Invalid version format: $version"
        print_info "Expected: MAJOR.MINOR.PATCH[-prerelease][+build]"
        exit 1
    fi
}

# Update VERSION file
update_version_file() {
    local version="$1"
    print_step "Updating VERSION file..."
    echo "$version" > "${PROJECT_ROOT}/VERSION"
    print_success "VERSION file updated"
}

# Update package.json
update_package_json() {
    local version="$1"
    local package_file="${PROJECT_ROOT}/frontend/package.json"
    
    if [[ -f "$package_file" ]]; then
        print_step "Updating frontend/package.json..."
        
        if command -v jq &> /dev/null; then
            jq --arg v "$version" '.version = $v' "$package_file" > tmp.json && mv tmp.json "$package_file"
            print_success "package.json updated"
        else
            # Fallback with sed
            if sed -i.bak "s/\"version\": \"[0-9.]*\"/\"version\": \"$version\"/" "$package_file" 2>/dev/null; then
                rm -f "${package_file}.bak"
                print_success "package.json updated (sed)"
            else
                print_warning "Could not update package.json (jq not installed)"
            fi
        fi
    fi
}

# Update pyproject.toml files
update_pyproject_toml() {
    local version="$1"
    
    for service in api-service transmission-service; do
        local toml_file="${PROJECT_ROOT}/${service}/pyproject.toml"
        
        if [[ -f "$toml_file" ]]; then
            print_step "Updating ${service}/pyproject.toml..."
            
            # Update version line
            if sed -i.bak "s/^version = \"[0-9.]*\"/version = \"$version\"/" "$toml_file" 2>/dev/null; then
                rm -f "${toml_file}.bak"
                print_success "${service}/pyproject.toml updated"
            else
                print_warning "Could not update ${service}/pyproject.toml"
            fi
        fi
    done
}

# Update docker-compose.yml (image tags)
update_docker_compose() {
    local version="$1"
    local compose_file="${PROJECT_ROOT}/docker-compose.yml"
    
    if [[ -f "$compose_file" ]]; then
        print_step "Updating docker-compose.yml image tags..."
        
        # Update image tags (format: image:tag or image:version)
        # This is a simple sed replacement - adjust as needed
        if grep -q "image:.*iot-devsim" "$compose_file" 2>/dev/null; then
            print_info "Docker image tags may need manual updating"
            print_info "  Current pattern: iot-devsim-<service>:<tag>"
            print_info "  Suggested: iot-devsim-<service>:v${version}"
        fi
    fi
}

# Verify all updates
verify_updates() {
    print_step "Verifying updates..."
    
    local all_good=true
    
    # Check VERSION file
    if [[ -f "${PROJECT_ROOT}/VERSION" ]]; then
        local current_version=$(cat "${PROJECT_ROOT}/VERSION")
        if [[ "$current_version" == "$VERSION" ]]; then
            print_success "VERSION file: $current_version"
        else
            print_error "VERSION file mismatch: $current_version"
            all_good=false
        fi
    fi
    
    # Check package.json
    local package_file="${PROJECT_ROOT}/frontend/package.json"
    if [[ -f "$package_file" ]] && command -v jq &> /dev/null; then
        local pkg_version=$(jq -r '.version' "$package_file")
        if [[ "$pkg_version" == "$VERSION" ]]; then
            print_success "frontend/package.json: $pkg_version"
        else
            print_error "frontend/package.json mismatch: $pkg_version"
            all_good=false
        fi
    fi
    
    if [[ "$all_good" == true ]]; then
        print_success "All version files updated successfully"
    else
        print_error "Some files were not updated correctly"
        exit 1
    fi
}

# Main
main() {
    echo -e "${BLUE}${BOLD}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║         IoT-DevSim v2 - Version Bump                     ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    # Parse args
    if [[ $# -eq 0 ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
        show_help
        exit 0
    fi
    
    VERSION="$1"
    
    # Validate version
    validate_version "$VERSION"
    
    print_info "Bumping version to: $VERSION"
    echo ""
    
    # Update all files
    update_version_file "$VERSION"
    update_package_json "$VERSION"
    update_pyproject_toml "$VERSION"
    update_docker_compose "$VERSION"
    
    echo ""
    verify_updates
    
    echo ""
    print_success "Version bump complete: $VERSION"
    print_info "Commit changes with: git add . && git commit -m 'chore(release): bump version to $VERSION'"
}

main "$@"
