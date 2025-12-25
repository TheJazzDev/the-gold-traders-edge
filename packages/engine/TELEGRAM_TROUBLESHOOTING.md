# Telegram Bot Troubleshooting

## Error: "Bad Request: chat not found"

This error occurs when the bot hasn't been activated by the user yet.

### Solution: Start a conversation with your bot

1. **Find your bot on Telegram:**
   - Open Telegram
   - Search for your bot by username (the one you created with @BotFather)
   - Example: If you named it `gold_signals_bot`, search for `@gold_signals_bot`

2. **Start the bot:**
   - Open the chat with your bot
   - Click the **START** button at the bottom (or send `/start`)
   - The bot should respond (or stay silent if no handlers are set up - that's OK!)

3. **Test again:**
   ```bash
   cd packages/engine
   source venv/bin/activate
   python src/signals/subscribers/telegram_subscriber.py
   ```

   You should now see:
   ```
   ✅ Test message sent!
   ```

### Alternative: Use a different Chat ID method

If the above doesn't work, get your chat ID using this method:

1. **Start a chat with your bot** (search for it and press START)

2. **Send any message to your bot** (e.g., "Hello")

3. **Check for messages via API:**
   ```bash
   curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```

4. **Look for your chat ID in the response:**
   ```json
   {
     "ok": true,
     "result": [
       {
         "update_id": 123456789,
         "message": {
           "message_id": 1,
           "from": {
             "id": 265602506,  <- This is your chat ID!
             "is_bot": false,
             "first_name": "Your Name"
           },
           "chat": {
             "id": 265602506,  <- This is your chat ID!
             "first_name": "Your Name",
             "type": "private"
           },
           "text": "Hello"
         }
       }
     ]
   }
   ```

5. **Update your .env file** with the correct chat ID if different

### Quick Test Script

Run this to verify your bot is working:

```bash
cd packages/engine
source venv/bin/activate

python3 << 'EOF'
from dotenv import load_dotenv
load_dotenv()
import os
import requests

bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

# Test 1: Get bot info
print("=" * 60)
print("TEST 1: Get Bot Info")
print("=" * 60)
response = requests.get(f'https://api.telegram.org/bot{bot_token}/getMe')
if response.status_code == 200:
    bot_info = response.json()['result']
    print(f"✅ Bot is valid!")
    print(f"   Username: @{bot_info['username']}")
    print(f"   Name: {bot_info['first_name']}")
else:
    print(f"❌ Bot token is invalid!")
    print(f"   Error: {response.text}")
    exit(1)

# Test 2: Send message
print("\n" + "=" * 60)
print("TEST 2: Send Message to Chat")
print("=" * 60)
response = requests.post(
    f'https://api.telegram.org/bot{bot_token}/sendMessage',
    json={'chat_id': chat_id, 'text': '🤖 Test from Gold Trader\'s Edge!'}
)
if response.status_code == 200:
    print(f"✅ Message sent successfully!")
    print(f"   Chat ID: {chat_id}")
    print(f"   Check your Telegram!")
else:
    print(f"❌ Failed to send message!")
    print(f"   Error: {response.json()}")
    print(f"\n💡 TIP: Make sure you:")
    print(f"   1. Started a chat with @{bot_info['username']}")
    print(f"   2. Pressed the START button")
    print(f"   3. Used the correct chat ID")

print("\n" + "=" * 60)
EOF
```

## Common Issues

### Issue 1: Bot token invalid
**Error:** `Unauthorized`

**Solution:**
- Get a new token from @BotFather: `/newbot`
- Update TELEGRAM_BOT_TOKEN in .env

### Issue 2: Chat not found
**Error:** `Bad Request: chat not found`

**Solution:**
- Start a conversation with your bot (search for @your_bot_username)
- Press the START button
- Send a message to the bot
- Verify chat ID using the getUpdates method above

### Issue 3: Bot was blocked
**Error:** `Forbidden: bot was blocked by the user`

**Solution:**
- Unblock the bot in Telegram
- Restart the conversation

### Issue 4: Wrong chat ID
**Error:** `Bad Request: chat not found`

**Solution:**
- Verify your chat ID using @userinfobot
- OR use the getUpdates method described above
- Make sure there are no extra spaces or characters

## Verification Checklist

Before running the signal service, verify:

- [ ] Bot created via @BotFather
- [ ] Bot token copied correctly to .env
- [ ] Started a chat with the bot on Telegram
- [ ] Pressed START button in the bot chat
- [ ] Chat ID verified using @userinfobot or getUpdates
- [ ] Chat ID copied correctly to .env (no spaces)
- [ ] Test script runs successfully
- [ ] Received test message in Telegram

## Still Having Issues?

1. **Check the .env file:**
   ```bash
   cat packages/engine/.env | grep TELEGRAM
   ```

2. **Verify environment variables are loaded:**
   ```bash
   cd packages/engine
   source venv/bin/activate
   python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('Token:', os.getenv('TELEGRAM_BOT_TOKEN')[:20], '...\nChat ID:', os.getenv('TELEGRAM_CHAT_ID'))"
   ```

3. **Check logs:**
   ```bash
   tail -f multi_timeframe_service.log | grep -i telegram
   ```

4. **Test with curl:**
   ```bash
   curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/sendMessage" \
     -H "Content-Type: application/json" \
     -d '{"chat_id": "<YOUR_CHAT_ID>", "text": "Test"}'
   ```

## Need Help?

Open an issue with:
- Error message
- Output of verification checklist
- Bot username
- Whether you can see the bot when searching on Telegram
