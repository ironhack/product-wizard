# Product Wizard - Slack Bot

A Slack bot that helps Ironhack Admissions Managers answer questions about educational programs using OpenAI's Assistant API.

## Context Issues and Debugging

### Known Issues

1. **Thread Context Problems**: The bot may lose context when users ask about "previous questions" in long conversations. This can happen due to:
   - Thread mapping not being properly updated when starting new threads
   - OpenAI thread context not being maintained correctly
   - Multiple course documents causing confusion in the assistant's responses

2. **Master Prompt Ambiguity**: When users ask about "the one before that" and multiple course variants exist, the assistant may get confused about which specific course or document to reference.

### Debugging

The bot now includes enhanced logging to help debug context issues:

- Thread mapping keys are logged for each message
- Conversation history is displayed for existing threads
- OpenAI thread creation and usage is tracked
- Error handling for failed API calls

To debug context issues:
1. Check the logs for thread mapping updates
2. Verify conversation history is being maintained
3. Look for any failed OpenAI API calls

### Recent Fixes

- Fixed thread mapping when starting new threads
- Added proper error handling for OpenAI API calls
- Enhanced logging for debugging conversation flow
- Added conversation history debugging function
- **CRITICAL FIX**: Added persistent thread mapping storage to prevent context loss during app restarts
- Added automatic cleanup of old thread mappings to prevent file size issues
