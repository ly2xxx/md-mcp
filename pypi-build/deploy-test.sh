#!/bin/bash
# deploy-test.sh - Deploy md-mcp to TestPyPI
# Supports: --dry-run (show what would happen without uploading)
#           --yes (skip confirmation prompt for CI/CD)

# Get script directory and source config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

# Parse command line arguments
DRY_RUN=false
AUTO_YES=false

for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --yes)
            AUTO_YES=true
            shift
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Usage: $0 [--dry-run] [--yes]"
            exit 1
            ;;
    esac
done

# Display banner
if [ "$DRY_RUN" = true ]; then
    display_banner "TestPyPI Deployment [DRY RUN]" "$YELLOW"
else
    display_banner "TestPyPI Deployment" "$BLUE"
fi

# Load TestPyPI token
info "Loading TestPyPI token..."
TESTPYPI_TOKEN=$(load_token "TESTPYPI_TOKEN" "TestPyPI API token")

if [ -z "$TESTPYPI_TOKEN" ]; then
    error "No TestPyPI token provided"
    exit 1
fi

# Validate token format
if ! validate_token "$TESTPYPI_TOKEN"; then
    exit 1
fi

echo ""

# Run build script
info "Running build script..."
echo ""

if ! "$SCRIPT_DIR/build.sh"; then
    error "Build failed"
    exit 3
fi

# Get version
VERSION=$(get_version_from_toml)

echo ""
display_banner "Pre-Upload Summary" "$BLUE"
info "Package: md-mcp"
info "Version: $VERSION"
info "Target:  TestPyPI (https://test.pypi.org/)"

echo ""
info "Files to upload:"
ls -lh "$PROJECT_ROOT/dist/"

echo ""

# Confirmation (unless --yes flag is used)
if [ "$AUTO_YES" = false ] && [ "$DRY_RUN" = false ]; then
    read -p "Deploy to TestPyPI? [y/N] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        warning "Deployment cancelled by user"
        exit 5
    fi
    echo ""
fi

# Upload to TestPyPI
cd "$PROJECT_ROOT" || exit 1

if [ "$DRY_RUN" = true ]; then
    echo ""
    info "DRY RUN - Would execute:"
    echo "  TWINE_USERNAME=__token__ TWINE_PASSWORD=*** twine upload --repository testpypi dist/*"
    echo ""
    success "Dry run completed successfully!"
    echo ""
    info "To actually upload, run without --dry-run flag"
    exit 0
fi

info "Uploading to TestPyPI..."
echo ""

if TWINE_USERNAME=__token__ TWINE_PASSWORD="$TESTPYPI_TOKEN" twine upload --repository testpypi dist/*; then
    success "Upload successful!"

    # Log deployment
    log_deployment "test" "$VERSION" "SUCCESS"
else
    error "Upload failed"
    log_deployment "test" "$VERSION" "FAILED"
    exit 4
fi

echo ""
display_banner "Deployment Complete!" "$GREEN"

echo ""
info "Package uploaded to TestPyPI"
info "View at: https://test.pypi.org/project/md-mcp/$VERSION/"

echo ""
banner "Installation Instructions:"
echo ""
echo "To install from TestPyPI (for testing):"
echo ""
echo -e "${BLUE}pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ md-mcp${NC}"
echo ""

info "Note: The --extra-index-url allows pip to install dependencies from PyPI"

echo ""
info "To verify the installation, run:"
echo "  ./pypi-build/verify-install.sh test"

echo ""
success "TestPyPI deployment completed successfully!"
echo ""
