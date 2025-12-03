# AGENTS.md

## Build/Test Commands
- **Build**: `docker-compose up --build`
- **Run tests**: `./test_daemon.sh` (requires daemon running)
- **Single test**: Use specific curl commands from test_daemon.sh
- **Lint**: No formal linting configured - follow Python PEP 8

## Environment Variables
- **OPENROUTER_API_KEY**: Required for summary generation (OpenRouter API key)
- **SUMMARY_MODEL**: Default model for summaries (default: "x-ai/grok-4.1-fast:free")
- **ENABLE_SUMMARY**: Enable/disable summary generation (default: "true")
- **SUMMARY_TIMEOUT**: Summary generation timeout in seconds (default: 120)
- **MAX_RETRIES**: Maximum retry attempts for API calls (default: 3)
- **RETRY_DELAY**: Delay between retries in seconds (default: 2)

## Code Style Guidelines
- **Python**: PEP 8 formatting, 4-space indentation
- **Imports**: Standard library first, then third-party, then local (alphabetical within groups)
- **Types**: No type hints required, but use clear variable names
- **Naming**: snake_case for functions/variables, UPPER_CASE for constants
- **Error handling**: Use try/except blocks, log errors, return appropriate HTTP status codes
- **Logging**: Use the configured logger, include timestamps and context
- **Security**: Validate all inputs, use rate limiting, sanitize URLs
- **Docker**: Run as non-root user, use Alpine base image

## API Usage

### Summary Generation
The `/process` endpoint now supports automatic summary generation using OpenRouter:

**JSON Request Format:**
```json
{
  "url": "https://youtube.com/watch?v=...",
  "summary_model": "anthropic/claude-3-haiku",  // Optional
  "disable_summary": false  // Optional
}
```

**Text/Plain Request Format:**
```
Line 1: YouTube URL
Line 2: summary_model (optional)
Line 3: disable_summary (optional, true/false)
```

**Response Format:**
```json
{
  "status": "OK",  // or "PARTIAL_SUCCESS" if summary fails
  "subtitle_files": ["subtitles_123_video.srt"],
  "summary": {
    "content": "Brief overview...\n\n• Key topics...\n• Countries: USA...",
    "model_used": "x-ai/grok-4.1-fast:free",
    "retry_attempts": 1
  },
  "summary_error": "Failed after 3 retries: API rate limit exceeded"  // Only if summary fails
}
```

**HTTP Status Codes:**
- `200 OK`: Full success (subtitles + summary)
- `207 Multi-Status`: Partial success (subtitles only, summary failed)
- `400 Bad Request`: Invalid parameters
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Configuration or critical failures

### Summary Content Format
Summaries include:
1. Brief overview (2-3 sentences)
2. Detailed bullet points covering:
   - Key topics and themes
   - Countries mentioned
   - Cities mentioned
   - People mentioned
   - Brands mentioned