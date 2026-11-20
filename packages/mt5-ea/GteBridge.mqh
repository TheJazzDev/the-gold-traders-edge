//+------------------------------------------------------------------+
//| HTTP through files, for a terminal that cannot use WebRequest.   |
//|                                                                  |
//| MT5 keeps its list of allowed web addresses encrypted per        |
//| machine, so it cannot be set up without clicking through the     |
//| Options window. On a server with no screen (packages/            |
//| mt5-terminal) the EA instead writes each request to a file in    |
//| MQL5\Files\<folder>, and a small program next to the terminal    |
//| sends it and writes the answer back.                             |
//|   <id>.req  first line the path, then the JSON body              |
//|   <id>.res  first line the HTTP status, then the response body   |
//+------------------------------------------------------------------+
#ifndef GTE_BRIDGE_MQH
#define GTE_BRIDGE_MQH

int gteBridgeCount = 0;

bool GteBridgeWrite(const string name, const string text)
  {
   int file = FileOpen(name, FILE_WRITE | FILE_BIN);
   if(file == INVALID_HANDLE)
      return false;
   uchar bytes[];
   int size = StringToCharArray(text, bytes, 0, WHOLE_ARRAY, CP_UTF8) - 1; // without the final zero
   if(size > 0)
      FileWriteArray(file, bytes, 0, size);
   FileClose(file);
   return true;
  }

string GteBridgeRead(const string name)
  {
   int file = FileOpen(name, FILE_READ | FILE_BIN);
   if(file == INVALID_HANDLE)
      return "";
   uchar bytes[];
   FileReadArray(file, bytes);
   FileClose(file);
   return CharArrayToString(bytes, 0, WHOLE_ARRAY, CP_UTF8);
  }

// Returns the HTTP status, or -1 when no answer came back in time.
int GteBridgePost(const string folder, const string path, const string json,
                  const uint timeoutMs, string &response)
  {
   response = "";
   string id = folder + "\\" + IntegerToString((long)GetTickCount64()) + "_" + IntegerToString(++gteBridgeCount);

   // Written under another name first, so a half-written request is never sent.
   if(!GteBridgeWrite(id + ".tmp", path + "\n" + json) || !FileMove(id + ".tmp", 0, id + ".req", FILE_REWRITE))
     {
      Print("GTE: could not write the request file, error ", GetLastError());
      return -1;
     }

   ulong deadline = GetTickCount64() + timeoutMs;
   while(GetTickCount64() < deadline && !IsStopped())
     {
      if(FileIsExist(id + ".res"))
        {
         string answer = GteBridgeRead(id + ".res");
         FileDelete(id + ".res");
         int lineEnd = StringFind(answer, "\n");
         if(lineEnd < 0)
            return -1;
         response = StringSubstr(answer, lineEnd + 1);
         return (int)StringToInteger(StringSubstr(answer, 0, lineEnd));
        }
      Sleep(50);
     }
   FileDelete(id + ".req");
   Print("GTE: no answer through the file bridge for ", path);
   return -1;
  }

#endif
