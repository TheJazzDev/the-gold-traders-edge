//+------------------------------------------------------------------+
//| HTTP to the bot's API. The API URL must be in the terminal's     |
//| allowed list: Tools > Options > Expert Advisors > Allow          |
//| WebRequest for listed URL.                                       |
//+------------------------------------------------------------------+
#ifndef GTE_HTTP_MQH
#define GTE_HTTP_MQH

#define GTE_HTTP_TIMEOUT_MS 8000
#define GTE_ERR_URL_NOT_ALLOWED 4014

// Returns the HTTP status, or -1 when the request never left the terminal.
int GtePost(const string path, const string json, string &response)
  {
   char body[];
   char result[];
   string resultHeaders;
   string headers = "Content-Type: application/json\r\nX-EA-Key: " + InpApiKey + "\r\n";

   StringToCharArray(json, body, 0, WHOLE_ARRAY, CP_UTF8);
   if(ArraySize(body) > 0)
      ArrayResize(body, ArraySize(body) - 1); // drop the terminating zero

   ResetLastError();
   int status = WebRequest("POST", InpApiUrl + path, headers, GTE_HTTP_TIMEOUT_MS, body, result, resultHeaders);
   if(status == -1)
     {
      int error = GetLastError();
      if(error == GTE_ERR_URL_NOT_ALLOWED)
         Print("GTE: add ", InpApiUrl, " to Tools > Options > Expert Advisors > Allow WebRequest");
      else
         Print("GTE: request to ", path, " failed, error ", error);
      response = "";
      return -1;
     }
   response = CharArrayToString(result, 0, WHOLE_ARRAY, CP_UTF8);
   return status;
  }

string GteNumber(const double value)
  {
   return DoubleToString(value, 8);
  }

// Server and symbol names go into JSON strings; keep them to safe characters.
string GteJsonText(const string value)
  {
   string clean = value;
   StringReplace(clean, "\\", "");
   StringReplace(clean, "\"", "");
   return clean;
  }

#endif
