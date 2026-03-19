// ============ Screener Types ============

export interface ScreenerCondition {
  logic?: 'AND' | 'OR';
  conditions?: ScreenerCondition[];
  type?: 'fundamental' | 'technical' | 'market';
  indicator?: string;
  params?: Record<string, unknown>;
  operator?: string;
  value?: unknown;
}

export interface ScreenerTemplate {
  id: number;
  name: string;
  description?: string;
  rules: ScreenerCondition;
  isBuiltin: boolean;
  autoRun: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface ScreenerTemplateCreate {
  name: string;
  description?: string;
  rules: ScreenerCondition;
  autoRun?: boolean;
}

export interface ScreenerTemplateUpdate {
  name?: string;
  description?: string;
  rules?: ScreenerCondition;
  autoRun?: boolean;
}

export interface MatchedStock {
  code: string;
  name: string;
  price?: number;
  changePct?: number;
  peRatio?: number;
  pbRatio?: number;
  totalMv?: number;
  volumeRatio?: number;
  turnoverRate?: number;
  matchedIndicators?: Record<string, unknown>;
}

export interface ScreenerRunRequest {
  templateId?: number;
  rules?: ScreenerCondition;
  stockPool?: string[];
  notify?: boolean;
}

export interface ScreenerRunResponse {
  runId: number;
  templateName?: string;
  totalScanned: number;
  matchedCount: number;
  matchedStocks: MatchedStock[];
  durationSeconds: number;
}

export interface ScreenerResult {
  id: number;
  templateId?: number;
  templateName?: string;
  runDate: string;
  totalScanned: number;
  matchedCount: number;
  matchedStocks: MatchedStock[];
  durationSeconds: number;
  createdAt?: string;
}

export interface ScreenerResultsResponse {
  total: number;
  page: number;
  limit: number;
  items: ScreenerResult[];
}

export interface IndicatorMeta {
  name: string;
  label: string;
  type: 'fundamental' | 'technical' | 'market';
  operators: string[];
  defaultParams?: Record<string, unknown>;
  description: string;
}

export interface IndicatorsResponse {
  indicators: IndicatorMeta[];
}
