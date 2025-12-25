#!/usr/bin/env python3
"""
Quick Telegram Bot Test Script

This script helps you verify your Telegram bot configuration.
Run this before starting the signal service.
"""

from dotenv import load_dotenv
load_dotenv()

import os
import sys

try:
    import requests
except ImportError:
    print("❌ Error: 'requests' library not found")
    print("Install with: pip install requests")
    sys.exit(1)


def test_bot_configuration():
    """Test Telegram bot configuration step by step."""

    print("\n" + "=" * 70)
    print("🤖 TELEGRAM BOT CONFIGURATION TEST")
    print("=" * 70)

    # Step 1: Check environment variables
    print("\n📋 Step 1: Checking environment variables...")
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env file")
        print("\n💡 Fix:")
        print("   1. Open packages/engine/.env")
        print("   2. Add: TELEGRAM_BOT_TOKEN=your_bot_token_here")
        return False

    if not chat_id:
        print("❌ TELEGRAM_CHAT_ID not found in .env file")
        print("\n💡 Fix:")
        print("   1. Open packages/engine/.env")
        print("   2. Add: TELEGRAM_CHAT_ID=your_chat_id_here")
        return False

    print(f"✅ Bot Token: {bot_token[:20]}...")
    print(f"✅ Chat ID: {chat_id}")

    # Step 2: Verify bot token
    print("\n📋 Step 2: Verifying bot token...")
    try:
        response = requests.get(
            f'https://api.telegram.org/bot{bot_token}/getMe',
            timeout=10
        )

        if response.status_code == 200:
            bot_info = response.json()['result']
            print(f"✅ Bot is valid!")
            print(f"   Username: @{bot_info['username']}")
            print(f"   Name: {bot_info['first_name']}")
            bot_username = bot_info['username']
        else:
            print(f"❌ Invalid bot token!")
            print(f"   Error: {response.text}")
            print("\n💡 Fix:")
            print("   1. Message @BotFather on Telegram")
            print("   2. Send /newbot and create a new bot")
            print("   3. Copy the new token to .env")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        print("   Check your internet connection")
        return False

    # Step 3: Try sending a message
    print("\n📋 Step 3: Sending test message to chat...")
    try:
        response = requests.post(
            f'https://api.telegram.org/bot{bot_token}/sendMessage',
            json={
                'chat_id': chat_id,
                'text': '🤖 <b>Gold Trader\'s Edge</b>\n\n✅ Bot configured successfully!\n\nYou will receive trading signals here.',
                'parse_mode': 'HTML'
            },
            timeout=10
        )

        if response.status_code == 200:
            print(f"✅ Message sent successfully!")
            print(f"   📱 Check your Telegram chat!")
            print("\n" + "=" * 70)
            print("🎉 SUCCESS! Your Telegram bot is ready!")
            print("=" * 70)
            print("\n🚀 Next step: Start the signal service")
            print("   cd packages/engine")
            print("   source venv/bin/activate")
            print("   python run_multi_timeframe_service.py")
            return True

        else:
            error_info = response.json()
            error_code = error_info.get('error_code')
            error_desc = error_info.get('description', '')

            print(f"❌ Failed to send message!")
            print(f"   Error Code: {error_code}")
            print(f"   Error: {error_desc}")

            if 'chat not found' in error_desc.lower():
                print("\n💡 Fix: You need to start a chat with your bot first!")
                print(f"   1. Open Telegram")
                print(f"   2. Search for: @{bot_username}")
                print(f"   3. Click on the bot")
                print(f"   4. Press the START button at the bottom")
                print(f"   5. Run this test script again")

            elif 'blocked' in error_desc.lower():
                print("\n💡 Fix: You blocked the bot!")
                print(f"   1. Open the chat with @{bot_username}")
                print(f"   2. Unblock the bot")
                print(f"   3. Press START")
                print(f"   4. Run this test script again")

            else:
                print("\n💡 Possible fixes:")
                print(f"   1. Verify your chat ID using @userinfobot")
                print(f"   2. Make sure you started a chat with @{bot_username}")
                print(f"   3. Check TELEGRAM_TROUBLESHOOTING.md for more help")

            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False

    print("\n" + "=" * 70)


if __name__ == "__main__":
    success = test_bot_configuration()
    sys.exit(0 if success else 1)
