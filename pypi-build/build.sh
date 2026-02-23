#!/bin/bash
# build.sh - Build distribution packages for md-mcp

# Get script directory and source config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

# Display banner
display_banner "Build md-mcp Package" "$BLUE"

# Check prerequisites
if ! check_prerequisites; then
    error "Prerequisites check failed"
    exit 2
fi

echo ""

# Check required files
if ! check_required_files; then
    error "Required files check failed"
    exit 2
fi

echo ""

# Check version consistency
if ! check_version_consistency; then
    error "Version consistency check failed"
    exit 2
fi

echo ""

# Get version for display
VERSION=$(get_version_from_toml)
info "Building version: $VERSION"

echo ""

# Clean old artifacts
clean_build_artifacts

echo ""

# Change to project root
cd "$PROJECT_ROOT" || exit 1

# Build the package
info "Running: $PYTHON_CMD -m build"
echo ""

if $PYTHON_CMD -m build; then
    success "Build completed successfully"
else
    error "Build failed"
    exit 3
fi

echo ""

# Check the built packages with twine
info "Running: twine check dist/*"
echo ""

if twine check dist/*; then
    success "Twine check passed"
else
    error "Twine check failed"
    exit 3
fi

echo ""

# Display created artifacts
info "Build artifacts created:"
if [ -d "dist" ]; then
    ls -lh dist/
else
    error "dist/ directory not found"
    exit 3
fi

echo ""
success "Build completed successfully!"
echo ""
info "You can now upload these files to PyPI using:"
echo "  - ./pypi-build/deploy-test.sh  (for TestPyPI)"
echo "  - ./pypi-build/deploy-prod.sh  (for PyPI)"
echo ""
