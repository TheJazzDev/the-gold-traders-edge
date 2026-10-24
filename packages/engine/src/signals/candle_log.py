"""
One log line per evaluation holding the exact candle frame live evaluated.

Yahoo revises GC=F hourly highs/lows after live reads them (OBR-1015-01
reproduced on 2026-10-19's data, not on 2026-10-24's), so a live-vs-backtest
mismatch can't be explained from today's history. With this line in the
Railway logs, scripts/replay_logged_candles.py re-runs the strategy on
live's own input.

The whole frame is logged, not just the order-block window: OBR's
confidence bonus reads swing points across the full frame.
"""
import json
import re
from typing import Tuple

import pandas as pd

CANDLE_LOG_PREFIX = 'CANDLES '
_DECIMALS = 6  # well below a tick on gold and FX, so no knife-edge flips


def format_candle_log(df: pd.DataFrame, symbol: str, timeframe: str) -> str:
    payload = {
        'symbol': symbol,
        'timeframe': timeframe,
        't': [int(pd.Timestamp(ts).timestamp()) for ts in df.index],
        'ohlc': [[round(float(v), _DECIMALS) for v in row]
                 for row in df[['open', 'high', 'low', 'close']].itertuples(index=False)],
    }
    return CANDLE_LOG_PREFIX + json.dumps(payload, separators=(',', ':'))


def parse_candle_log(line: str) -> Tuple[str, str, pd.DataFrame]:
    """(symbol, timeframe, frame) from a log line containing format_candle_log output.
    The index is naive UTC, as the live feed returns it."""
    match = re.search(re.escape(CANDLE_LOG_PREFIX) + r'(\{.*\})', line)
    if match is None:
        raise ValueError('no candle log payload in line')
    payload = json.loads(match.group(1))
    index = pd.to_datetime(payload['t'], unit='s')
    df = pd.DataFrame(payload['ohlc'], columns=['open', 'high', 'low', 'close'], index=index)
    df['volume'] = 0
    return payload['symbol'], payload['timeframe'], df
