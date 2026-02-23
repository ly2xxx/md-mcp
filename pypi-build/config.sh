#!/bin/bash
# config.sh - Shared configuration and functions for PyPI deployment scripts
# This file should be sourced by other scripts, not executed directly

# Color codes for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Repository URLs
TESTPYPI_REPO="https://test.pypi.org/legacy/"
PYPI_REPO="https://upload.pypi.org/legacy/"

# Script directory detection
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Detect the correct Python command (python3 or python)
detect_python_command() {
    # Try to find a working Python command
    # Validates that the command actually works (not Windows Store stub)

    # Try 'python' first (most common in venv and Windows)
    if command -v python &> /dev/null && python --version &> /dev/null 2>&1; then
        echo "python"
        return 0
    fi

    # Try 'python3' (Linux/macOS)
    if command -v python3 &> /dev/null && python3 --version &> /dev/null 2>&1; then
        echo "python3"
        return 0
    fi

    # No working Python found
    echo ""
    return 1
}

# Set the Python command to use
# If in a virtual environment, use 'python' directly (most reliable)
if [ -n "$VIRTUAL_ENV" ]; then
    PYTHON_CMD="python"
else
    PYTHON_CMD=$(detect_python_command)
fi

# Output functions with color coding
success() {
    echo -e "${GREEN}✓${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

banner() {
    echo -e "${BOLD}$1${NC}"
}

# Load token from environment variable, .env file, or interactive prompt
# Usage: load_token VAR_NAME "Display Name"
# Returns: token value
load_token() {
    local token_var=$1
    local token_name=$2

    # 1. Check environment variable (highest priority)
    if [ -n "${!token_var}" ]; then
        echo "${!token_var}"
        return 0
    fi

    # 2. Check .env file
    if [ -f "$SCRIPT_DIR/.env" ]; then
        source "$SCRIPT_DIR/.env"
        if [ -n "${!token_var}" ]; then
            echo "${!token_var}"
            return 0
        fi
    fi

    # 3. Interactive prompt (fallback)
    echo "" >&2
    warning "No token found in environment or .env file" >&2
    echo -e "${BLUE}ℹ${NC} Enter $token_name (input hidden):" >&2
    read -s token
    echo "" >&2
    echo "$token"
}

# Validate token format (should start with "pypi-")
# Usage: validate_token "token_value"
# Returns: 0 if valid, 1 if invalid
validate_token() {
    local token=$1

    if [ -z "$token" ]; then
        error "Token is empty"
        return 1
    fi

    if [[ ! "$token" =~ ^pypi- ]]; then
        error "Invalid token format (should start with 'pypi-')"
        return 1
    fi

    success "Token format is valid"
    return 0
}

# Extract version from pyproject.toml
# Returns: version string
get_version_from_toml() {
    grep '^version = ' "$PROJECT_ROOT/pyproject.toml" | sed 's/version = "\(.*\)"/\1/'
}

# Extract version from __init__.py
# Returns: version string
get_version_from_init() {
    grep '__version__ = ' "$PROJECT_ROOT/md_mcp/__init__.py" | sed 's/__version__ = "\(.*\)"/\1/'
}

# Check version consistency between pyproject.toml and __init__.py
# Returns: 0 if consistent, 2 if mismatch
check_version_consistency() {
    local toml_version=$(get_version_from_toml)
    local init_version=$(get_version_from_init)

    info "Checking version consistency..."
    echo "  pyproject.toml: $toml_version"
    echo "  __init__.py:    $init_version"

    if [ "$toml_version" != "$init_version" ]; then
        error "Version mismatch detected!"
        echo ""
        warning "Please update both files to the same version:"
        echo "  - $PROJECT_ROOT/pyproject.toml"
        echo "  - $PROJECT_ROOT/md_mcp/__init__.py"
        return 2
    fi

    success "Version is consistent: $toml_version"
    return 0
}

# Check if required prerequisites are installed
# Returns: 0 if all present, 2 if missing
check_prerequisites() {
    local missing=0

    info "Checking prerequisites..."

    # Check Python
    if [ -n "$PYTHON_CMD" ]; then
        local python_version=$($PYTHON_CMD --version 2>&1)
        success "Python: $python_version"
    else
        error "Python is not installed (tried python3 and python)"
        missing=1
    fi

    # Check build module
    if [ -n "$PYTHON_CMD" ] && $PYTHON_CMD -c "import build" 2> /dev/null; then
        success "Python 'build' module is installed"
    else
        error "Python 'build' module is not installed"
        echo "  Install with: pip install build"
        missing=1
    fi

    # Check twine
    if command -v twine &> /dev/null; then
        local twine_version=$(twine --version 2>&1 | head -n1)
        success "Twine: $twine_version"
    else
        error "Twine is not installed"
        echo "  Install with: pip install twine"
        missing=1
    fi

    if [ $missing -eq 1 ]; then
        return 2
    fi

    return 0
}

# Check if required files exist
# Returns: 0 if all present, 2 if missing
check_required_files() {
    local missing=0

    info "Checking required files..."

    local files=("pyproject.toml" "README.md" "LICENSE" "md_mcp/__init__.py")

    for file in "${files[@]}"; do
        if [ -f "$PROJECT_ROOT/$file" ]; then
            success "$file exists"
        else
            error "$file is missing"
            missing=1
        fi
    done

    if [ $missing -eq 1 ]; then
        return 2
    fi

    return 0
}

# Log deployment to file
# Usage: log_deployment "test|prod" "version" "status"
log_deployment() {
    local repo_type=$1
    local version=$2
    local status=$3

    local log_dir="$SCRIPT_DIR/logs"
    mkdir -p "$log_dir"

    local log_file
    if [ "$repo_type" = "test" ]; then
        log_file="$log_dir/test-deployments.log"
    else
        log_file="$log_dir/prod-deployments.log"
    fi

    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local hostname=$(hostname)
    local username=$(whoami)

    echo "$timestamp | v$version | $status | $username@$hostname | ${repo_type^^}PyPI" >> "$log_file"
}

# Clean build artifacts
# This is used by multiple scripts
clean_build_artifacts() {
    info "Cleaning old build artifacts..."

    cd "$PROJECT_ROOT" || return 1

    if [ -d "dist" ]; then
        rm -rf dist/
        success "Removed dist/"
    fi

    if [ -d "build" ]; then
        rm -rf build/
        success "Removed build/"
    fi

    if [ -d "md_mcp.egg-info" ]; then
        rm -rf md_mcp.egg-info/
        success "Removed md_mcp.egg-info/"
    fi

    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null

    success "Build artifacts cleaned"
}

# Display banner with box
display_banner() {
    local message=$1
    local color=$2

    local length=${#message}
    local border=$(printf 'â•%.0s' $(seq 1 $((length + 4))))

    echo ""
    echo -e "${color}â•”${border}â•—${NC}"
    echo -e "${color}â•‘  ${message}  â•‘${NC}"
    echo -e "${color}â•š${border}â•${NC}"
    echo ""
}

# Check git status and warn if uncommitted changes
check_git_status() {
    if ! git -C "$PROJECT_ROOT" rev-parse --git-dir > /dev/null 2>&1; then
        warning "Not a git repository"
        return 0
    fi

    if [ -n "$(git -C "$PROJECT_ROOT" status --porcelain)" ]; then
        warning "You have uncommitted changes in your repository"
        git -C "$PROJECT_ROOT" status --short
        echo ""
        return 1
    fi

    success "Git working directory is clean"
    return 0
}

# Check if git tag exists
# Usage: check_git_tag "v1.0.4"
# Returns: 0 if exists, 1 if not
check_git_tag() {
    local tag=$1

    if git -C "$PROJECT_ROOT" tag -l "$tag" | grep -q "$tag"; then
        return 0
    fi

    return 1
}

# Create git tag
# Usage: create_git_tag "v1.0.4"
# Returns: 0 if created, 1 if failed
create_git_tag() {
    local tag=$1

    if git -C "$PROJECT_ROOT" tag -a "$tag" -m "Release $tag"; then
        success "Created git tag: $tag"
        return 0
    else
        error "Failed to create git tag: $tag"
        return 1
    fi
}

# Offer to push git tag
# Usage: offer_push_tag "v1.0.4"
offer_push_tag() {
    local tag=$1

    echo ""
    read -p "Push tag $tag to origin? [y/N] " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if git -C "$PROJECT_ROOT" push origin "$tag"; then
            success "Pushed tag $tag to origin"
        else
            error "Failed to push tag $tag"
        fi
    else
        info "Tag not pushed. You can push it later with: git push origin $tag"
    fi
}
