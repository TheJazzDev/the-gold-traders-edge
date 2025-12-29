#!/bin/bash
# API Connection Test Script

echo "🔍 Testing API Connection..."
echo "================================"
echo ""

# Get API URL from environment or use default
API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}"

echo "📡 API URL: $API_URL"
echo ""

# Test health endpoint
echo "1️⃣  Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "$API_URL/health" 2>&1)
HEALTH_CODE=$(echo "$HEALTH_RESPONSE" | tail -n 1)
HEALTH_BODY=$(echo "$HEALTH_RESPONSE" | sed '$d')

if [ "$HEALTH_CODE" = "200" ]; then
    echo "   ✅ Health check passed"
    echo "   Response: $HEALTH_BODY"
else
    echo "   ❌ Health check failed (HTTP $HEALTH_CODE)"
    echo "   Response: $HEALTH_BODY"
fi
echo ""

# Test signals endpoint
echo "2️⃣  Testing signals endpoint..."
SIGNALS_RESPONSE=$(curl -s -w "\n%{http_code}" "$API_URL/v1/signals/history?limit=5" 2>&1)
SIGNALS_CODE=$(echo "$SIGNALS_RESPONSE" | tail -n 1)
SIGNALS_BODY=$(echo "$SIGNALS_RESPONSE" | sed '$d')

if [ "$SIGNALS_CODE" = "200" ]; then
    echo "   ✅ Signals endpoint working"
    # Parse signal count if jq is available
    if command -v jq &> /dev/null; then
        SIGNAL_COUNT=$(echo "$SIGNALS_BODY" | jq '.total // 0')
        echo "   Total signals in database: $SIGNAL_COUNT"
        echo ""
        echo "   Recent signals:"
        echo "$SIGNALS_BODY" | jq -r '.signals[]? | "      - [\(.timeframe)] \(.strategy_name) \(.direction) @ $\(.entry_price) (created: \(.created_at))"' | head -5
    else
        echo "   Response preview: ${SIGNALS_BODY:0:200}..."
    fi
else
    echo "   ❌ Signals endpoint failed (HTTP $SIGNALS_CODE)"
    echo "   Response: $SIGNALS_BODY"
fi
echo ""

# Test market status endpoint
echo "3️⃣  Testing market status endpoint..."
MARKET_RESPONSE=$(curl -s -w "\n%{http_code}" "$API_URL/v1/market/status" 2>&1)
MARKET_CODE=$(echo "$MARKET_RESPONSE" | tail -n 1)
MARKET_BODY=$(echo "$MARKET_RESPONSE" | sed '$d')

if [ "$MARKET_CODE" = "200" ]; then
    echo "   ✅ Market status endpoint working"
    if command -v jq &> /dev/null; then
        IS_OPEN=$(echo "$MARKET_BODY" | jq -r '.is_open')
        REASON=$(echo "$MARKET_BODY" | jq -r '.reason')
        if [ "$IS_OPEN" = "true" ]; then
            echo "   🟢 Market is OPEN"
        else
            echo "   🔴 Market is CLOSED"
        fi
        echo "   Reason: $REASON"
    else
        echo "   Response preview: ${MARKET_BODY:0:200}..."
    fi
else
    echo "   ❌ Market status endpoint failed (HTTP $MARKET_CODE)"
    echo "   Response: $MARKET_BODY"
fi
echo ""

# Summary
echo "================================"
echo "📊 Summary"
echo "================================"
echo ""

if [ "$HEALTH_CODE" = "200" ] && [ "$SIGNALS_CODE" = "200" ] && [ "$MARKET_CODE" = "200" ]; then
    echo "✅ All endpoints working correctly!"
    echo ""
    echo "If frontend still doesn't show data, check:"
    echo "   1. Browser console for errors (F12 > Console)"
    echo "   2. Network tab in browser (F12 > Network)"
    echo "   3. NEXT_PUBLIC_API_URL environment variable"
    echo "   4. CORS configuration in backend"
else
    echo "❌ Some endpoints failed. Check the errors above."
    echo ""
    echo "Common issues:"
    echo "   - API URL incorrect (check NEXT_PUBLIC_API_URL)"
    echo "   - Backend not running"
    echo "   - CORS not configured"
    echo "   - Firewall blocking requests"
fi
echo ""
