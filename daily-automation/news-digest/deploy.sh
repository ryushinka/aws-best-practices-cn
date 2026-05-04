#!/bin/bash
set -e
FUNCTION_NAME="daily-news-digest"
REGION="us-west-2"

cd "$(dirname "$0")"
rm -f /tmp/daily-news.zip

# Package src + config into zip
cd src && zip -r /tmp/daily-news.zip . && cd ..
cd config && zip -r /tmp/daily-news.zip . && cd ..

# Update Lambda
aws lambda update-function-code \
  --function-name $FUNCTION_NAME \
  --zip-file fileb:///tmp/daily-news.zip \
  --region $REGION \
  --query '{FunctionName:FunctionName,LastModified:LastModified}' \
  --output table

echo "✅ Deployed $FUNCTION_NAME"
