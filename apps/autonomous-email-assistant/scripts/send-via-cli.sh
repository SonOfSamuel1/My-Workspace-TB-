#!/bin/bash

# Send email via AWS CLI using raw email format

PREVIEW_FILE="../preview/eod-report-preview.html"
TO_EMAIL="${1:-terrance@goodportion.org}"
FROM_EMAIL="brandonhome.appdev@gmail.com"
SUBJECT="[TEST] Email Assistant - EOD Report Preview - Redesigned Email Output"

cd "$(dirname "$0")"

# Check if preview file exists
if [ ! -f "$PREVIEW_FILE" ]; then
  echo "Error: Preview file not found at $PREVIEW_FILE"
  exit 1
fi

echo "=== AWS SES Email Test ==="
echo "From: $FROM_EMAIL"
echo "To: $TO_EMAIL"
echo "Subject: $SUBJECT"
echo ""

# Create raw email with proper MIME headers
RAW_EMAIL_FILE="/tmp/ses-raw-email.txt"

cat > "$RAW_EMAIL_FILE" << RAWEOF
From: $FROM_EMAIL
To: $TO_EMAIL
Subject: $SUBJECT
MIME-Version: 1.0
Content-Type: text/html; charset=utf-8

$(cat "$PREVIEW_FILE")
RAWEOF

echo "Sending via AWS SES..."

# Send using raw email
RESULT=$(aws ses send-raw-email \
  --raw-message "Data=$(cat $RAW_EMAIL_FILE | base64)" \
  --region us-east-1 2>&1)

if [ $? -eq 0 ]; then
  echo ""
  echo "=== SUCCESS ==="
  echo "$RESULT"
  echo ""
  echo "Check your inbox at: $TO_EMAIL"
else
  echo ""
  echo "=== ERROR ==="
  echo "$RESULT"
fi

# Cleanup
rm -f "$RAW_EMAIL_FILE"
