#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEAM_SKILLS_DIR="${HOME}/team-skills"
SKILLS_SYMLINK_DIR="${HOME}/.claude/skills"
FACTORY_OS_DIR="${HOME}/factory-os"

# Color output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if team-skills exists
if [ ! -d "$TEAM_SKILLS_DIR" ]; then
    echo -e "${RED}✗ Error: ~/team-skills not found${NC}"
    echo ""
    echo "Please install team-skills first:"
    echo "  git clone git@github.com:lmanxue/team-skills.git ~/team-skills"
    echo "  ~/team-skills/install.sh"
    exit 1
fi

# Create symlinks directory if not exists
mkdir -p "$SKILLS_SYMLINK_DIR"

# List of skills for factory-os
SKILLS=(
    # Core (⭐⭐⭐)
    "triage"
    "bug-fix"
    "api-audit"
    "security-audit"
    "error-handling-audit"

    # Common (⭐⭐)
    "frontend-audit"
    "playwright-cli"
    "cleanup-followthrough"
    "post-change-audit"
    "fix-and-unify"
    "code-placement"
    "negative-code-audit"
    "implementation-path-audit"

    # Supplementary (⭐)
    "concept-diagram"
    "daily-recap"
    "feishu-read"
    "feishu-sync"
    "feishu-task-delivery"
    "feishu-todo-enrichment"
)

echo -e "${GREEN}Installing factory-os skills from team-skills...${NC}"
echo ""

# Create symlinks in repo
created_count=0
for skill in "${SKILLS[@]}"; do
    if [ ! -d "$TEAM_SKILLS_DIR/$skill" ]; then
        echo -e "${YELLOW}⚠ Skipping $skill (not found in team-skills)${NC}"
        continue
    fi

    # Create symlink in repo
    if [ -L "$SCRIPT_DIR/$skill" ] || [ -d "$SCRIPT_DIR/$skill" ]; then
        rm -rf "$SCRIPT_DIR/$skill"
    fi

    ln -s "$TEAM_SKILLS_DIR/$skill" "$SCRIPT_DIR/$skill"
    echo -e "${GREEN}✓ Linked $skill${NC}"
    ((created_count++))
done

echo ""
echo -e "${GREEN}Created $created_count skill symlinks${NC}"

# Update factory-os project settings if exists
if [ -d "$FACTORY_OS_DIR" ]; then
    SETTINGS_FILE="$FACTORY_OS_DIR/.claude/settings.json"

    if [ ! -f "$SETTINGS_FILE" ]; then
        mkdir -p "$FACTORY_OS_DIR/.claude"
        echo "{}" > "$SETTINGS_FILE"
    fi

    # Add skillsDir to settings (using jq if available, else sed)
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
fi

echo ""
echo -e "${GREEN}Installation complete!${NC}"
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
