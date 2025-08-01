#!/bin/bash

# ==============================================================================
#                 Project Aura - Verbose API Test Suite
# ==============================================================================
# This script tests all major tool endpoints, printing every detail of the
# request and response for maximum clarity and debugging.
#
# REQUIREMENTS:
#   - `jq` must be installed for pretty-printing JSON.
#   - A valid JWT must be exported as the environment variable $AIBUDDIES_JWT.
#
# ==============================================================================

# --- Configuration ---
BASE_URL="http://localhost:8000"

# --- Helper Functions ---

# Check for prerequisites
if [ -z "$AIBUDDIES_JWT" ]; then
    echo "❌ FATAL ERROR: AIBUDDIES_JWT is not set. Please run your auth script first."
    exit 1
fi
if ! command -v jq &> /dev/null; then
    echo "❌ FATAL ERROR: `jq` is not installed. Please install it to run this script."
    exit 1
fi

# Function to print a clear, formatted header for each test section
print_header() {
    echo ""
    echo "=============================================================================="
    echo "  $1"
    echo "=============================================================================="
}

# --- Test Execution Starts Here ---

print_header "🚀 STARTING AURA API TEST SUITE 🚀"

# ------------------------------------------------------------------------------
# SECTION 1: TASK MANAGEMENT
# ------------------------------------------------------------------------------
print_header "SECTION 1: TESTING TASK MANAGEMENT"

echo "ACTION: Creating a new top-level task..."
RESPONSE_JSON=$(curl -s -X POST \
  -H "Authorization: Bearer $AIBUDDIES_JWT" \
  -H "Content-Type: application/json" \
  -d '{"description": "Plan the agent architecture"}' \
  "$BASE_URL/tasks")
echo "RESPONSE BODY:"
echo "$RESPONSE_JSON" | jq .
TASK_ID=$(echo "$RESPONSE_JSON" | jq -r '.id')
if [ "$TASK_ID" != "null" ]; then echo "✅ SUCCESS: Task created with ID: $TASK_ID"; else echo "❌ FAILURE: Could not create task."; exit 1; fi

echo -e "\nACTION: Creating a sub-task for task ID $TASK_ID..."
RESPONSE_JSON=$(curl -s -X POST \
  -H "Authorization: Bearer $AIBUDDIES_JWT" \
  -H "Content-Type: application/json" \
  -d '{"description": "Sub-task: Define tool specifications", "parent_id": "'$TASK_ID'"}' \
  "$BASE_URL/tasks")
echo "RESPONSE BODY:"
echo "$RESPONSE_JSON" | jq .
SUB_TASK_ID=$(echo "$RESPONSE_JSON" | jq -r '.id')
if [ "$SUB_TASK_ID" != "null" ]; then echo "✅ SUCCESS: Sub-task created with ID: $SUB_TASK_ID"; else echo "❌ FAILURE: Could not create sub-task."; exit 1; fi

echo -e "\nACTION: Listing all tasks (should show the parent task with nested sub-task)..."
RESPONSE_JSON=$(curl -s -X GET -H "Authorization: Bearer $AIBUDDIES_JWT" "$BASE_URL/tasks/$TASK_ID")
echo "RESPONSE BODY:"
echo "$RESPONSE_JSON" | jq .
if [[ $(echo "$RESPONSE_JSON" | jq -r '.sub_tasks[0].id') == "$SUB_TASK_ID" ]]; then echo "✅ SUCCESS: Sub-task is correctly nested."; else echo "❌ FAILURE: Sub-task not found in parent."; exit 1; fi

echo -e "\nACTION: Updating sub-task $SUB_TASK_ID to 'completed'..."
RESPONSE_JSON=$(curl -s -X PUT \
  -H "Authorization: Bearer $AIBUDDIES_JWT" \
  -H "Content-Type: application/json" \
  -d '{"status": "completed"}' \
  "$BASE_URL/tasks/$SUB_TASK_ID")
echo "RESPONSE BODY:"
echo "$RESPONSE_JSON" | jq .
if [[ $(echo "$RESPONSE_JSON" | jq -r '.status') == "completed" ]]; then echo "✅ SUCCESS: Sub-task status updated."; else echo "❌ FAILURE: Could not update sub-task."; exit 1; fi


# ------------------------------------------------------------------------------
# SECTION 2: NOTE MANAGEMENT
# ------------------------------------------------------------------------------
print_header "SECTION 2: TESTING NOTE MANAGEMENT"

echo "ACTION: Creating a new note..."
RESPONSE_JSON=$(curl -s -X POST \
  -H "Authorization: Bearer $AIBUDDIES_JWT" \
  -H "Content-Type: application/json" \
  -d '{"title": "Agent Research", "content": "Initial thoughts on agent memory and state."}' \
  "$BASE_URL/notes/")
echo "RESPONSE BODY:"
echo "$RESPONSE_JSON" | jq .
NOTE_ID=$(echo "$RESPONSE_JSON" | jq -r '.id')
if [ "$NOTE_ID" != "null" ]; then echo "✅ SUCCESS: Note created with ID: $NOTE_ID"; else echo "❌ FAILURE: Could not create note."; exit 1; fi

# ------------------------------------------------------------------------------
# SECTION 3: LINKING NOTES AND TASKS
# ------------------------------------------------------------------------------
print_header "SECTION 3: TESTING NOTE/TASK LINKING"

echo "ACTION: Linking Note $NOTE_ID to Task $TASK_ID..."
RESPONSE_JSON=$(curl -s -X POST -H "Authorization: Bearer $AIBUDDIES_JWT" "$BASE_URL/notes/$NOTE_ID/link-task/$TASK_ID")
echo "RESPONSE BODY:"
echo "$RESPONSE_JSON" | jq .
if [[ $(echo "$RESPONSE_JSON" | jq -r '.tasks[0].id') == "$TASK_ID" ]]; then echo "✅ SUCCESS: Link appears successful in note response."; else echo "❌ FAILURE: Task ID not found in note response."; exit 1; fi

echo -e "\nACTION: Verifying link by fetching Task $TASK_ID again..."
RESPONSE_JSON=$(curl -s -X GET -H "Authorization: Bearer $AIBUDDIES_JWT" "$BASE_URL/tasks/$TASK_ID")
echo "RESPONSE BODY:"
echo "$RESPONSE_JSON" | jq .
if [[ $(echo "$RESPONSE_JSON" | jq -r '.notes[0].id') == "$NOTE_ID" ]]; then echo "✅ SUCCESS: Two-way link confirmed. Note ID found in task."; else echo "❌ FAILURE: Note ID not found in task response."; exit 1; fi


# ------------------------------------------------------------------------------
# SECTION 4: GMAIL & CALENDAR TOOLS
# ------------------------------------------------------------------------------
print_header "SECTION 4: TESTING GMAIL & CALENDAR"

echo "ACTION: Initiating/Confirming Gmail Watch..."
RESPONSE_JSON=$(curl -s -X POST -H "Authorization: Bearer $AIBUDDIES_JWT" "$BASE_URL/gmail/watch")
echo "RESPONSE BODY:"
echo "$RESPONSE_JSON" | jq .
if [[ $(echo "$RESPONSE_JSON" | jq -r '.status') == "success" || $(echo "$RESPONSE_JSON" | jq -r '.status') == "already_active" ]]; then echo "✅ SUCCESS: Gmail Watch is active."; else echo "❌ FAILURE: Could not start Gmail Watch."; exit 1; fi

echo -e "\nACTION: Listing up to 3 unread emails..."
echo "(NOTE: This test just confirms the endpoint works. Content depends on your inbox.)"
RESPONSE_JSON=$(curl -s -X GET -H "Authorization: Bearer $AIBUDDIES_JWT" "$BASE_URL/gmail/unread?max_results=3")
echo "RESPONSE BODY:"
echo "$RESPONSE_JSON" | jq .
echo "✅ SUCCESS: List unread request sent successfully."

echo -e "\nACTION: Creating a new calendar event..."
START_TIME=$(date -u -d "+5 minutes" +"%Y-%m-%dT%H:%M:%SZ")
END_TIME=$(date -u -d "+35 minutes" +"%Y-%m-%dT%H:%M:%SZ")
EVENT_PAYLOAD="{\"summary\": \"Aura Test Event\", \"start_time_iso\": \"$START_TIME\", \"end_time_iso\": \"$END_TIME\", \"description\": \"Event created by automated test suite.\"}"
RESPONSE_JSON=$(curl -s -X POST \
  -H "Authorization: Bearer $AIBUDDIES_JWT" \
  -H "Content-Type: application/json" \
  -d "$EVENT_PAYLOAD" \
  "$BASE_URL/calendar/events")
echo "RESPONSE BODY:"
echo "$RESPONSE_JSON" | jq .
EVENT_ID=$(echo "$RESPONSE_JSON" | jq -r '.id')
if [[ "$EVENT_ID" != "null" && "$EVENT_ID" != "" ]]; then echo "✅ SUCCESS: Calendar event created with ID: $EVENT_ID"; else echo "❌ FAILURE: Could not create calendar event."; exit 1; fi


# ------------------------------------------------------------------------------
# SECTION 5: CLEANUP
# ------------------------------------------------------------------------------
print_header "SECTION 5: CLEANING UP TEST RESOURCES"

echo "ACTION: Deleting test task $TASK_ID (and its sub-tasks)..."
curl -s -X DELETE -H "Authorization: Bearer $AIBUDDIES_JWT" "$BASE_URL/tasks/$TASK_ID" > /dev/null
echo "✅ SUCCESS: Deletion request sent for task $TASK_ID."

echo -e "\nACTION: Deleting test note $NOTE_ID..."
curl -s -X DELETE -H "Authorization: Bearer $AIBUDDIES_JWT" "$BASE_URL/notes/$NOTE_ID" > /dev/null
echo "✅ SUCCESS: Deletion request sent for note $NOTE_ID."

echo -e "\nACTION: Deleting test calendar event $EVENT_ID..."
curl -s -X DELETE -H "Authorization: Bearer $AIBUDDIES_JWT" "$BASE_URL/calendar/events/$EVENT_ID" > /dev/null
echo "✅ SUCCESS: Deletion request sent for event $EVENT_ID."

echo -e "\nACTION: Stopping Gmail Watch..."
RESPONSE_JSON=$(curl -s -X POST -H "Authorization: Bearer $AIBUDDIES_JWT" "$BASE_URL/gmail/unwatch")
echo "RESPONSE BODY:"
echo "$RESPONSE_JSON" | jq .
if [[ $(echo "$RESPONSE_JSON" | jq -r '.status') == "success" ]]; then echo "✅ SUCCESS: Gmail watch stopped."; else echo "❌ FAILURE: Could not stop watch."; fi


print_header "🎉 ALL TESTS COMPLETED 🎉"
