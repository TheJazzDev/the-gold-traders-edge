//+------------------------------------------------------------------+
//| Tell the API what the broker did: the fill, then the close.      |
//| Each report is repeated every cycle until the API answers.       |
//+------------------------------------------------------------------+
#ifndef GTE_REPORTS_MQH
#define GTE_REPORTS_MQH

#include "GteHttp.mqh"
#include "GteState.mqh"

bool GteReportFill(const long signalId, const ulong ticket)
  {
   if(!HistorySelectByPosition(ticket))
      return false;
   for(int i = 0; i < HistoryDealsTotal(); i++)
     {
      ulong deal = HistoryDealGetTicket(i);
      if(deal == 0 || HistoryDealGetInteger(deal, DEAL_ENTRY) != DEAL_ENTRY_IN)
         continue;
      string json = "{\"ticket\":" + IntegerToString((long)ticket)
                    + ",\"lots\":" + GteNumber(HistoryDealGetDouble(deal, DEAL_VOLUME))
                    + ",\"entry_price\":" + GteNumber(HistoryDealGetDouble(deal, DEAL_PRICE))
                    + ",\"stop_loss\":" + GteNumber(GteGet("sl", signalId))
                    + ",\"take_profit\":" + GteNumber(GteGet("tp", signalId))
                    + ",\"broker_symbol\":\"" + GteJsonText(HistoryDealGetString(deal, DEAL_SYMBOL)) + "\""
                    + ",\"account\":\"" + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)) + "\"}";
      string response;
      int status = GtePost("/v1/ea/orders/" + IntegerToString(signalId) + "/fill", json, response);
      return status == 200 || status == 404;
     }
   return false; // the opening deal is not in history yet
  }

string GteCloseReason(const long dealReason)
  {
   if(dealReason == DEAL_REASON_SL)
      return "sl";
   if(dealReason == DEAL_REASON_TP)
      return "tp";
   if(dealReason == DEAL_REASON_CLIENT || dealReason == DEAL_REASON_MOBILE || dealReason == DEAL_REASON_WEB)
      return "manual";
   return "other";
  }

bool GteReportClose(const long signalId, const ulong ticket)
  {
   if(!HistorySelectByPosition(ticket))
      return false;
   double profit = 0.0;
   double exitPrice = 0.0;
   string closeReason = "";
   for(int i = 0; i < HistoryDealsTotal(); i++)
     {
      ulong deal = HistoryDealGetTicket(i);
      if(deal == 0)
         continue;
      profit += HistoryDealGetDouble(deal, DEAL_PROFIT) + HistoryDealGetDouble(deal, DEAL_SWAP)
                + HistoryDealGetDouble(deal, DEAL_COMMISSION);
      if(HistoryDealGetInteger(deal, DEAL_ENTRY) == DEAL_ENTRY_OUT)
        {
         exitPrice = HistoryDealGetDouble(deal, DEAL_PRICE);
         closeReason = GteCloseReason(HistoryDealGetInteger(deal, DEAL_REASON));
        }
     }
   if(closeReason == "")
      return false; // the closing deal is not in history yet

   string json = "{\"exit_price\":" + GteNumber(exitPrice) + ",\"profit\":" + GteNumber(profit)
                 + ",\"close_reason\":\"" + closeReason + "\"}";
   string response;
   int status = GtePost("/v1/ea/orders/" + IntegerToString(signalId) + "/close", json, response);
   return status == 200 || status == 404;
  }

void GteSendReports()
  {
   long signalIds[];
   int count = GteTrackedSignals(signalIds);
   for(int i = 0; i < count; i++)
     {
      long signalId = signalIds[i];
      ulong ticket = (ulong)GteGet("pos", signalId);

      if(GteGet("rep", signalId) < 1.0)
        {
         if(!GteReportFill(signalId, ticket))
            continue;
         GteSet("rep", signalId, 1.0);
        }
      if(!PositionSelectByTicket(ticket) && GteReportClose(signalId, ticket))
        {
         Print("GTE: signal ", signalId, " closed and reported");
         GteMarkDone(signalId);
        }
     }
  }

#endif
