"""
Run coroutines from the service's worker threads.

The MetaAPI SDK keeps a websocket alive on its event loop, so that loop has to
keep running between calls. One daemon thread owns it, and every worker hands
coroutines to it.
"""
import asyncio
import threading
from typing import Any, Coroutine, Optional

_shared: Optional['AsyncBridge'] = None
_shared_lock = threading.Lock()


class AsyncBridge:
    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, name='metaapi-loop', daemon=True)
        self._thread.start()

    def run(self, coroutine: Coroutine, timeout: float = 60.0) -> Any:
        return asyncio.run_coroutine_threadsafe(coroutine, self._loop).result(timeout)


def shared_bridge() -> AsyncBridge:
    global _shared
    with _shared_lock:
        if _shared is None:
            _shared = AsyncBridge()
        return _shared
