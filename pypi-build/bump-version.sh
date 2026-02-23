#!/bin/bash
# bump-version.sh - Bump version in pyproject.toml and __init__.py
# Usage: ./bump-version.sh [major|minor|patch|X.Y.Z]

# Get script directory and source config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

# Display banner
display_banner "Bump Version" "$BLUE"

# Check if argument provided
if [ $# -eq 0 ]; then
    error "No version bump type specified"
    echo ""
    echo "Usage: $0 [major|minor|patch|X.Y.Z]"
    echo ""
    echo "Examples:"
    echo "  $0 major    # 1.0.4 → 2.0.0"
    echo "  $0 minor    # 1.0.4 → 1.1.0"
    echo "  $0 patch    # 1.0.4 → 1.0.5"
    echo "  $0 1.2.3    # Set explicit version"
    echo ""
    exit 1
fi

BUMP_TYPE=$1

# Get current version
CURRENT_VERSION=$(get_version_from_toml)

if [ -z "$CURRENT_VERSION" ]; then
    error "Could not read current version from pyproject.toml"
    exit 2
fi

info "Current version: $CURRENT_VERSION"

# Parse current version
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

# Calculate new version based on bump type
case $BUMP_TYPE in
    major)
        NEW_VERSION="$((MAJOR + 1)).0.0"
        ;;
    minor)
        NEW_VERSION="$MAJOR.$((MINOR + 1)).0"
        ;;
    patch)
        NEW_VERSION="$MAJOR.$MINOR.$((PATCH + 1))"
        ;;
    *)
        # Assume explicit version provided
        if [[ $BUMP_TYPE =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            NEW_VERSION=$BUMP_TYPE
        else
            error "Invalid version format: $BUMP_TYPE"
            echo "Must be 'major', 'minor', 'patch', or X.Y.Z format"
            exit 1
        fi
        ;;
esac

echo ""
info "New version: $NEW_VERSION"
echo ""

# Display changes
banner "Version Changes:"
echo ""
echo "  pyproject.toml:"
echo "    $CURRENT_VERSION → $NEW_VERSION"
echo ""
echo "  netshare/__init__.py:"
echo "    $CURRENT_VERSION → $NEW_VERSION"
echo ""

# Confirmation
read -p "Apply these changes? [y/N] " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    warning "Version bump cancelled"
    exit 5
fi

echo ""

# Update pyproject.toml
TOML_FILE="$PROJECT_ROOT/pyproject.toml"
info "Updating $TOML_FILE..."

if sed -i "s/^version = \"$CURRENT_VERSION\"/version = \"$NEW_VERSION\"/" "$TOML_FILE"; then
    success "Updated pyproject.toml"
else
    error "Failed to update pyproject.toml"
    exit 2
fi

# Update __init__.py
INIT_FILE="$PROJECT_ROOT/netshare/__init__.py"
info "Updating $INIT_FILE..."

if sed -i "s/__version__ = \"$CURRENT_VERSION\"/__version__ = \"$NEW_VERSION\"/" "$INIT_FILE"; then
    success "Updated __init__.py"
else
    error "Failed to update __init__.py"
    # Revert pyproject.toml change
    sed -i "s/^version = \"$NEW_VERSION\"/version = \"$CURRENT_VERSION\"/" "$TOML_FILE"
    error "Reverted pyproject.toml"
    exit 2
fi

echo ""

# Verify consistency
if ! check_version_consistency; then
    error "Version consistency check failed after update"
    exit 2
fi

echo ""
success "Version bumped successfully!"

echo ""
banner "Next Steps:"
echo ""
echo "1. Review the changes:"
echo "   git diff pyproject.toml netshare/__init__.py"
echo ""
echo "2. Commit the changes:"
echo "   git add pyproject.toml netshare/__init__.py"
echo "   git commit -m \"Bump version to $NEW_VERSION\""
echo ""
echo "3. Build and deploy:"
echo "   ./pypi-build/deploy-test.sh   # Test on TestPyPI first"
echo "   ./pypi-build/deploy-prod.sh   # Then deploy to PyPI"
echo ""
