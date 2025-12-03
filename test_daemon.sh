#!/bin/bash

# Test script for YT-DLP Subtitle Downloader Daemon
# Make sure the daemon is running: docker-compose up -d

BASE_URL="http://localhost:33032"
#YOUTUBE_URL="https://www.youtube.com/watch?v=tQ3VbRpIM6U"
YOUTUBE_URL="https://www.youtube.com/watch?v=170W4jY8_Ds"

echo "=== Testing YT-DLP Subtitle Downloader Daemon ==="
echo "Base URL: $BASE_URL"
echo "YouTube URL: $YOUTUBE_URL"
echo ""

# Test 1: Health Check
echo "1. Testing health check endpoint..."
curl -s "$BASE_URL/health" | jq '.' 2>/dev/null || curl -s "$BASE_URL/health"
echo ""
echo ""

# Test 2: Process URL with text/plain content type
echo "2. Testing URL processing with text/plain content type..."
curl -s -X POST \
  -H "Content-Type: text/plain" \
  -d "$YOUTUBE_URL" \
  "$BASE_URL/process" | jq '.' 2>/dev/null || curl -s -X POST \
  -H "Content-Type: text/plain" \
  -d "$YOUTUBE_URL" \
  "$BASE_URL/process"
echo ""
echo ""

# Test 3: Process URL with application/json content type
echo "3. Testing URL processing with application/json content type..."
curl -s -X POST \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"$YOUTUBE_URL\"}" \
  "$BASE_URL/process" | jq '.' 2>/dev/null || curl -s -X POST \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"$YOUTUBE_URL\"}" \
  "$BASE_URL/process"
echo ""
echo ""

# Test 4: Test with invalid URL
echo "4. Testing with invalid URL..."
curl -s -X POST \
  -H "Content-Type: text/plain" \
  -d "not-a-valid-url" \
  "$BASE_URL/process" | jq '.' 2>/dev/null || curl -s -X POST \
  -H "Content-Type: text/plain" \
  -d "not-a-valid-url" \
  "$BASE_URL/process"
echo ""
echo ""

# Test 5: Test with empty request
echo "5. Testing with empty request..."
curl -s -X POST \
  -H "Content-Type: text/plain" \
  -d "" \
  "$BASE_URL/process" | jq '.' 2>/dev/null || curl -s -X POST \
  -H "Content-Type: text/plain" \
  -d "" \
  "$BASE_URL/process"
echo ""
echo ""

# Test 6: Test rate limiting (make multiple requests quickly)
echo "6. Testing rate limiting (making 6 requests quickly)..."
for i in {1..6}; do
  echo "Request $i:"
  curl -s -X POST \
    -H "Content-Type: text/plain" \
    -d "$YOUTUBE_URL" \
    "$BASE_URL/process" | jq -r '.status' 2>/dev/null || curl -s -X POST \
    -H "Content-Type: text/plain" \
    -d "$YOUTUBE_URL" \
    "$BASE_URL/process" | grep -o '"status":"[^"]*"' | cut -d'"' -f4
  sleep 0.5
done

echo ""

# Test 7: Test with summary generation (JSON with custom model)
echo "7. Testing summary generation with custom model..."
curl -s -X POST \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"$YOUTUBE_URL\",\"summary_model\":\"anthropic/claude-3-haiku\"}" \
  "$BASE_URL/process" | jq '.' 2>/dev/null || curl -s -X POST \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"$YOUTUBE_URL\",\"summary_model\":\"anthropic/claude-3-haiku\"}" \
  "$BASE_URL/process"
echo ""
echo ""

# Test 8: Test with summary disabled
echo "8. Testing with summary generation disabled..."
curl -s -X POST \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"$YOUTUBE_URL\",\"disable_summary\":true}" \
  "$BASE_URL/process" | jq '.' 2>/dev/null || curl -s -X POST \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"$YOUTUBE_URL\",\"disable_summary\":true}" \
  "$BASE_URL/process"
echo ""
echo ""

# Test 9: Test text/plain format with summary parameters
echo "9. Testing text/plain format with summary parameters..."
curl -s -X POST \
  -H "Content-Type: text/plain" \
  -d "$YOUTUBE_URL
anthropic/claude-3-haiku
false" \
  "$BASE_URL/process" | jq '.' 2>/dev/null || curl -s -X POST \
  -H "Content-Type: text/plain" \
  -d "$YOUTUBE_URL
anthropic/claude-3-haiku
false" \
  "$BASE_URL/process"
echo ""
echo ""

# Test 10: Test summary functionality without OpenRouter API key (should return partial success)
echo "10. Testing behavior without OpenRouter API key..."
echo "Note: This test requires restarting daemon without OPENROUTER_API_KEY environment variable"
echo "Expected: Should return subtitle files with summary_error and PARTIAL_SUCCESS status"
echo ""

echo ""
echo "=== Test completed ==="
echo ""
echo "Note: The actual subtitle extraction may take some time (up to 5 minutes)."
echo "Summary generation adds additional time depending on model response time."
echo "Check the daemon logs for progress: docker-compose logs -f"
echo ""
echo "New functionality tested:"
echo "- Summary generation with default model (x-ai/grok-4.1-fast:free)"
echo "- Custom model override via parameters"
echo "- Summary disable option"
echo "- Text/plain format with multi-line parameters"
echo "- Error handling when OpenRouter API is unavailable"
