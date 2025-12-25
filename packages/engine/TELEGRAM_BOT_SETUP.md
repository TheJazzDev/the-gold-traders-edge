# Telegram Bot Setup Guide

This guide will help you set up a Telegram bot to receive real-time trading signals from the Gold Trader's Edge signal engine.

## Overview

The Telegram bot subscriber sends formatted trading signals to a Telegram chat/channel whenever a new signal is generated. All signals are automatically pushed in real-time with:

- ✅ Signal direction (LONG/SHORT)
- 💰 Entry price, Stop Loss, Take Profit
- 📊 Risk/Reward metrics
- ⭐ Confidence indicators
- 📈 Strategy and timeframe information

## Prerequisites

- A Telegram account
- Access to Telegram (via mobile app or web)
- The Gold Trader's Edge signal engine installed

## Step 1: Create Your Telegram Bot

### 1.1 Message BotFather

1. Open Telegram and search for **@BotFather**
2. Start a chat with BotFather
3. Send the command: `/newbot`

### 1.2 Configure Your Bot

1. BotFather will ask for a **bot name** (display name)
   - Example: "Gold Signals Bot"

2. Then it will ask for a **username** (must be unique and end with 'bot')
   - Example: "gold_trader_signals_bot"

3. BotFather will reply with your **Bot Token**
   - Example: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
   - ⚠️ **KEEP THIS SECRET!** Anyone with this token can control your bot

### 1.3 Customize Your Bot (Optional)

You can enhance your bot with these commands to BotFather:

```
/setdescription - Add a description
/setabouttext - Add about text
/setuserpic - Upload a profile picture
/setcommands - Set bot commands
```

## Step 2: Get Your Chat ID

You need to tell the bot where to send messages. This can be:
- Your personal chat ID
- A group chat ID
- A channel ID

### Option A: Personal Chat (Recommended for Testing)

1. Search for **@userinfobot** on Telegram
2. Start a chat and send any message
3. The bot will reply with your **User ID**
   - Example: `1234567890`
4. This is your `TELEGRAM_CHAT_ID`

### Option B: Group Chat

1. Create a new group on Telegram
2. Add your bot to the group (search by @username)
3. Search for **@RawDataBot** on Telegram
4. Add @RawDataBot to your group
5. The bot will send a message with chat details
6. Look for `"id": -1001234567890` in the message
7. This is your `TELEGRAM_CHAT_ID` (including the minus sign!)

### Option C: Channel

1. Create a new channel on Telegram
2. Add your bot as an administrator
3. The channel ID can be found using @RawDataBot (add it as admin temporarily)
4. Or use the channel username directly: `@your_channel_username`

## Step 3: Configure Environment Variables

Add these environment variables to your system or `.env` file:

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
TELEGRAM_CHAT_ID="1234567890"
```

### Setting Environment Variables

**On Linux/macOS:**
```bash
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export TELEGRAM_CHAT_ID="your_chat_id_here"
```

**On Windows (CMD):**
```cmd
set TELEGRAM_BOT_TOKEN=your_bot_token_here
set TELEGRAM_CHAT_ID=your_chat_id_here
```

**On Windows (PowerShell):**
```powershell
$env:TELEGRAM_BOT_TOKEN="your_bot_token_here"
$env:TELEGRAM_CHAT_ID="your_chat_id_here"
```

**Using .env file (Recommended):**

Create or edit `.env` file in the `packages/engine` directory:

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=1234567890

# Other configuration...
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/gold_signals
```

## Step 4: Test Your Bot

### 4.1 Test the Telegram Subscriber

Run the test script to verify your bot configuration:

```bash
cd packages/engine
python src/signals/subscribers/telegram_subscriber.py
```

Expected output:
```
==================================================================
🧪 TESTING TELEGRAM SUBSCRIBER
==================================================================

1. Creating Telegram subscriber...
   ✅ TelegramSubscriber initialized: Chat ID 1234567890

2. Sending test message...
   ✅ Test message sent!

3. Creating test LONG signal...

4. Sending LONG signal to Telegram...
   📱 Signal sent to Telegram: LONG @ $2650.50
   ✅ LONG signal sent!

5. Creating test SHORT signal...

6. Sending SHORT signal to Telegram...
   📱 Signal sent to Telegram: SHORT @ $2650.50
   ✅ SHORT signal sent!

==================================================================
✅ TELEGRAM SUBSCRIBER TEST COMPLETE!
==================================================================

📱 Check your Telegram chat for the messages!
```

### 4.2 Check Your Telegram

You should receive messages in your Telegram chat:

1. A welcome message confirming the bot is connected
2. A sample LONG signal with full details
3. A sample SHORT signal with full details

## Step 5: Start the Signal Service

Once your bot is configured and tested, start the signal service:

```bash
cd packages/engine
python run_multi_timeframe_service.py
```

The service will:
- ✅ Monitor multiple timeframes (5m, 15m, 30m, 1h, 4h, 1d)
- ✅ Generate signals using profitable strategies
- ✅ Save signals to the database
- ✅ Send signals to your Telegram bot in real-time
- ✅ Log all activity to file and console

## Signal Message Format

When a signal is generated, you'll receive a formatted message like this:

```
🟢 NEW LONG SIGNAL 📈

Symbol: XAUUSD
Strategy: Momentum Equilibrium
Timeframe: 4H
Time: 2025-12-25 14:30 UTC

💰 TRADE DETAILS
├ Entry: $2650.50
├ Stop Loss: $2635.20
├ Take Profit: $2681.10

📊 RISK MANAGEMENT
├ Risk: 153.0 pips
├ Reward: 306.0 pips
├ R:R Ratio: 1:2.00
├ Confidence: 75% ⭐⭐⭐
```

## Troubleshooting

### Bot Not Sending Messages

**Check 1: Verify credentials**
```bash
echo $TELEGRAM_BOT_TOKEN
echo $TELEGRAM_CHAT_ID
```

**Check 2: Test bot manually**
```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": "<YOUR_CHAT_ID>", "text": "Test message"}'
```

**Check 3: Check logs**
```bash
tail -f multi_timeframe_service.log | grep -i telegram
```

### Common Errors

**Error: "Unauthorized"**
- Your bot token is invalid
- Create a new bot with @BotFather and update the token

**Error: "Chat not found"**
- Your chat ID is incorrect
- Verify the chat ID using @userinfobot
- For groups/channels, make sure the bot is added as a member/admin

**Error: "Forbidden: bot was blocked by the user"**
- You blocked the bot
- Unblock the bot in Telegram and restart the chat

**Error: "Bad Request: message is too long"**
- Signal message exceeds Telegram's limit (4096 characters)
- This shouldn't happen with standard signals

### Bot Working But No Messages

**Check 1: Is the service running?**
```bash
ps aux | grep run_multi_timeframe_service
```

**Check 2: Are signals being generated?**
- Check the database for recent signals
- Review the service logs for signal generation messages

**Check 3: Is Telegram subscriber enabled?**
- Check logs for "TelegramSubscriber initialized" message
- Verify environment variables are loaded

## Advanced Configuration

### Multiple Recipients

To send signals to multiple chats/channels:

1. Create multiple Telegram subscribers in the code
2. Or use a Telegram channel and add multiple members

### Custom Formatting

Edit `telegram_subscriber.py` line 108 (`_format_signal_message` method) to customize:
- Emoji usage
- Message structure
- Information displayed
- Formatting style

### Filtering Signals

Modify the subscriber to filter signals before sending:

```python
def __call__(self, signal):
    # Only send LONG signals with confidence > 70%
    if signal.direction == "LONG" and signal.confidence > 0.7:
        self.send_signal(signal)
```

### Rate Limiting

Telegram allows up to 30 messages per second. If you're hitting rate limits:

1. Add delays between messages
2. Batch multiple signals into one message
3. Use a message queue

## Production Deployment

### Railway/Heroku

Add environment variables in the platform dashboard:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

### Docker

Add to your `docker-compose.yml`:

```yaml
environment:
  - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
  - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
```

### Systemd Service (Linux)

Create `/etc/systemd/system/gold-signals.service`:

```ini
[Unit]
Description=Gold Trader's Edge Signal Service
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/the-gold-traders-edge/packages/engine
Environment="TELEGRAM_BOT_TOKEN=your_token"
Environment="TELEGRAM_CHAT_ID=your_chat_id"
ExecStart=/usr/bin/python3 run_multi_timeframe_service.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable gold-signals
sudo systemctl start gold-signals
sudo systemctl status gold-signals
```

## Security Best Practices

1. **Never commit bot tokens to Git**
   - Add `.env` to `.gitignore`
   - Use environment variables

2. **Restrict bot access**
   - Use a private chat/group
   - Don't share bot token
   - Revoke and regenerate token if exposed

3. **Monitor bot activity**
   - Check logs regularly
   - Set up alerts for failures

4. **Use separate bots for dev/prod**
   - Create different bots for testing and production
   - Prevents test signals mixing with real signals

## Future Enhancements

The Telegram bot will support additional features in future versions:

- 📊 **Subscription tiers** (free, premium)
  - Free: Limited signals per day
  - Premium: All signals + auto-trading

- 🤖 **Interactive commands**
  - `/signals` - Get recent signals
  - `/stats` - View performance statistics
  - `/settings` - Configure preferences

- 🔔 **Custom notifications**
  - Signal opened
  - Signal closed (TP/SL hit)
  - Performance updates

- 📈 **Rich media**
  - Chart images with entry/exit levels
  - Performance graphs
  - Trade history

## Support

If you encounter issues:

1. Check the logs: `multi_timeframe_service.log`
2. Review this documentation
3. Test the bot configuration manually
4. Open an issue on GitHub

## References

- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [BotFather Commands](https://core.telegram.org/bots/features#botfather)
- [Telegram Bot Best Practices](https://core.telegram.org/bots/tutorial)
