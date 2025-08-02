#!/bin/bash

# ==============================================================================
#                 Project Aura - Definitive Test Script
# ==============================================================================
# This script performs all steps to test the user-centric agent system:
# 1. Defines all credentials.
# 2. Sets up the system as an Admin.
# 3. Configures a personal agent as a Normal User.
# 4. Provides final instructions for a live agent chat test.
#
# It will exit immediately if any command fails.
# ==============================================================================
set -e

# --- Colors for better readability ---
BLUE='\033[1;34m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# --- Helper function to print headers ---
print_header() {
    echo -e "\n${BLUE}==============================================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}==============================================================================${NC}"
}

# --- 1. DEFINE CREDENTIALS ---
print_header "STEP 1: DEFINING TEST CREDENTIALS"
ADMIN_EMAIL="admin@aura.test"
ADMIN_PASS="admin_password_123"
USER_EMAIL="user@aura.test"
USER_PASS="user_password_123"
# IMPORTANT: Replace with a REAL, VALID Google AI Studio API Key
USER_API_KEY="AIzaSyBU30IKlP3f5_NrOvLqtWMQSx3-UZTV8M4"

echo "🔑 Admin User: $ADMIN_EMAIL"
echo "🔑 Normal User: $USER_EMAIL"
if [ "$USER_API_KEY" == "YOUR_REAL_GOOGLE_API_KEY_HERE" ]; then
    echo -e "${YELLOW}🚨 WARNING: Please edit this script and replace YOUR_REAL_GOOGLE_API_KEY_HERE with a valid key.${NC}"
    exit 1
fi
echo "------------------------------------------------------------------------------"

# --- 2. SERVER HEALTH CHECK ---
print_header "STEP 2: CHECKING IF SERVER IS RUNNING"
curl -s --fail http://localhost:8000/ > /dev/null
echo -e "${GREEN}✅ Server is running.${NC}"
echo "------------------------------------------------------------------------------"

# --- 3. ADMIN SETUP ---
print_header "STEP 3: CONFIGURING THE SYSTEM AS ADMIN"

echo -e "\n${YELLOW}3.1: Registering the Admin user...${NC}"
curl -s -X POST -H "Content-Type: application/json" -d "{\"email\": \"$ADMIN_EMAIL\", \"password\": \"$ADMIN_PASS\"}" http://localhost:8000/auth/register | jq .

echo -e "\n${YELLOW}3.2: Logging in as Admin to get ADMIN_JWT...${NC}"
ADMIN_JWT=$(curl -s -X POST -H "Content-Type: application/x-www-form-urlencoded" -d "username=$ADMIN_EMAIL&password=$ADMIN_PASS" http://localhost:8000/auth/token | jq -r '.access_token')
echo -e "${GREEN}✅ Admin JWT captured.${NC}"
echo -e "  Use this token for all admin operations: ${GREEN}$ADMIN_JWT${NC}"
# This is a manual database step to promote the user to admin.
echo -e "\n${YELLOW}3.3: Promoting Admin user via a temporary script...${NC}"
cat << EOF > make_admin.py
from src.database.database import SessionLocal
from src.database.models import User
db = SessionLocal()
user = db.query(User).filter(User.email == "$ADMIN_EMAIL").first()
if user:
    user.is_admin = True
    db.commit()
    print(f"✅ Success! User '{user.email}' has been promoted to an admin.")
else:
    print(f"❌ Error: User with email '$ADMIN_EMAIL' not found.")
db.close()
EOF
python make_admin.py
rm make_admin.py

echo -e "\n${YELLOW}3.4: Creating the 'google' provider...${NC}"
curl --fail-with-body -s -X POST http://localhost:8000/admin/providers -H "Authorization: Bearer $ADMIN_JWT" -H "Content-Type: application/json" -d '{"name": "google"}' | jq .

echo -e "\n${YELLOW}3.5: Adding 'gemini-1.5-flash-latest' as a globally available model...${NC}"
curl --fail-with-body -s -X POST http://localhost:8000/admin/providers/google/models -H "Authorization: Bearer $ADMIN_JWT" -H "Content-Type: application/json" -d '{"name": "gemini-1.5-flash-latest"}' | jq .
echo "------------------------------------------------------------------------------"

# --- 4. NORMAL USER SETUP ---
print_header "STEP 4: CONFIGURING A PERSONAL AGENT AS A NORMAL USER"

echo -e "\n${YELLOW}4.1: Registering the Normal user...${NC}"
curl -s -X POST -H "Content-Type: application/json" -d "{\"email\": \"$USER_EMAIL\", \"password\": \"$USER_PASS\"}" http://localhost:8000/auth/register | jq .

echo -e "\n${YELLOW}4.2: Logging in as Normal user to get USER_JWT...${NC}"
USER_JWT=$(curl -s -X POST -H "Content-Type: application/x-www-form-urlencoded" -d "username=$USER_EMAIL&password=$USER_PASS" http://localhost:8000/auth/token | jq -r '.access_token')
echo -e "${GREEN}✅ Normal User JWT captured.${NC}"

echo -e "\n${YELLOW}4.3: User adds their personal Google API Key...${NC}"
curl --fail-with-body -s -X POST http://localhost:8000/settings/keys -H "Authorization: Bearer $USER_JWT" -H "Content-Type: application/json" -d "{\"provider_name\": \"google\", \"key\": \"$USER_API_KEY\", \"nickname\": \"My Personal Gemini Key\"}" | jq .

echo -e "\n${YELLOW}4.4: User sets their active model to 'gemini-1.5-flash-latest'...${NC}"
curl --fail-with-body -s -X PUT http://localhost:8000/settings/models/gemini-1.5-flash-latest/activate -H "Authorization: Bearer $USER_JWT" | jq .
echo "------------------------------------------------------------------------------"


# --- 5. FINAL LIVE TEST ---
print_header "STEP 5: FINAL LIVE AGENT TEST"
echo -e "${YELLOW}The system is fully configured. Now for the final proof.${NC}"
echo -e "\n1. Open the file 'chat_client.py' in your editor."
echo -e "2. Replace 'YOUR_JWT_HERE' with the following token:"
echo -e "\n   ${GREEN}$USER_JWT${NC}\n"
echo -e "3. Save the 'chat_client.py' file."
echo -e "4. In a new terminal, run: ${YELLOW}python chat_client.py${NC}"
echo -e "5. After it connects, type a message like: ${YELLOW}Hello, what can you do?${NC}"
echo -e "\n${BLUE}WATCH THE SERVER LOGS! You should see the line:${NC}"
echo -e "${GREEN}   INFO: [User 2] Configured model 'gemini-1.5-flash-latest' using their API key ID ...${NC}"
echo -e "${BLUE}This confirms the entire user-centric flow is working perfectly.${NC}"

print_header "🎉 TUTORIAL COMPLETE 🎉"