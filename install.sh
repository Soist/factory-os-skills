#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FACTORY_OS_DIR="${HOME}/factory-os"

# Color output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Configuring factory-os skills...${NC}"
echo ""

# Update factory-os project settings if exists
if [ -d "$FACTORY_OS_DIR" ]; then
    SETTINGS_FILE="$FACTORY_OS_DIR/.claude/settings.json"

    if [ ! -f "$SETTINGS_FILE" ]; then
        mkdir -p "$FACTORY_OS_DIR/.claude"
        echo "{}" > "$SETTINGS_FILE"
    fi

    # Add skillsDir to settings (using jq if available)
    if command -v jq &> /dev/null; then
        temp_file=$(mktemp)
        # Handle both empty and non-empty JSON files
        if [ "$(cat "$SETTINGS_FILE")" = "{}" ] || [ -z "$(grep skillsDir "$SETTINGS_FILE")" ]; then
            jq '.skillsDir = ["~/.claude/skills", "~/factory-os-skills/"]' "$SETTINGS_FILE" > "$temp_file"
        else
            jq '.skillsDir += ["~/factory-os-skills/"] | .skillsDir |= unique' "$SETTINGS_FILE" > "$temp_file"
        fi
        mv "$temp_file" "$SETTINGS_FILE"
        echo -e "${GREEN}✓ Updated $FACTORY_OS_DIR/.claude/settings.json${NC}"
    else
        echo -e "${YELLOW}⚠ jq not found, please manually add this to $SETTINGS_FILE:${NC}"
        echo '  {"skillsDir": ["~/.claude/skills", "~/factory-os-skills/"]}'
    fi
else
    echo -e "${YELLOW}⚠ factory-os not found at $FACTORY_OS_DIR${NC}"
fi

echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Start a new Claude Code session in factory-os"
echo "  2. Use /triage, /bug-fix, /api-audit, etc. to access these skills"
echo ""
echo "For feishu-* skills, set up credentials:"
echo "  mkdir -p ~/.config/feishu && chmod 700 ~/.config/feishu"
echo "  cat > ~/.config/feishu/secrets.env << 'EOF'"
echo "  FEISHU_ALERT_APP_ID=..."
echo "  FEISHU_ALERT_APP_SECRET=..."
echo "  EOF"
echo "  chmod 600 ~/.config/feishu/secrets.env"
