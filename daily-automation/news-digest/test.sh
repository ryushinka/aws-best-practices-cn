#!/bin/bash
set -e
FUNCTION_NAME="daily-news-digest"
REGION="us-west-2"

echo "🧪 Testing $FUNCTION_NAME..."
aws lambda invoke \
  --function-name $FUNCTION_NAME \
  --payload '{}' \
  --region $REGION \
  /tmp/news-output.json 2>&1

echo "📄 Result:"
cat /tmp/news-output.json
echo ""
