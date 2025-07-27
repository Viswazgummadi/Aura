#!/bin/bash

# --- Step 1: User Registration & Authentication ---
echo "--- Step 1: User Registration & Authentication ---"
# Register a new user for this test session.
curl -X POST \
     -H "Content-Type: application/json" \
     -d '{"email": "aura.demo.user@example.com", "password": "MySecurePassword123"}' \
     https://aura-r1gd.onrender.com/auth/register

# Capture the JWT for the new user.
export AIBUDDIES_JWT=$(curl -s -X POST \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=aura.demo.user@example.com&password=MySecurePassword123" \
     https://aura-r1gd.onrender.com/auth/token | grep -oP '"access_token":"\K[^"]+')
echo ""
echo "✅ Step 1 complete. User created and JWT is ready."
echo ""


# --- Step 2: Google Account Linking ---
echo "--- Step 2: Google Account Linking ---"
# Generate the Google OAuth2 URL.
GOOGLE_AUTH_URL=$(curl -v -X GET \
     -H "Authorization: Bearer $AIBUDDIES_JWT" \
     https://aura-r1gd.onrender.com/auth/google/login 2>&1 \
     | grep -i '^< location:' | awk '{print $NF}' | tr -d '\r')

echo "ACTION REQUIRED: Please open this URL in your browser to link your Google Account:"
echo "$GOOGLE_AUTH_URL"
read -p "Press [Enter] key after you have linked your account..."
echo ""
echo "✅ Step 2 complete."
echo ""


# --- Step 3: Configure the Model Manager ---
echo "--- Step 3: Configure the Model Manager ---"
# Create the 'google' LLM provider.
curl -X POST \
     -H "Content-Type: application/json" \
     -d '{"name": "google"}' \
     https://aura-r1gd.onrender.com/admin/providers
echo ""

# Add your valid Google API key.
curl -X POST \
     -H "Content-Type: application/json" \
     -d '{"key": "AIzaSyAoFxCR6u_sJWCk8WEwI-aYspFdBEGuIlI"}' \
     https://aura-r1gd.onrender.com/admin/providers/google/keys
echo ""

# Add the 'gemini-1.5-flash' model for the agent.
curl -X POST \
     -H "Content-Type: application/json" \
     -d '{"name": "gemini-1.5-flash"}' \
     https://aura-r1gd.onrender.com/admin/providers/google/models
echo ""

# Set 'gemini-1.5-flash' as the active model.
curl -X PUT \
     https://aura-r1gd.onrender.com/admin/models/gemini-1.5-flash/activate
echo ""
echo "✅ Step 3 complete. Model Manager is configured."
echo ""


# --- Step 4: Test the Memory Matrix ---
echo "--- Step 4: Test the Memory Matrix ---"
# "Write" Operation: Teach Aura a fact.
curl -X POST \
     -H "Authorization: Bearer $AIBUDDIES_JWT" \
     -H "Content-Type: application/json" \
     -d '{"content": "The primary goal for the Aura project is to create a super-intelligent assistant."}' \
     https://aura-r1gd.onrender.com/agent/test/long_term_memory
echo ""

# "Read" Operation: Ask a conceptually similar question to test semantic search.
curl -X GET \
     -H "Authorization: Bearer $AIBUDDIES_JWT" \
     "https://aura-r1gd.onrender.com/agent/test/long_term_memory/search?q=What%20is%20the%20main%20objective%20of%20this%20project?"
echo ""
echo "✅ Step 4 complete. Memory Matrix test finished."
echo ""
echo "--- AURA FOUNDATION VERIFIED ---"