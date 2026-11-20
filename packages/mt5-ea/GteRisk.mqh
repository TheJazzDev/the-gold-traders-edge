//+------------------------------------------------------------------+
//| Sizing and the limits checked before any order.                  |
//+------------------------------------------------------------------+
#ifndef GTE_RISK_MQH
#define GTE_RISK_MQH

// Lots that lose `riskFraction` of the balance at the stop, rounded DOWN to
// the broker's step. Returns 0 with a reason when no safe size exists.
double GteLots(const string symbol, const ENUM_ORDER_TYPE type, const double price,
               const double stopLoss, const double riskFraction, string &reason)
  {
   double lossPerLot = 0.0;
   if(!OrderCalcProfit(type, symbol, 1.0, price, stopLoss, lossPerLot) || lossPerLot >= 0.0)
     {
      reason = "could not work out the loss per lot";
      return 0.0;
     }
   lossPerLot = -lossPerLot;

   double riskMoney = AccountInfoDouble(ACCOUNT_BALANCE) * riskFraction;
   double step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   double minLots = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double maxLots = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   if(step <= 0.0 || minLots <= 0.0)
     {
      reason = "broker gave no lot step";
      return 0.0;
     }

   double lots = MathFloor(riskMoney / lossPerLot / step + 1e-9) * step;
   if(lots < minLots)
     {
      reason = StringFormat("smallest lot %.2f would risk %.2f, over the %.2f allowed",
                            minLots, minLots * lossPerLot, riskMoney);
      return 0.0;
     }
   return NormalizeDouble(MathMin(lots, maxLots), 8);
  }

int GteOpenPositions(const string symbol = "")
  {
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;
      if(symbol == "" || PositionGetString(POSITION_SYMBOL) == symbol)
         count++;
     }
   return count;
  }

// Closed profit and loss of this EA's trades since the broker's midnight.
double GteClosedToday()
  {
   datetime now = TimeCurrent();
   if(!HistorySelect(now - (now % 86400), now + 60))
      return 0.0;
   double total = 0.0;
   for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
     {
      ulong deal = HistoryDealGetTicket(i);
      if(deal == 0 || HistoryDealGetInteger(deal, DEAL_MAGIC) != InpMagic)
         continue;
      total += HistoryDealGetDouble(deal, DEAL_PROFIT) + HistoryDealGetDouble(deal, DEAL_SWAP)
               + HistoryDealGetDouble(deal, DEAL_COMMISSION);
     }
   return total;
  }

// Empty string when a new position is allowed, else why not.
string GteLimitReached(const string symbol)
  {
   if(GteOpenPositions(symbol) > 0)
      return "a position is already open on " + symbol;
   if(GteOpenPositions() >= InpMaxPositions)
      return "maximum open positions reached";
   double dailyLimit = AccountInfoDouble(ACCOUNT_BALANCE) * InpMaxDailyLossPercent / 100.0;
   if(GteClosedToday() <= -dailyLimit)
      return "daily loss limit reached";
   return "";
  }

bool GteTradingAllowed()
  {
   return TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) && MQLInfoInteger(MQL_TRADE_ALLOWED)
          && AccountInfoInteger(ACCOUNT_TRADE_EXPERT) && AccountInfoInteger(ACCOUNT_TRADE_ALLOWED);
  }

#endif
