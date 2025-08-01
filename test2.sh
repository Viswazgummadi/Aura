#!/bin/bash

# ==============================================================================
#           Project Aura - Interactive Demonstration & Test Suite
# ==============================================================================
# This script provides a step-by-step, highly verbose walkthrough of all
# major API features, including an interactive test for the Gmail watcher.
#
# REQUIREMENTS:
#   - `jq` for pretty-printing JSON.
#   - A valid JWT exported as $AIBUDDIES_JWT.
#   - Your FastAPI server and ngrok tunnel must be running.
#
# ==============================================================================

# --- Configuration & Helper Functions ---
BASE_URL="http://localhost:8000"

# Colors for better readability
BLUE='\033[1;34m'
GREEN='\033[1;32m'
RED='\033[1;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper to pause and wait for user input
function pause_for_user() {
    echo -e "\n${YELLOW}ACTION REQUIRED: $1${NC}"
    read -p "  Press [Enter] to continue..."
}

# Helper to print a major section header
function print_header() {
    echo -e "\n${BLUE}==============================================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}==============================================================================${NC}"
}

# --- Prerequisite Check ---
if [ -z "$AIBUDDIES_JWT" ]; then echo -e "${RED}❌ FATAL ERROR: AIBUDDIES_JWT is not set.${NC}"; exit 1; fi
if ! command -v jq &> /dev/null; then echo -e "${RED}❌ FATAL ERROR: jq is not installed.${NC}"; exit 1; fi

# --- Test Execution ---
print_header "🚀 STARTING AURA API INTERACTIVE DEMO 🚀"
pause_for_user "This script will now test all core tools."

# ------------------------------------------------------------------------------
# SECTION 1: TASK MANAGEMENT - A Live Story
# ------------------------------------------------------------------------------
print_header "SECTION 1: TESTING TASK MANAGEMENT"

echo -e "${YELLOW}Step 1.1: Let's check our initial list of tasks. It should be empty.${NC}"
curl -s -X GET -H "Authorization: Bearer $AIBUDDIES_JWT" "$BASE_URL/tasks" | jq .

echo -e "\n${YELLOW}Step 1.2: Now, let's create our first task: 'Build the agent core'.${NC}"
RESPONSE_JSON=$(curl -s -X POST -H "Authorization: Bearer $AIBUDDIES_JWT" -H "Content-Type: application/json" -d '{"description": "Build the agent core"}' "$BASE_URL/tasks")
echo "$RESPONSE_JSON" | jq .
TASK_ID_1=$(echo "$RESPONSE_JSON" | jq -r '.id')
if [ "$TASK_ID_1" == "null" ]; then echo -e "${RED}❌ FAILURE: Could not create task.${NC}"; exit 1; fi
echo -e "${GREEN}✅ Task created with ID: $TASK_ID_1${NC}"

echo -e "\n${YELLOW}Step 1.3: Let's check the list again. See? The new task is there.${NC}"
curl -s -X GET -H "Authorization: Bearer $AIBUDDIES_JWT" "$BASE_URL/tasks" | jq .

echo -e "\n${YELLOW}Step 1.4: Let's add a sub-task to it: 'Define agent tools'.${NC}"
RESPONSE_JSON=$(curl -s -X POST -H "Authorization: Bearer $AIBUDDIES_JWT" -H "Content-Type: application/json" -d '{"description": "Define agent tools", "parent_id": "'$TASK_ID_1'"}' "$BASE_URL/tasks")
echo "$RESPONSE_JSON" | jq .
SUB_TASK_ID=$(echo "$RESPONSE_JSON" | jq -r '.id')
if [ "$SUB_TASK_ID" == "null" ]; then echo -e "${RED}❌ FAILURE: Could not create sub-task.${NC}"; exit 1; fi
echo -e "${GREEN}✅ Sub-task created with ID: $SUB_TASK_ID${NC}"

echo -e "\n${YELLOW}Step 1.5: Now let's fetch the parent task to see the sub-task nested inside.${NC}"
curl -s -X GET -H "Authorization: Bearer $AIBUDDIES_JWT" "$BASE_URL/tasks/$TASK_ID_1" | jq .

echo -e "\n${YELLOW}Step 1.6: Great! Now, let's mark the sub-task as 'completed'. Watch the status change.${NC}"
curl -s -X PUT -H "Authorization: Bearer $AIBUDDIES_JWT" -H "Content-Type: application/json" -d '{"status": "completed"}' "$BASE_URL/tasks/$SUB_TASK_ID" | jq .

pause_for_user "Task management tools are working perfectly. Next, we'll test Notes."

# ------------------------------------------------------------------------------
# SECTION 2: NOTE & LINKING MANAGEMENT
# ------------------------------------------------------------------------------
print_header "SECTION 2: TESTING NOTES AND LINKING"

echo -e "${YELLOW}Step 2.1: Let's create a note about our agent research.${NC}"
RESPONSE_JSON=$(curl -s -X POST -H "Authorization: Bearer $AIBUDDIES_JWT" -H "Content-Type: application/json" -d '{"title": "Agent Research Notes", "content": "The agent needs a robust memory system."}' "$BASE_URL/notes/")
echo "$RESPONSE_JSON" | jq .
NOTE_ID=$(echo "$RESPONSE_JSON" | jq -r '.id')
if [ "$NOTE_ID" == "null" ]; then echo -e "${RED}❌ FAILURE: Could not create note.${NC}"; exit 1; fi
echo -e "${GREEN}✅ Note created with ID: $NOTE_ID${NC}"

echo -e "\n${YELLOW}Step 2.2: Now for the magic. Let's link this note to our main task.${NC}"
curl -s -X POST -H "Authorization: Bearer $AIBUDDIES_JWT" "$BASE_URL/notes/$NOTE_ID/link-task/$TASK_ID_1" | jq .

echo -e "\n${YELLOW}Step 2.3: To prove it worked, let's fetch the task again. It should now contain our note!${NC}"
curl -s -X GET -H "Authorization: Bearer $AIBUDDIES_JWT" "$BASE_URL/tasks/$TASK_ID_1" | jq .
echo -e "${GREEN}✅ Two-way linking confirmed!${NC}"

pause_for_user "Notes and linking tools are perfect. Now for the real-time Gmail test."

# ------------------------------------------------------------------------------
# SECTION 3: INTERACTIVE GMAIL WATCHER TEST
# ------------------------------------------------------------------------------
print_header "SECTION 3: INTERACTIVE GMAIL WATCHER TEST"

echo -e "${YELLOW}Step 3.1: First, we'll tell the server to start watching your inbox.${NC}"
curl -s -X POST -H "Authorization: Bearer $AIBUDDIES_JWT" "$BASE_URL/gmail/watch" | jq .
echo -e "${GREEN}✅ Watch command sent successfully.${NC}"

echo -e "\n${YELLOW}--------------------------- YOUR TURN! ---------------------------${NC}"
echo -e "${YELLOW}1. Go to your email client (e.g., Gmail, Outlook).${NC}"
echo -e "${YELLOW}2. Compose and SEND A NEW EMAIL to the account you linked with Aura.${NC}"
echo -e "${YELLOW}   Subject: 'Aura Real-Time Test'${NC}"
echo -e "${YELLOW}3. IMPORTANT: Watch your FastAPI server log. You should see the webhook fire!${NC}"
pause_for_user "Once you have SENT the email, come back here and press [Enter]."

echo -e "\n${YELLOW}Step 3.2: Awesome! Now, let's ask the server to list your latest unread emails.${NC}"
echo -e "${YELLOW}The email you just sent should appear at the top of this list.${NC}"
RESPONSE_JSON=$(curl -s -X GET -H "Authorization: Bearer $AIBUDDIES_JWT" "$BASE_URL/gmail/unread?max_results=5")
echo "$RESPONSE_JSON" | jq .
if [[ $(echo "$RESPONSE_JSON" | jq '.[0].subject') == *"Aura Real-Time Test"* ]]; then
    echo -e "${GREEN}✅ VICTORY! Your real-time notification pipeline is working perfectly!${NC}"
else
    echo -e "${RED}❌ Hmm, the new email wasn't found. Check the server logs for any errors during background processing.${NC}"
fi

pause_for_user "Real-time notifications are confirmed working. Let's clean up."

# ------------------------------------------------------------------------------
# SECTION 4: CLEANUP
# ------------------------------------------------------------------------------
print_header "SECTION 4: CLEANING UP TEST RESOURCES"

echo -e "${YELLOW}Step 4.1: Deleting the test tasks...${NC}"
curl -s -X DELETE -H "Authorization: Bearer $AIBUDDIES_JWT" "$BASE_URL/tasks/$TASK_ID_1"
echo -e "${GREEN}✅ Deletion request sent for task $TASK_ID_1.${NC}"

echo -e "\n${YELLOW}Step 4.2: Deleting the test note...${NC}"
curl -s -X DELETE -H "Authorization: Bearer $AIBUDDIES_JWT" "$BASE_URL/notes/$NOTE_ID"
echo -e "${GREEN}✅ Deletion request sent for note $NOTE_ID.${NC}"

echo -e "\n${YELLOW}Step 4.3: Stopping the Gmail Watch...${NC}"
curl -s -X POST -H "Authorization: Bearer $AIBUDDIES_JWT" "$BASE_URL/gmail/unwatch" | jq .
echo -e "${GREEN}✅ Unwatch request sent.${NC}"

print_header "🎉 ALL DEMOS COMPLETED SUCCESSFULLY 🎉"
echo -e "${GREEN}Your toolset is fully tested and ready for the agentic layer!${NC}"