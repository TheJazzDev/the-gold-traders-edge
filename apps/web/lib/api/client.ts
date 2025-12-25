/**
 * API Client for Gold Trader's Edge
 * Connects to Railway backend API
 */

import axios, { AxiosInstance, AxiosError } from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor (add auth token if needed)
    this.client.interceptors.request.use(
      (config) => {
        // TODO: Add authentication token from session
        // const token = getSession()?.token;
        // if (token) {
        //   config.headers.Authorization = `Bearer ${token}`;
        // }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor (handle errors)
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Unauthorized - redirect to login
          // window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // ==================== SETTINGS ====================

  async getSettings(category?: string) {
    const params = category ? { category } : {};
    const response = await this.client.get('/v1/settings', { params });
    return response.data;
  }

  async getSettingsByCategory() {
    const response = await this.client.get('/v1/settings/categories');
    return response.data;
  }

  async getSetting(key: string) {
    const response = await this.client.get(`/v1/settings/${key}`);
    return response.data;
  }

  async updateSetting(key: string, value: any, modifiedBy: string = 'admin') {
    const response = await this.client.put(`/v1/settings/${key}`, {
      value,
      modified_by: modifiedBy,
    });
    return response.data;
  }

  async bulkUpdateSettings(settings: Record<string, any>, modifiedBy: string = 'admin') {
    const response = await this.client.put('/v1/settings/bulk/update', {
      settings,
      modified_by: modifiedBy,
    });
    return response.data;
  }

  async resetSetting(key: string, modifiedBy: string = 'admin') {
    const response = await this.client.post(`/v1/settings/${key}/reset`, null, {
      params: { modified_by: modifiedBy },
    });
    return response.data;
  }

  async getServiceStatus() {
    const response = await this.client.get('/v1/settings/service/status');
    return response.data;
  }

  // ==================== SIGNALS ====================

  async getSignals(params?: {
    limit?: number;
    offset?: number;
    status?: string;
    strategy?: string;
    timeframe?: string;
  }) {
    const response = await this.client.get('/v1/signals/history', { params });
    return response.data;
  }

  async getSignal(id: string) {
    const response = await this.client.get(`/v1/signals/${id}`);
    return response.data;
  }

  // ==================== ANALYTICS ====================

  async getAnalyticsOverview() {
    const response = await this.client.get('/v1/analytics/overview');
    return response.data;
  }

  async getPerformanceMetrics(params?: {
    days?: number;
    strategy?: string;
  }) {
    const response = await this.client.get('/v1/analytics/performance', { params });
    return response.data;
  }

  // ==================== HEALTH ====================

  async healthCheck() {
    const response = await this.client.get('/health');
    return response.data;
  }
}

export const apiClient = new APIClient();
export default apiClient;
