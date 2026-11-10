#!/usr/bin/env bash

# dev-logbook/scripts/log.sh
# Usage: ./log.sh "<title>" "<summary>"

TITLE="$1"
SUMMARY="$2"
LOGBOOK_PATH="LOGBOOK.md"

if [ -z "$TITLE" ] || [ -z "$SUMMARY" ]; then
    echo "Error: Title and Summary are required."
    exit 1
fi

DATE=$(date +"%Y-%m-%d %H:%M:%S")
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
ROLE="${DEV_ROLE:-platform_engineer}"

# Ensure LOGBOOK.md ends with a newline before appending
if [ -f "$LOGBOOK_PATH" ] && [ -n "$(tail -c 1 "$LOGBOOK_PATH")" ]; then
    echo "" >> "$LOGBOOK_PATH"
fi

cat <<EOF >> "$LOGBOOK_PATH"
# $TITLE
$DATE | $BRANCH ($ROLE)
$SUMMARY

---
EOF

echo "Success: Logbook updated."
