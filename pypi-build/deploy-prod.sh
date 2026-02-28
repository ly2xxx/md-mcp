#!/bin/bash
# deploy-prod.sh - Deploy md-mcp to Production PyPI
# Supports: --dry-run (show what would happen without uploading)
#           --yes (skip confirmation prompts for CI/CD)
#
# WARNING: This deploys to production PyPI!

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

# Display banner with warning
if [ "$DRY_RUN" = true ]; then
    display_banner "PRODUCTION PyPI Deployment [DRY RUN]" "$YELLOW"
else
    display_banner "⚠️  PRODUCTION PyPI Deployment ⚠️" "$RED"
fi

# Check git status
check_git_status
GIT_STATUS_CODE=$?

if [ $GIT_STATUS_CODE -ne 0 ] && [ "$AUTO_YES" = false ]; then
    echo ""
    read -p "Continue despite uncommitted changes? [y/N] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        warning "Deployment cancelled"
        exit 5
    fi
fi

echo ""

# Load PyPI token
info "Loading PyPI token..."
PYPI_TOKEN=$(load_token "PYPI_TOKEN" "PyPI API token")

if [ -z "$PYPI_TOKEN" ]; then
    error "No PyPI token provided"
    exit 1
fi

# Validate token format
if ! validate_token "$PYPI_TOKEN"; then
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
TAG="v${VERSION}"

echo ""

# Check if git tag exists, create if not
info "Checking git tag: $TAG"

if check_git_tag "$TAG"; then
    success "Git tag $TAG already exists"
else
    warning "Git tag $TAG does not exist"

    if [ "$DRY_RUN" = false ]; then
        if [ "$AUTO_YES" = true ]; then
            info "Auto-creating git tag: $TAG"
            create_git_tag "$TAG"
        else
            read -p "Create git tag $TAG? [Y/n] " -n 1 -r
            echo ""
            if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                create_git_tag "$TAG"
            else
                warning "Continuing without creating git tag"
            fi
        fi
    else
        info "Would create git tag: $TAG"
    fi
fi

echo ""
display_banner "Pre-Upload Summary" "$RED"
warning "You are about to deploy to PRODUCTION PyPI!"
warning "This action cannot be undone!"

echo ""
info "Package: md-mcp"
info "Version: $VERSION"
info "Target:  PyPI (https://pypi.org/)"

echo ""
info "Files to upload:"
ls -lh "$PROJECT_ROOT/dist/"

echo ""

# Double confirmation (unless --yes flag is used)
if [ "$AUTO_YES" = false ] && [ "$DRY_RUN" = false ]; then
    # First confirmation
    read -p "Deploy version $VERSION to PRODUCTION PyPI? [y/N] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        warning "Deployment cancelled by user"
        exit 5
    fi

    echo ""

    # Second confirmation (must type "yes")
    echo -e "${RED}⚠️  FINAL CONFIRMATION ⚠️${NC}"
    read -p "Are you ABSOLUTELY sure? Type 'yes' to confirm: " confirmation

    if [ "$confirmation" != "yes" ]; then
        warning "Deployment cancelled (confirmation not received)"
        exit 5
    fi

    echo ""
fi

# Upload to PyPI
cd "$PROJECT_ROOT" || exit 1

if [ "$DRY_RUN" = true ]; then
    echo ""
    info "DRY RUN - Would execute:"
    echo "  TWINE_USERNAME=__token__ TWINE_PASSWORD=*** twine upload dist/*"
    echo ""
    success "Dry run completed successfully!"
    echo ""
    info "To actually upload, run without --dry-run flag"
    exit 0
fi

info "Uploading to PyPI..."
echo ""

if TWINE_USERNAME=__token__ TWINE_PASSWORD="$PYPI_TOKEN" twine upload dist/*; then
    success "Upload successful!"

    # Log deployment
    log_deployment "prod" "$VERSION" "SUCCESS"
else
    error "Upload failed"
    log_deployment "prod" "$VERSION" "FAILED"
    exit 4
fi

echo ""
display_banner "🎉 Deployment Complete! 🎉" "$GREEN"

echo ""
success "Package uploaded to PyPI"
info "View at: https://pypi.org/project/md-mcp/$VERSION/"

echo ""

# Offer to push git tag
if check_git_tag "$TAG"; then
    offer_push_tag "$TAG"
fi

echo ""
banner "Installation Instructions:"
echo ""
echo "Users can now install with:"
echo ""
echo -e "${GREEN}pip install md-mcp${NC}"
echo ""

info "To verify the installation, run:"
echo "  ./pypi-build/verify-install.sh prod"

echo ""
banner "Next Steps:"
echo "1. Verify the package page: https://pypi.org/project/md-mcp/"
echo "2. Test installation: ./pypi-build/verify-install.sh prod"
echo "3. Update README.md or documentation if needed"
echo "4. Announce the release!"

echo ""
success "Production PyPI deployment completed successfully!"
echo ""
