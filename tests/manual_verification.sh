#!/bin/bash
# Manual Verification Script for Phase 1 Operational Core

# Configuration
AGENT_URL="http://localhost:5001"
GUARDIAN_URL="http://localhost:5000"
API_KEY="test_secret_key" # As defined in .env

echo "--- PHASE 1 VERIFICATION START ---"

# 1. Test Real Execution (ls)
echo "1. Testing Real Command Execution (ls)..."
RESPONSE=$(curl -s -X POST $AGENT_URL/execute \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"task": "list files in current directory"}')
echo "Response: $RESPONSE"
if [[ $RESPONSE == *"status\":\"executed\""* && $RESPONSE == *"output\":\""* && $RESPONSE == *"ROADMAP.md"* ]]; then
  echo "✅ SUCCESS: Command executed and output captured."
else
  echo "❌ FAILURE: Real execution failed or output missing."
fi

echo -e "\n-----------------------------------\n"

# 2. Test Dual-Path Validation (Hex bypass)
echo "2. Testing Dual-Path Validation (Hex bypass)..."
# 'rm -rf /' in hex: 726d202d7266202f
BYPASS_CMD="echo 726d202d7266202f | xxd -r -p"
RESPONSE=$(curl -s -X POST $GUARDIAN_URL/validate \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"command\": \"$BYPASS_CMD\"}")
echo "Response: $RESPONSE"
if [[ $RESPONSE == *"approved\":false"* && $RESPONSE == *"Blocked (Normalized)"* ]]; then
  echo "✅ SUCCESS: Hex bypass blocked via Dual-Path validation."
else
  echo "❌ FAILURE: Hex bypass allowed or blocked incorrectly."
fi

echo -e "\n-----------------------------------\n"

# 3. Test Robust JSON Validation (Malformed)
echo "3. Testing Robust JSON Validation (Malformed)..."
RESPONSE=$(curl -s -i -W "%{http_code}" -X POST $GUARDIAN_URL/validate \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"invalid": json' 2>&1)
echo "Response: $RESPONSE"
if [[ $RESPONSE == *"400"* ]]; then
  echo "✅ SUCCESS: Malformed JSON handled gracefully (400 Bad Request)."
else
  echo "❌ FAILURE: Server crashed or returned wrong status code."
fi

echo -e "\n-----------------------------------\n"

# 4. Test Case-Insensitive Matching (SUDO)
echo "4. Testing Case-Insensitive Matching (SUDO)..."
RESPONSE=$(curl -s -X POST $GUARDIAN_URL/validate \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"command": "SUDO apt-get update"}')
echo "Response: $RESPONSE"
if [[ $RESPONSE == *"approved\":false"* && $RESPONSE == *"privilege_escalation"* ]]; then
  echo "✅ SUCCESS: Case-insensitive SUDO blocked."
else
  echo "❌ FAILURE: SUDO bypass allowed."
fi

echo -e "\n-----------------------------------\n"

# 5. Test /report functionality
echo "5. Testing /report logging..."
RESPONSE=$(curl -s -X POST $GUARDIAN_URL/report \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"task": "Manual Verification", "command": "test-report", "status": "reported"}')
echo "Response: $RESPONSE"
if [[ $RESPONSE == *"status\":\"logged\""* ]]; then
  echo "✅ SUCCESS: /report acknowledged. (Manual check needed in DB/UI or via logs)"
else
  echo "❌ FAILURE: /report endpoint non-functional."
fi

echo -e "\n--- PHASE 1 VERIFICATION END ---"
