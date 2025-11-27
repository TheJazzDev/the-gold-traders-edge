"use client";

import { useEffect, useRef, useCallback } from "react";
import {
  createChart,
  IChartApi,
  ISeriesApi,
  CandlestickData,
  Time,
  ColorType,
} from "lightweight-charts";
import { useChartStore } from "@/store";
import { fetchCandleData } from "@/services/market";
import type { Candle, Signal } from "@/types";
import { cn } from "@/lib/utils";

interface GoldChartProps {
  signals?: Signal[];
  className?: string;
}

export function GoldChart({ signals = [], className }: GoldChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  const { timeframe, showSignals, showLevels } = useChartStore();

  const initChart = useCallback(() => {
    if (!chartContainerRef.current) return;

    if (chartRef.current) {
      chartRef.current.remove();
    }

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#9fb3c8",
        fontSize: 12,
        fontFamily: "var(--font-mono)",
      },
      grid: {
        vertLines: { color: "rgba(50, 70, 100, 0.2)" },
        horzLines: { color: "rgba(50, 70, 100, 0.2)" },
      },
      crosshair: {
        mode: 1,
        vertLine: {
          color: "#fbbf24",
          width: 1,
          style: 2,
          labelBackgroundColor: "#1a2332",
        },
        horzLine: {
          color: "#fbbf24",
          width: 1,
          style: 2,
          labelBackgroundColor: "#1a2332",
        },
      },
      rightPriceScale: {
        borderColor: "rgba(50, 70, 100, 0.3)",
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor: "rgba(50, 70, 100, 0.3)",
        timeVisible: true,
        secondsVisible: false,
      },
      handleScroll: { mouseWheel: true, pressedMouseMove: true },
      handleScale: { mouseWheel: true, pinch: true },
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#10b981",
      downColor: "#ef4444",
      borderUpColor: "#10b981",
      borderDownColor: "#ef4444",
      wickUpColor: "#10b981",
      wickDownColor: "#ef4444",
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        });
      }
    };

    window.addEventListener("resize", handleResize);
    handleResize();

    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  const loadData = useCallback(async () => {
    if (!candleSeriesRef.current) return;

    const candles = await fetchCandleData(timeframe);
    const chartData: CandlestickData<Time>[] = candles.map((c: Candle) => ({
      time: c.time as Time,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));

    candleSeriesRef.current.setData(chartData);

    if (showSignals && signals.length > 0 && chartRef.current) {
      const markers = signals
        .filter((s) => s.status !== "CANCELLED" && s.status !== "EXPIRED")
        .map((signal) => ({
          time: (Math.floor(signal.createdAt.getTime() / 1000)) as Time,
          position: signal.direction === "BUY" ? "belowBar" as const : "aboveBar" as const,
          color: signal.direction === "BUY" ? "#10b981" : "#ef4444",
          shape: signal.direction === "BUY" ? "arrowUp" as const : "arrowDown" as const,
          text: `${signal.direction} @ ${signal.entryZone.low.toFixed(2)}`,
        }));

      candleSeriesRef.current.setMarkers(markers);
    }

    if (showLevels && chartRef.current && candles.length > 0) {
      const lastCandle = candles[candles.length - 1];
      
      signals.forEach((signal) => {
        if (signal.status === "PENDING" || signal.status === "ACTIVE") {
          candleSeriesRef.current?.createPriceLine({
            price: signal.entryZone.low,
            color: "#fbbf24",
            lineWidth: 1,
            lineStyle: 2,
            axisLabelVisible: true,
            title: "Entry",
          });

          candleSeriesRef.current?.createPriceLine({
            price: signal.stopLoss,
            color: "#ef4444",
            lineWidth: 1,
            lineStyle: 2,
            axisLabelVisible: true,
            title: "SL",
          });

          candleSeriesRef.current?.createPriceLine({
            price: signal.takeProfit1,
            color: "#10b981",
            lineWidth: 1,
            lineStyle: 2,
            axisLabelVisible: true,
            title: "TP1",
          });

          if (signal.takeProfit2) {
            candleSeriesRef.current?.createPriceLine({
              price: signal.takeProfit2,
              color: "#10b981",
              lineWidth: 1,
              lineStyle: 0,
              axisLabelVisible: true,
              title: "TP2",
            });
          }
        }
      });
    }

    chartRef.current?.timeScale().fitContent();
  }, [timeframe, signals, showSignals, showLevels]);

  useEffect(() => {
    initChart();
    return () => {
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [initChart]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <div className={cn("chart-container relative", className)}>
      <div ref={chartContainerRef} className="w-full h-full" />
      <div className="absolute top-4 left-4 flex items-center gap-2">
        <span className="px-3 py-1 rounded-lg bg-secondary-800/80 border border-secondary-700/50 text-xs font-mono text-primary-400">
          XAUUSD
        </span>
        <span className="px-3 py-1 rounded-lg bg-secondary-800/80 border border-secondary-700/50 text-xs font-mono text-secondary-300">
          {timeframe.toUpperCase()}
        </span>
      </div>
    </div>
  );
}
