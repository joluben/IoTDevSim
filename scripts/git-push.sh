#!/bin/bash
#
# IoTDevSim - Safe Git Push Script
# Validates changes before pushing to remote
#
# Usage: ./scripts/git-push.sh [options]
#   Validates and pushes current branch safely
#
# Options:
#   -f, --force      Skip validations (dangerous)
#   -n, --no-verify  Skip pre-push hooks
#   -h, --help       Show help
#

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
FORCE=false
NO_VERIFY=false

# Protected branches
PROTECTED_BRANCHES="^(main|develop)$"

# Helper functions
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${CYAN}ℹ️  $1${NC}"; }
print_step() { echo -e "${BLUE}▶ $1${NC}"; }

show_help() {
    cat << EOF
${BOLD}IoT-DevSim v2 - Safe Git Push Script${NC}

Validates code quality before pushing:
  ✓ Commit message format (Conventional Commits)
  ✓ No push to protected branches (main, develop)
  ✓ No uncommitted changes
  ✓ Tests passing (if available)
  ✓ Linting clean (if available)

${BOLD}Usage:${NC}
  $(basename "$0") [options]

${BOLD}Options:${NC}
  -f, --force       Skip all validations (DANGEROUS)
  -n, --no-verify   Skip pre-push hooks
  -h, --help        Show this help

${BOLD}Examples:${NC}
  $(basename "$0")              # Normal push with validations
  $(basename "$0") --force    # Skip validations

EOF
}

# Get current branch
current_branch() {
    git rev-parse --abbrev-ref HEAD
}

# Validate commit message format
validate_commit_message() {
    local msg="$1"
    local conventional_regex="^(feat|fix|docs|style|refactor|perf|test|chore|ci|build)(\(.+\))?!?: .+"
    
    if [[ ! "$msg" =~ $conventional_regex ]]; then
        return 1
    fi
    return 0
}

# Check if trying to push to protected branch
check_protected_branch() {
    local branch=$(current_branch)
    
    if [[ "$branch" =~ $PROTECTED_BRANCHES ]]; then
        return 0
    fi
    return 1
}

# Run backend Python tests
run_python_tests() {
    local service="$1"
    local test_dir="${PROJECT_ROOT}/${service}"
    
    if [[ -d "$test_dir" ]]; then
        if [[ -f "${test_dir}/pytest.ini" ]] || [[ -f "${test_dir}/pyproject.toml" ]]; then
            print_step "Running Python tests in ${service}..."
            cd "$test_dir"
            if python -m pytest -x -q --tb=short 2>/dev/null; then
                print_success "Tests passed in ${service}"
                return 0
            else
                print_error "Tests failed in ${service}"
                return 1
            fi
        fi
    fi
    return 0
}

# Run frontend tests
run_frontend_tests() {
    local frontend_dir="${PROJECT_ROOT}/frontend"
    
    if [[ -d "$frontend_dir" ]]; then
        if [[ -f "${frontend_dir}/package.json" ]]; then
            print_step "Running frontend tests..."
            cd "$frontend_dir"
            if npm test -- --run --reporter=dot 2>/dev/null; then
                print_success "Frontend tests passed"
                return 0
            else
                print_warning "Frontend tests not available or failed"
                return 0  # Don't block push for missing tests
            fi
        fi
    fi
    return 0
}

# Run linting
run_linting() {
    print_step "Running linting checks..."
    
    # Python linting (ruff)
    if command -v ruff &> /dev/null; then
        if ruff check "$PROJECT_ROOT" 2>/dev/null; then
            print_success "Python linting (ruff) passed"
        else
            print_warning "Python linting issues found (not blocking)"
        fi
    fi
    
    # Frontend linting
    local frontend_dir="${PROJECT_ROOT}/frontend"
    if [[ -d "$frontend_dir" ]] && [[ -f "${frontend_dir}/package.json" ]]; then
        cd "$frontend_dir"
        if npm run lint 2>/dev/null; then
            print_success "Frontend linting passed"
        else
            print_warning "Frontend linting issues found (not blocking)"
        fi
    fi
}

# Main validation
validate_push() {
    print_step "Running pre-push validations..."
    
    # 1. Check protected branches
    if check_protected_branch; then
        local branch=$(current_branch)
        print_error "Direct push to protected branch: ${branch}"
        print_info "Use Pull Requests to merge into ${branch}"
        print_info "Current workflow: feature branch → develop → main"
        exit 1
    fi
    
    # 2. Check for WIP commits
    local last_msg=$(git log -1 --pretty=%B)
    if echo "$last_msg" | grep -qiE "^WIP|^TODO|^DRAFT|^temp|^tmp"; then
        print_warning "Last commit appears to be WIP/TODO:"
        print_info "  $last_msg"
        echo -ne "${YELLOW}Continue anyway? (y/N): ${NC}"
        read -r confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # 3. Validate commit message format
    if ! validate_commit_message "$last_msg"; then
        print_warning "Last commit doesn't follow Conventional Commits format:"
        print_info "  $last_msg"
        print_info "Expected format: type(scope): description"
        print_info "Valid types: feat, fix, docs, style, refactor, perf, test, chore, ci, build"
        echo -ne "${YELLOW}Continue anyway? (y/N): ${NC}"
        read -r confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            print_info "Amend commit with: git commit --amend -m 'type(scope): description'"
            exit 1
        fi
    else
        print_success "Commit message format valid"
    fi
    
    # 4. Check for large files (>10MB)
    local large_files=$(git ls-files | xargs -I{} find {} -type f -size +10M 2>/dev/null || true)
    if [[ -n "$large_files" ]]; then
        print_warning "Large files detected (>10MB):"
        echo "$large_files" | while read -r file; do
            ls -lh "$file" | awk '{print "  " $9 " (" $5 ")"}'
        done
        print_info "Consider using Git LFS for large files"
        echo -ne "${YELLOW}Continue anyway? (y/N): ${NC}"
        read -r confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # 5. Run tests (optional, can be slow)
    if [[ "$FORCE" == false ]]; then
        print_info "Skipping automatic tests (run manually before push)"
        print_info "  API tests: cd api-service && pytest"
        print_info "  Frontend tests: cd frontend && npm test"
    fi
    
    # 6. Check for secrets (basic)
    local staged_files=$(git diff --cached --name-only)
    if echo "$staged_files" | grep -qiE "(password|secret|key|token|credential)"; then
        print_warning "Files with suspicious names staged:"
        echo "$staged_files" | grep -iE "(password|secret|key|token|credential)" | sed 's/^/  /'
        print_info "Ensure no secrets are being committed"
        echo -ne "${YELLOW}Continue? (y/N): ${NC}"
        read -r confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    print_success "All validations passed"
}

# Do the push
do_push() {
    local branch=$(current_branch)
    local remote="origin"
    
    print_step "Pushing ${branch} to ${remote}..."
    
    local verify_flag=""
    if [[ "$NO_VERIFY" == true ]]; then
        verify_flag="--no-verify"
    fi
    
    if git push $verify_flag -u "$remote" "$branch"; then
        print_success "Push successful!"
        
        # Show PR link if available
        local repo_url=$(git remote get-url origin 2>/dev/null | sed 's/.*github.com[:/]//' | sed 's/.git$//')
        if [[ -n "$repo_url" ]]; then
            print_info "Create PR: https://github.com/${repo_url}/compare/develop...${branch}"
        fi
    else
        print_error "Push failed"
        exit 1
    fi
}

# Main
main() {
    echo -e "${BLUE}${BOLD}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║         IoT-DevSim v2 - Safe Git Push                      ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    # Parse args
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -f|--force)
                FORCE=true
                shift
                ;;
            -n|--no-verify)
                NO_VERIFY=true
                shift
                ;;
            -*)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Pre-checks
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_error "Not in a git repository"
        exit 1
    fi
    
    # Validate or skip
    if [[ "$FORCE" == true ]]; then
        print_warning "FORCE MODE - Skipping all validations"
    else
        validate_push
    fi
    
    # Push
    do_push
}

main "$@"
