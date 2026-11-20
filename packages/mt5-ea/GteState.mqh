//+------------------------------------------------------------------+
//| What the EA remembers about each signal, kept in terminal global |
//| variables so it survives a restart. One signal moves through:    |
//|   try  -> an order was about to be sent                          |
//|   pos  -> the position ticket, once filled                       |
//|   done -> finished (closed and reported, or rejected)            |
//+------------------------------------------------------------------+
#ifndef GTE_STATE_MQH
#define GTE_STATE_MQH

#define GTE_PREFIX "GTE_"

string GteKey(const string field, const long signalId)
  {
   return GTE_PREFIX + field + "_" + IntegerToString(signalId);
  }

bool GteHas(const string field, const long signalId)
  {
   return GlobalVariableCheck(GteKey(field, signalId));
  }

double GteGet(const string field, const long signalId)
  {
   return GlobalVariableGet(GteKey(field, signalId));
  }

void GteSet(const string field, const long signalId, const double value)
  {
   GlobalVariableSet(GteKey(field, signalId), value);
  }

void GteForget(const long signalId)
  {
   string fields[] = {"try", "pos", "rep", "sl", "tp"};
   for(int i = 0; i < ArraySize(fields); i++)
      GlobalVariableDel(GteKey(fields[i], signalId));
  }

void GteMarkDone(const long signalId)
  {
   GteForget(signalId);
   GteSet("done", signalId, (double)TimeCurrent());
  }

// Signals with a recorded position, open or waiting for its close report.
int GteTrackedSignals(long &signalIds[])
  {
   string prefix = GTE_PREFIX + "pos_";
   int count = 0;
   ArrayResize(signalIds, 0);
   for(int i = GlobalVariablesTotal() - 1; i >= 0; i--)
     {
      string name = GlobalVariableName(i);
      if(StringFind(name, prefix) != 0)
         continue;
      ArrayResize(signalIds, count + 1);
      signalIds[count++] = StringToInteger(StringSubstr(name, StringLen(prefix)));
     }
   return count;
  }

#endif
