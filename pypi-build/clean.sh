#!/bin/bash
# clean.sh - Clean build artifacts for netshare package

# Get script directory and source config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

# Display banner
display_banner "Clean Build Artifacts" "$BLUE"

# Change to project root
cd "$PROJECT_ROOT" || exit 1

# Clean artifacts
clean_build_artifacts

echo ""
success "Cleanup complete!"
echo ""
info "Removed directories:"
echo "  - dist/"
echo "  - build/"
echo "  - *.egg-info/"
echo "  - __pycache__/"
echo ""
