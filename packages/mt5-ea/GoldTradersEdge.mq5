//+------------------------------------------------------------------+
//| Gold Trader's Edge order EA.                                     |
//|                                                                  |
//| Asks the bot's API for new signals every few seconds, places     |
//| each one as a market order with its stop loss and take profit,   |
//| and reports fills and closes back. Attach it to ONE chart; the   |
//| chart's symbol does not matter.                                  |
//+------------------------------------------------------------------+
#property copyright "Gold Trader's Edge"
#property version   "1.00"
#property strict

input string InpApiUrl = "https://the-gold-traders-edge-production.up.railway.app"; // API address
input string InpApiKey = "";                // EA key (EA_API_KEY on the server)
input string InpSymbolSuffix = "";          // Added to symbol names, e.g. ".m"
input double InpMaxRiskPercent = 0.5;       // Hard ceiling on risk per trade, % of balance
input int    InpMaxPositions = 3;           // Most positions open at once
input double InpMaxDailyLossPercent = 1.5;  // Stop opening trades after this loss in a day, %
input int    InpSlippagePoints = 50;        // Most slippage accepted, in points
input int    InpPollSeconds = 5;            // How often to ask for orders
input long   InpMagic = 20261120;           // Marks this EA's trades
input bool   InpAllowLiveAccount = false;   // Must be true to trade a non-demo account
input string InpLabel = "";                 // Name of this terminal, e.g. "railway"

#include "GteHttp.mqh"
#include "GteState.mqh"
#include "GteRisk.mqh"
#include "GteOrders.mqh"
#include "GteReports.mqh"

string gteMode = "unknown";
string gteLastContact = "never";

int OnInit()
  {
   if(InpApiKey == "")
     {
      Alert("GTE: set the EA key in the EA's inputs");
      return INIT_PARAMETERS_INCORRECT;
     }
   if(AccountInfoInteger(ACCOUNT_TRADE_MODE) != ACCOUNT_TRADE_MODE_DEMO && !InpAllowLiveAccount)
     {
      Alert("GTE: this is not a demo account. Set InpAllowLiveAccount to true to trade it.");
      return INIT_PARAMETERS_INCORRECT;
     }
   EventSetTimer(MathMax(InpPollSeconds, 2));
   GteShowStatus();
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   Comment("");
  }

void OnTick()
  {
  }

void OnTimer()
  {
   GteSendReports();

   string json = "{\"terminal\":\"" + GteJsonText(InpLabel) + "\""
                 + ",\"account\":\"" + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)) + "\""
                 + ",\"server\":\"" + GteJsonText(AccountInfoString(ACCOUNT_SERVER)) + "\""
                 + ",\"balance\":" + GteNumber(AccountInfoDouble(ACCOUNT_BALANCE))
                 + ",\"equity\":" + GteNumber(AccountInfoDouble(ACCOUNT_EQUITY))
                 + ",\"open_positions\":" + IntegerToString(GteOpenPositions()) + "}";
   string response;
   int status = GtePost("/v1/ea/poll", json, response);
   if(status != 200)
     {
      gteMode = "no answer from the API (" + IntegerToString(status) + ")";
      GteShowStatus();
      return;
     }
   gteLastContact = TimeToString(TimeLocal(), TIME_DATE | TIME_SECONDS);

   if(!GteTradingAllowed())
     {
      gteMode = "Algo Trading is switched off in the terminal";
      GteShowStatus();
      return; // nothing is rejected: the signal is offered again until it is stale
     }
   GteHandlePoll(response, gteMode);
   GteShowStatus();
  }

void GteShowStatus()
  {
   Comment("Gold Trader's Edge EA\n",
           "Mode: ", gteMode, "\n",
           "Last contact: ", gteLastContact, "\n",
           "Open positions: ", GteOpenPositions(), "\n",
           "Closed today: ", DoubleToString(GteClosedToday(), 2));
  }
