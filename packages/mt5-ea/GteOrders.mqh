//+------------------------------------------------------------------+
//| Turn one ORDER line from the API into a market order with its    |
//| stop loss and take profit attached.                              |
//+------------------------------------------------------------------+
#ifndef GTE_ORDERS_MQH
#define GTE_ORDERS_MQH

#include <Trade\Trade.mqh>
#include "GteHttp.mqh"
#include "GteState.mqh"
#include "GteRisk.mqh"

CTrade gteTrade;

void GteReject(const long signalId, const string reason)
  {
   Print("GTE: signal ", signalId, " not traded: ", reason);
   string response;
   int status = GtePost("/v1/ea/orders/" + IntegerToString(signalId) + "/reject",
                        "{\"reason\":\"" + GteJsonText(reason) + "\"}", response);
   if(status == 200 || status == 404)
      GteMarkDone(signalId); // otherwise it is offered again and rejected again
  }

// A position this EA opened for the signal, found by its comment.
ulong GteFindPosition(const long signalId)
  {
   string comment = "GTE-" + IntegerToString(signalId);
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket != 0 && PositionGetInteger(POSITION_MAGIC) == InpMagic
         && PositionGetString(POSITION_COMMENT) == comment)
         return ticket;
     }
   return 0;
  }

void GteRemember(const long signalId, const ulong ticket, const double stopLoss, const double takeProfit)
  {
   GteSet("sl", signalId, stopLoss);
   GteSet("tp", signalId, takeProfit);
   GteSet("rep", signalId, 0.0);
   GteSet("pos", signalId, (double)ticket);
  }

// A position must never sit without its stop. If the broker dropped it,
// put it back, and close the position if that fails.
bool GteStopIsSet(const ulong ticket, const double stopLoss, const double takeProfit)
  {
   if(!PositionSelectByTicket(ticket))
      return true; // already closed, nothing left to protect
   if(PositionGetDouble(POSITION_SL) > 0.0)
      return true;
   if(gteTrade.PositionModify(ticket, stopLoss, takeProfit))
      return true;
   Print("GTE: could not set the stop on ", ticket, ", closing it");
   gteTrade.PositionClose(ticket);
   return false;
  }

void GtePlaceOrder(const long signalId, const string symbol, const string direction,
                   const double signalEntry, const double signalStop, const double signalTarget,
                   const double apiRisk)
  {
   if(GteHas("done", signalId) || GteHas("pos", signalId))
      return;

   if(GteHas("try", signalId))
     {
      // An earlier attempt was cut off. Adopt its position if there is one;
      // never send a second order for the same signal.
      ulong existing = GteFindPosition(signalId);
      if(existing != 0 && PositionSelectByTicket(existing))
         GteRemember(signalId, existing, PositionGetDouble(POSITION_SL), PositionGetDouble(POSITION_TP));
      else
         GteReject(signalId, "an earlier attempt was interrupted");
      return;
     }

   string brokerSymbol = symbol + InpSymbolSuffix;
   if(!SymbolSelect(brokerSymbol, true))
     { GteReject(signalId, "symbol " + brokerSymbol + " not found at the broker"); return; }
   if(SymbolInfoInteger(brokerSymbol, SYMBOL_TRADE_MODE) != SYMBOL_TRADE_MODE_FULL)
     { GteReject(signalId, "trading is not open on " + brokerSymbol); return; }

   string limit = GteLimitReached(brokerSymbol);
   if(limit != "")
     { GteReject(signalId, limit); return; }

   MqlTick tick;
   if(!SymbolInfoTick(brokerSymbol, tick) || tick.ask <= 0.0 || tick.bid <= 0.0)
      return; // no price yet; the API offers the signal again until it is stale

   bool isLong = (direction == "LONG");
   if(!isLong && direction != "SHORT")
     { GteReject(signalId, "unknown direction " + direction); return; }

   // The signal's levels come from another price feed. Keep its stop and
   // target distances and move them to where this broker is trading.
   int digits = (int)SymbolInfoInteger(brokerSymbol, SYMBOL_DIGITS);
   double point = SymbolInfoDouble(brokerSymbol, SYMBOL_POINT);
   double price = isLong ? tick.ask : tick.bid;
   double shift = price - signalEntry;
   double stopLoss = NormalizeDouble(signalStop + shift, digits);
   double takeProfit = NormalizeDouble(signalTarget + shift, digits);

   bool levelsMakeSense = isLong ? (stopLoss < price && takeProfit > price)
                                 : (stopLoss > price && takeProfit < price);
   if(!levelsMakeSense || stopLoss <= 0.0 || takeProfit <= 0.0)
     { GteReject(signalId, "stop and target are on the wrong side of the price"); return; }

   double minDistance = SymbolInfoInteger(brokerSymbol, SYMBOL_TRADE_STOPS_LEVEL) * point;
   if(MathAbs(price - stopLoss) < minDistance || MathAbs(takeProfit - price) < minDistance)
     { GteReject(signalId, "stop or target is closer than the broker allows"); return; }

   ENUM_ORDER_TYPE type = isLong ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double risk = MathMin(apiRisk, InpMaxRiskPercent / 100.0);
   string reason = "";
   double lots = GteLots(brokerSymbol, type, price, stopLoss, risk, reason);
   if(lots <= 0.0)
     { GteReject(signalId, reason); return; }

   double margin = 0.0;
   if(!OrderCalcMargin(type, brokerSymbol, lots, price, margin)
      || margin > AccountInfoDouble(ACCOUNT_MARGIN_FREE) * 0.5)
     { GteReject(signalId, "not enough free margin"); return; }

   gteTrade.SetExpertMagicNumber(InpMagic);
   gteTrade.SetDeviationInPoints(InpSlippagePoints);
   gteTrade.SetTypeFillingBySymbol(brokerSymbol);
   string comment = "GTE-" + IntegerToString(signalId);

   GteSet("try", signalId, (double)TimeCurrent());
   bool sent = isLong ? gteTrade.Buy(lots, brokerSymbol, 0.0, stopLoss, takeProfit, comment)
                      : gteTrade.Sell(lots, brokerSymbol, 0.0, stopLoss, takeProfit, comment);
   uint retcode = gteTrade.ResultRetcode();
   if(!sent || (retcode != TRADE_RETCODE_DONE && retcode != TRADE_RETCODE_DONE_PARTIAL))
     {
      GteReject(signalId, StringFormat("broker refused the order: %u %s", retcode,
                                       gteTrade.ResultRetcodeDescription()));
      return;
     }

   ulong ticket = gteTrade.ResultOrder();
   GteRemember(signalId, ticket, stopLoss, takeProfit);
   Print("GTE: signal ", signalId, " filled, ticket ", ticket, ", ", lots, " lots of ", brokerSymbol);
   GteStopIsSet(ticket, stopLoss, takeProfit);
  }

// One poll response: MODE|.., RISK|.., then ORDER|id|symbol|direction|entry|sl|tp|reference
void GteHandlePoll(const string text, string &mode)
  {
   string lines[];
   int count = StringSplit(text, '\n', lines);
   double risk = 0.0;
   for(int i = 0; i < count; i++)
     {
      string parts[];
      int fields = StringSplit(lines[i], '|', parts);
      if(fields >= 2 && parts[0] == "MODE")
         mode = parts[1];
      else if(fields >= 2 && parts[0] == "RISK")
         risk = StringToDouble(parts[1]);
      else if(fields >= 7 && parts[0] == "ORDER" && mode == "live" && risk > 0.0)
         GtePlaceOrder(StringToInteger(parts[1]), parts[2], parts[3], StringToDouble(parts[4]),
                       StringToDouble(parts[5]), StringToDouble(parts[6]), risk);
     }
  }

#endif
