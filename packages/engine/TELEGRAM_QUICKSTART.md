# Telegram Bot Quick Start (5 Minutes)

Get real-time trading signals in your Telegram chat in 5 minutes!

## Step 1: Create Bot (2 minutes)

1. Open Telegram and message **@BotFather**
2. Send: `/newbot`
3. Choose a name: `Gold Signals Bot`
4. Choose username: `your_gold_signals_bot` (must end with 'bot')
5. Copy the **bot token** (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

## Step 2: Get Your Chat ID (1 minute)

1. Message **@userinfobot** on Telegram
2. Copy your **ID** (looks like `1234567890`)

## Step 3: Configure (1 minute)

Edit `.env` file in `packages/engine`:

```bash
TELEGRAM_BOT_TOKEN=paste_your_bot_token_here
TELEGRAM_CHAT_ID=paste_your_chat_id_here
```

Or set environment variables:

```bash
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

## Step 4: Test (30 seconds)

```bash
cd packages/engine
python src/signals/subscribers/telegram_subscriber.py
```

Check your Telegram - you should see test messages!

## Step 5: Start Service (30 seconds)

```bash
python run_multi_timeframe_service.py
```

**Done!** You'll now receive all trading signals in Telegram automatically.

## What You'll Receive

Every time a signal is generated:

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

**Not receiving messages?**

```bash
# Check environment variables
echo $TELEGRAM_BOT_TOKEN
echo $TELEGRAM_CHAT_ID

# Test bot manually
curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
  -H "Content-Type: application/json" \
  -d "{\"chat_id\": \"$TELEGRAM_CHAT_ID\", \"text\": \"Test\"}"
```

**Still not working?**
- Make sure you started a chat with your bot (search for it and press START)
- Verify the bot token is correct (check for typos)
- Verify the chat ID is correct

## Next Steps

- **Full Setup Guide**: See `TELEGRAM_BOT_SETUP.md` for advanced configuration
- **Multiple Recipients**: Create a Telegram group and add your bot
- **Customize**: Edit `src/signals/subscribers/telegram_subscriber.py`

## Support

Need help? Check the logs:

```bash
tail -f multi_timeframe_service.log | grep -i telegram
```
