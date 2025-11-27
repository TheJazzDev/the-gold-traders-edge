"use client";

import { useEffect, useCallback } from "react";
import { useMarketStore } from "@/store";
import { priceStream } from "@/services/market";
import type { MarketData } from "@/types";

export function usePriceTicker() {
  const { 
    currentPrice, 
    setCurrentPrice, 
    addPriceHistory, 
    setConnectionStatus 
  } = useMarketStore();

  const handlePriceUpdate = useCallback(
    (price: MarketData) => {
      setCurrentPrice(price);
      addPriceHistory(price);
      setConnectionStatus(true);
    },
    [setCurrentPrice, addPriceHistory, setConnectionStatus]
  );

  useEffect(() => {
    const unsubscribe = priceStream.subscribe(handlePriceUpdate);

    return () => {
      unsubscribe();
      setConnectionStatus(false);
    };
  }, [handlePriceUpdate, setConnectionStatus]);

  return { currentPrice };
}
