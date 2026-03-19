import apiClient from './index';
import { toCamelCase } from './utils';
import type {
  ScreenerTemplate,
  ScreenerTemplateCreate,
  ScreenerTemplateUpdate,
  ScreenerRunRequest,
  ScreenerRunResponse,
  ScreenerResult,
  ScreenerResultsResponse,
  IndicatorsResponse,
  MatchedStock,
} from '../types/screener';

export const screenerApi = {
  // ── 执行选股 ──
  run: async (params: ScreenerRunRequest): Promise<ScreenerRunResponse> => {
    const body: Record<string, unknown> = {};
    if (params.templateId) body.template_id = params.templateId;
    if (params.rules) body.rules = params.rules;
    if (params.stockPool) body.stock_pool = params.stockPool;
    if (params.notify) body.notify = params.notify;

    const response = await apiClient.post<Record<string, unknown>>(
      '/api/v1/screener/run',
      body,
      { timeout: 300000 }, // 5 min for full market scan
    );
    const data = toCamelCase<ScreenerRunResponse>(response.data);
    data.matchedStocks = (data.matchedStocks || []).map(s => toCamelCase<MatchedStock>(s));
    return data;
  },

  // ── 结果查询 ──
  getResults: async (params: {
    templateId?: number;
    page?: number;
    limit?: number;
  } = {}): Promise<ScreenerResultsResponse> => {
    const { templateId, page = 1, limit = 20 } = params;
    const query: Record<string, string | number> = { page, limit };
    if (templateId) query.template_id = templateId;

    const response = await apiClient.get<Record<string, unknown>>(
      '/api/v1/screener/results',
      { params: query },
    );
    const data = toCamelCase<ScreenerResultsResponse>(response.data);
    data.items = (data.items || []).map(item => {
      const r = toCamelCase<ScreenerResult>(item);
      r.matchedStocks = (r.matchedStocks || []).map(s => toCamelCase<MatchedStock>(s));
      return r;
    });
    return data;
  },

  getResultDetail: async (resultId: number): Promise<ScreenerResult> => {
    const response = await apiClient.get<Record<string, unknown>>(
      `/api/v1/screener/results/${resultId}`,
    );
    const data = toCamelCase<ScreenerResult>(response.data);
    data.matchedStocks = (data.matchedStocks || []).map(s => toCamelCase<MatchedStock>(s));
    return data;
  },

  // ── 模板管理 ──
  listTemplates: async (): Promise<ScreenerTemplate[]> => {
    const response = await apiClient.get<Record<string, unknown>[]>(
      '/api/v1/screener/templates',
    );
    return (response.data || []).map(t => toCamelCase<ScreenerTemplate>(t));
  },

  getTemplate: async (id: number): Promise<ScreenerTemplate> => {
    const response = await apiClient.get<Record<string, unknown>>(
      `/api/v1/screener/templates/${id}`,
    );
    return toCamelCase<ScreenerTemplate>(response.data);
  },

  createTemplate: async (data: ScreenerTemplateCreate): Promise<ScreenerTemplate> => {
    const body: Record<string, unknown> = {
      name: data.name,
      rules: data.rules,
    };
    if (data.description) body.description = data.description;
    if (data.autoRun != null) body.auto_run = data.autoRun;

    const response = await apiClient.post<Record<string, unknown>>(
      '/api/v1/screener/templates',
      body,
    );
    return toCamelCase<ScreenerTemplate>(response.data);
  },

  updateTemplate: async (id: number, data: ScreenerTemplateUpdate): Promise<ScreenerTemplate> => {
    const body: Record<string, unknown> = {};
    if (data.name != null) body.name = data.name;
    if (data.description != null) body.description = data.description;
    if (data.rules != null) body.rules = data.rules;
    if (data.autoRun != null) body.auto_run = data.autoRun;

    const response = await apiClient.put<Record<string, unknown>>(
      `/api/v1/screener/templates/${id}`,
      body,
    );
    return toCamelCase<ScreenerTemplate>(response.data);
  },

  deleteTemplate: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/v1/screener/templates/${id}`);
  },

  // ── 指标元数据 ──
  getIndicators: async (): Promise<IndicatorsResponse> => {
    const response = await apiClient.get<Record<string, unknown>>(
      '/api/v1/screener/indicators',
    );
    return toCamelCase<IndicatorsResponse>(response.data);
  },
};
