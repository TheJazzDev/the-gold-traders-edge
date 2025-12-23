#!/usr/bin/env python3
"""
Test MetaAPI Connection
Quick script to deploy account and test connection
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_connection():
    """Test MetaAPI connection"""
    try:
        from metaapi_cloud_sdk import MetaApi

        token = os.getenv('METAAPI_TOKEN')
        account_id = os.getenv('METAAPI_ACCOUNT_ID')

        print(f"🔌 Connecting to MetaAPI...")
        print(f"Account ID: {account_id}")

        # Initialize API
        api = MetaApi(token)
        account = await api.metatrader_account_api.get_account(account_id)

        print(f"\n📊 Account Info:")
        print(f"Name: {account.name}")
        print(f"Login: {account.login}")
        print(f"Server: {account.server}")
        print(f"State: {account.state}")
        print(f"Connection Status: {account.connection_status}")

        # Deploy account if needed
        if account.state == 'UNDEPLOYED':
            print(f"\n🚀 Deploying account...")
            await account.deploy()
            print(f"✅ Account deployed!")
        else:
            print(f"\n✅ Account already deployed")

        # Wait for connection
        print(f"\n⏳ Waiting for connection...")
        await account.wait_connected()
        print(f"✅ Connected to broker!")

        # Get RPC connection
        print(f"\n🔗 Establishing RPC connection...")
        connection = account.get_rpc_connection()
        await connection.connect()
        await connection.wait_synchronized()
        print(f"✅ RPC connection established!")

        # Get account information
        print(f"\n💰 Account Details:")
        account_info = await connection.get_account_information()
        print(f"Balance: ${account_info['balance']:.2f}")
        print(f"Equity: ${account_info['equity']:.2f}")
        print(f"Margin: ${account_info['margin']:.2f}")
        print(f"Free Margin: ${account_info['freeMargin']:.2f}")
        print(f"Leverage: 1:{account_info['leverage']}")
        print(f"Currency: {account_info['currency']}")

        # Test getting XAUUSD symbol info
        print(f"\n📈 XAUUSD Symbol Info:")
        try:
            symbol_spec = await connection.get_symbol_specification('XAUUSD')
            symbol_price = await connection.get_symbol_price('XAUUSD')

            print(f"Current Bid: ${symbol_price['bid']:.2f}")
            print(f"Current Ask: ${symbol_price['ask']:.2f}")
            print(f"Contract Size: {symbol_spec['contractSize']}")
            print(f"Min Volume: {symbol_spec['minVolume']}")
            print(f"Max Volume: {symbol_spec['maxVolume']}")
            print(f"Volume Step: {symbol_spec['volumeStep']}")
        except Exception as e:
            print(f"❌ Error getting XAUUSD info: {e}")
            print(f"Note: Make sure XAUUSD is available on your broker")

        # Close connection
        connection.close()

        print(f"\n{'='*60}")
        print(f"✅ CONNECTION TEST SUCCESSFUL!")
        print(f"{'='*60}")
        print(f"\n🎯 Next Steps:")
        print(f"1. Run dry-run mode: python run_demo_trading.py --dry-run")
        print(f"2. If successful, run live demo: python run_demo_trading.py")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"\n❌ Connection test failed:")
        print(f"Error: {e}")
        print(f"\nTroubleshooting:")
        print(f"1. Check your .env file has correct METAAPI_TOKEN and METAAPI_ACCOUNT_ID")
        print(f"2. Verify your account exists in MetaAPI dashboard")
        print(f"3. Check internet connection")
        return False

    return True

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    exit(0 if success else 1)
