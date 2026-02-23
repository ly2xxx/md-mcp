#!/bin/bash
# verify-install.sh - Verify installation from TestPyPI or PyPI
# Usage: ./verify-install.sh [test|prod]

# Get script directory and source config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

# Display banner
display_banner "Verify Installation" "$BLUE"

# Check argument
if [ $# -eq 0 ]; then
    error "No repository specified"
    echo ""
    echo "Usage: $0 [test|prod]"
    echo ""
    echo "  test - Verify installation from TestPyPI"
    echo "  prod - Verify installation from PyPI"
    echo ""
    exit 1
fi

REPO_TYPE=$1

# Determine repository URL and name
case $REPO_TYPE in
    test)
        REPO_NAME="TestPyPI"
        PIP_ARGS="--index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/"
        ;;
    prod)
        REPO_NAME="PyPI"
        PIP_ARGS=""
        ;;
    *)
        error "Invalid repository type: $REPO_TYPE"
        echo "Must be 'test' or 'prod'"
        exit 1
        ;;
esac

info "Testing installation from $REPO_NAME"

# Create temporary venv
TIMESTAMP=$(date +%s)
VENV_DIR="/tmp/netshare-verify-$TIMESTAMP"

echo ""
info "Creating temporary virtual environment..."
info "Location: $VENV_DIR"

if $PYTHON_CMD -m venv "$VENV_DIR"; then
    success "Virtual environment created"
else
    error "Failed to create virtual environment"
    exit 2
fi

# Activate venv
source "$VENV_DIR/bin/activate"

echo ""
info "Installing netshare from $REPO_NAME..."
echo ""

# Install package
if pip install $PIP_ARGS netshare; then
    success "Installation completed"
else
    error "Installation failed"
    deactivate
    rm -rf "$VENV_DIR"
    exit 2
fi

echo ""
banner "Running Verification Tests"
echo ""

# Track test results
TESTS_PASSED=0
TESTS_FAILED=0

# Test 1: netshare --help
info "Test 1: Running 'netshare --help'"
if netshare --help > /dev/null 2>&1; then
    success "netshare command works"
    ((TESTS_PASSED++))
else
    error "netshare command failed"
    ((TESTS_FAILED++))
fi

echo ""

# Test 2: python -m netshare --help
info "Test 2: Running 'python -m netshare --help'"
if python -m netshare --help > /dev/null 2>&1; then
    success "python -m netshare works"
    ((TESTS_PASSED++))
else
    error "python -m netshare failed"
    ((TESTS_FAILED++))
fi

echo ""

# Test 3: Import and version check
info "Test 3: Checking version"
INSTALLED_VERSION=$(python -c "import netshare; print(netshare.__version__)" 2>/dev/null)

if [ -n "$INSTALLED_VERSION" ]; then
    success "Version imported successfully: $INSTALLED_VERSION"
    ((TESTS_PASSED++))

    # Compare with expected version if possible
    EXPECTED_VERSION=$(get_version_from_toml)
    if [ "$INSTALLED_VERSION" = "$EXPECTED_VERSION" ]; then
        success "Installed version matches expected version"
    else
        warning "Version mismatch: installed=$INSTALLED_VERSION, expected=$EXPECTED_VERSION"
        warning "This is normal if you haven't deployed the latest version yet"
    fi
else
    error "Failed to import version"
    ((TESTS_FAILED++))
fi

echo ""

# Test 4: Check dependencies
info "Test 4: Verifying dependencies"
DEPS_OK=true

if python -c "import flask" 2>/dev/null; then
    success "Flask is installed"
else
    error "Flask is not installed"
    DEPS_OK=false
fi

if python -c "import qrcode" 2>/dev/null; then
    success "qrcode is installed"
else
    error "qrcode is not installed"
    DEPS_OK=false
fi

if python -c "import PIL" 2>/dev/null; then
    success "Pillow is installed"
else
    error "Pillow is not installed"
    DEPS_OK=false
fi

if [ "$DEPS_OK" = true ]; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi

# Deactivate and cleanup
echo ""
info "Cleaning up..."
deactivate
rm -rf "$VENV_DIR"
success "Temporary environment removed"

# Summary
echo ""
display_banner "Verification Summary" "$BLUE"

echo ""
info "Tests passed: $TESTS_PASSED"
if [ $TESTS_FAILED -gt 0 ]; then
    error "Tests failed: $TESTS_FAILED"
else
    info "Tests failed: $TESTS_FAILED"
fi

echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    success "All tests passed!"
    echo ""
    info "Installation from $REPO_NAME is working correctly"
    exit 0
else
    error "Some tests failed"
    echo ""
    warning "Installation from $REPO_NAME may have issues"
    exit 1
fi
