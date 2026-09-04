/**
 * Single HTTP client for the Gold Trader's Edge API.
 *
 * Previously the app had three parallel HTTP layers (this file, a second
 * axios instance in the now-deleted lib/api.ts, and raw fetch() calls
 * scattered in components) with duplicated, conflicting types. This is the
 * only one now.
 */
import axios, { AxiosInstance, AxiosError } from "axios";
import type {
  MarketStatus,
  PerformanceStats,
  RulePerformance,
  ServiceStatus,
  Setting,
  SettingsByCategory,
  SignalsResponse,
  StrategyPerformance,
  Trade,
} from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      timeout: 30000,
      headers: { "Content-Type": "application/json" },
    });

    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => Promise.reject(error)
    );
  }

  // ==================== SETTINGS ====================

  async getSettingsByCategory(): Promise<SettingsByCategory> {
    const response = await this.client.get("/v1/settings/categories");
    const byCategory: SettingsByCategory = {};
    for (const entry of response.data as { category: string; settings: Setting[] }[]) {
      byCategory[entry.category] = entry.settings;
    }
    return byCategory;
  }

  async updateSetting(key: string, value: unknown, modifiedBy = "web-app"): Promise<Setting> {
    const response = await this.client.put(`/v1/settings/${key}`, {
      value,
      modified_by: modifiedBy,
    });
    return response.data;
  }

  async getServiceStatus(): Promise<ServiceStatus> {
    const response = await this.client.get("/v1/settings/service/status");
    return response.data;
  }

  async getStrategies(): Promise<StrategyPerformance[]> {
    const response = await this.client.get("/v1/settings/strategies");
    return response.data;
  }

  // ==================== SIGNALS ====================

  async getSignals(params?: {
    limit?: number;
    offset?: number;
    status?: string;
    strategy?: string;
    timeframe?: string;
  }): Promise<SignalsResponse> {
    const response = await this.client.get("/v1/signals/history", { params });
    return response.data;
  }

  async getPerformanceStats(days?: number): Promise<PerformanceStats> {
    const response = await this.client.get("/v1/signals/stats/performance", {
      params: days ? { days } : undefined,
    });
    return response.data;
  }

  // ==================== ANALYTICS ====================

  async getByRule(days?: number): Promise<RulePerformance[]> {
    const response = await this.client.get("/v1/analytics/by-rule", {
      params: days ? { days } : undefined,
    });
    return response.data.strategies;
  }

  async getTrades(page = 1, pageSize = 20): Promise<{ total: number; trades: Trade[] }> {
    const response = await this.client.get("/v1/analytics/backtest");
    // /v1/analytics/backtest already returns every resolved trade; paginate
    // client-side rather than adding a redundant endpoint for one screen.
    const all: Trade[] = response.data.trades;
    const start = (page - 1) * pageSize;
    return { total: all.length, trades: all.slice(start, start + pageSize) };
  }

  // ==================== MARKET ====================

  async getMarketStatus(): Promise<MarketStatus> {
    const response = await this.client.get("/v1/market/status");
    return response.data;
  }

  // ==================== HEALTH ====================

  async healthCheck(): Promise<{ status: string }> {
    const response = await this.client.get("/health");
    return response.data;
  }
}

export const apiClient = new APIClient();
export default apiClient;
