import type React from 'react';
import { useState, useEffect, useCallback } from 'react';
import { screenerApi } from '../api/screener';
import type { ParsedApiError } from '../api/error';
import { getParsedApiError } from '../api/error';
import {
  ApiErrorAlert, Card, Badge, PageHeader, Pagination, Select,
} from '../components/common';
import type {
  ScreenerTemplate,
  ScreenerCondition,
  MatchedStock,
  ScreenerRunResponse,
  ScreenerResult,
  IndicatorMeta,
} from '../types/screener';

// ============ Operator Labels ============
const OPERATOR_LABELS: Record<string, string> = {
  gt: '大于 (>)',
  gte: '大于等于 (>=)',
  lt: '小于 (<)',
  lte: '小于等于 (<=)',
  eq: '等于 (=)',
  between: '介于',
  in_list: '属于',
  cross_above: '金叉/上穿',
  cross_below: '死叉/下穿',
};

const TYPE_LABELS: Record<string, string> = {
  fundamental: '基本面',
  technical: '技术面',
  market: '行情',
};

// ============ Condition Builder ============
interface ConditionRowProps {
  condition: ScreenerCondition;
  indicators: IndicatorMeta[];
  onChange: (c: ScreenerCondition) => void;
  onRemove: () => void;
}

const ConditionRow: React.FC<ConditionRowProps> = ({ condition, indicators, onChange, onRemove }) => {
  const selectedIndicator = indicators.find(i => i.name === condition.indicator);
  const operators = selectedIndicator?.operators || [];

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-xl border border-white/8 bg-elevated/30 px-3 py-2.5">
      {/* Indicator type */}
      <select
        value={condition.type || ''}
        onChange={e => {
          const type = e.target.value;
          onChange({ ...condition, type, indicator: '', operator: '', value: undefined });
        }}
        className="h-9 rounded-lg border border-white/10 bg-card px-2 text-sm text-foreground"
      >
        <option value="">类型</option>
        <option value="fundamental">基本面</option>
        <option value="technical">技术面</option>
        <option value="market">行情</option>
      </select>

      {/* Indicator */}
      <select
        value={condition.indicator || ''}
        onChange={e => {
          const ind = indicators.find(i => i.name === e.target.value);
          onChange({
            ...condition,
            indicator: e.target.value,
            operator: ind?.operators[0] || '',
            value: undefined,
          });
        }}
        className="h-9 min-w-[140px] rounded-lg border border-white/10 bg-card px-2 text-sm text-foreground"
      >
        <option value="">选择指标</option>
        {indicators
          .filter(i => !condition.type || i.type === condition.type)
          .map(i => (
            <option key={i.name} value={i.name}>{i.label}</option>
          ))
        }
      </select>

      {/* Operator */}
      <select
        value={condition.operator || ''}
        onChange={e => onChange({ ...condition, operator: e.target.value })}
        className="h-9 rounded-lg border border-white/10 bg-card px-2 text-sm text-foreground"
      >
        <option value="">运算符</option>
        {operators.map(op => (
          <option key={op} value={op}>{OPERATOR_LABELS[op] || op}</option>
        ))}
      </select>

      {/* Value */}
      {condition.operator === 'between' ? (
        <div className="flex items-center gap-1">
          <input
            type="number"
            placeholder="最小值"
            value={Array.isArray(condition.value) ? condition.value[0] ?? '' : ''}
            onChange={e => {
              const arr = Array.isArray(condition.value) ? [...condition.value] : [0, 0];
              arr[0] = e.target.value === '' ? 0 : Number(e.target.value);
              onChange({ ...condition, value: arr });
            }}
            className="h-9 w-24 rounded-lg border border-white/10 bg-card px-2 text-sm text-foreground"
          />
          <span className="text-xs text-secondary-text">~</span>
          <input
            type="number"
            placeholder="最大值"
            value={Array.isArray(condition.value) ? condition.value[1] ?? '' : ''}
            onChange={e => {
              const arr = Array.isArray(condition.value) ? [...condition.value] : [0, 0];
              arr[1] = e.target.value === '' ? 0 : Number(e.target.value);
              onChange({ ...condition, value: arr });
            }}
            className="h-9 w-24 rounded-lg border border-white/10 bg-card px-2 text-sm text-foreground"
          />
        </div>
      ) : condition.operator === 'in_list' ? (
        <input
          type="text"
          placeholder="逗号分隔，如: 强势多头,多头排列"
          value={Array.isArray(condition.value) ? condition.value.join(',') : ''}
          onChange={e => onChange({ ...condition, value: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })}
          className="h-9 min-w-[200px] rounded-lg border border-white/10 bg-card px-2 text-sm text-foreground"
        />
      ) : condition.operator !== 'cross_above' && condition.operator !== 'cross_below' ? (
        <input
          type="number"
          placeholder="阈值"
          value={condition.value != null ? String(condition.value) : ''}
          onChange={e => onChange({ ...condition, value: e.target.value === '' ? undefined : Number(e.target.value) })}
          className="h-9 w-28 rounded-lg border border-white/10 bg-card px-2 text-sm text-foreground"
        />
      ) : null}

      {/* Remove */}
      <button
        type="button"
        onClick={onRemove}
        className="ml-auto flex h-8 w-8 items-center justify-center rounded-lg text-red-400 hover:bg-red-400/10 transition-colors"
        title="删除条件"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
};

// ============ Condition Group Builder ============
interface ConditionGroupProps {
  group: ScreenerCondition;
  indicators: IndicatorMeta[];
  onChange: (g: ScreenerCondition) => void;
  depth?: number;
}

const ConditionGroup: React.FC<ConditionGroupProps> = ({ group, indicators, onChange, depth = 0 }) => {
  const conditions = group.conditions || [];

  const addCondition = () => {
    onChange({
      ...group,
      conditions: [...conditions, { type: '', indicator: '', operator: '', value: undefined }],
    });
  };

  const addGroup = () => {
    onChange({
      ...group,
      conditions: [...conditions, { logic: 'AND', conditions: [] }],
    });
  };

  const updateCondition = (index: number, updated: ScreenerCondition) => {
    const next = [...conditions];
    next[index] = updated;
    onChange({ ...group, conditions: next });
  };

  const removeCondition = (index: number) => {
    onChange({ ...group, conditions: conditions.filter((_, i) => i !== index) });
  };

  const toggleLogic = () => {
    onChange({ ...group, logic: group.logic === 'AND' ? 'OR' : 'AND' });
  };

  return (
    <div className={`rounded-2xl border ${depth > 0 ? 'border-white/6 bg-white/[0.02]' : 'border-white/10 bg-card/40'} p-3 space-y-2`}>
      {/* Logic toggle + actions */}
      <div className="flex items-center gap-2 mb-2">
        <button
          type="button"
          onClick={toggleLogic}
          className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
            group.logic === 'AND'
              ? 'bg-cyan/15 text-cyan border border-cyan/30'
              : 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
          }`}
        >
          {group.logic === 'AND' ? '且 (AND)' : '或 (OR)'}
        </button>
        <span className="text-xs text-muted-text">
          {group.logic === 'AND' ? '所有条件都需满足' : '满足任一条件即可'}
        </span>
      </div>

      {/* Conditions */}
      {conditions.map((c, i) => (
        <div key={i}>
          {c.logic && c.conditions ? (
            <ConditionGroup
              group={c}
              indicators={indicators}
              onChange={updated => updateCondition(i, updated)}
              depth={depth + 1}
            />
          ) : (
            <ConditionRow
              condition={c}
              indicators={indicators}
              onChange={updated => updateCondition(i, updated)}
              onRemove={() => removeCondition(i)}
            />
          )}
        </div>
      ))}

      {/* Add buttons */}
      <div className="flex gap-2 pt-1">
        <button
          type="button"
          onClick={addCondition}
          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium text-cyan hover:bg-cyan/10 border border-cyan/20 transition-colors"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          添加条件
        </button>
        {depth < 2 && (
          <button
            type="button"
            onClick={addGroup}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium text-secondary-text hover:bg-white/5 border border-white/10 transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
            添加条件组
          </button>
        )}
      </div>
    </div>
  );
};

// ============ Results Table ============
const ResultsTable: React.FC<{ stocks: MatchedStock[] }> = ({ stocks }) => {
  if (!stocks.length) return null;

  const formatMv = (v?: number) => {
    if (v == null) return '--';
    if (v >= 1e12) return `${(v / 1e12).toFixed(1)}万亿`;
    if (v >= 1e8) return `${(v / 1e8).toFixed(1)}亿`;
    return `${(v / 1e4).toFixed(0)}万`;
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/10 text-left text-xs text-secondary-text">
            <th className="px-3 py-2.5 font-medium">代码</th>
            <th className="px-3 py-2.5 font-medium">名称</th>
            <th className="px-3 py-2.5 font-medium text-right">最新价</th>
            <th className="px-3 py-2.5 font-medium text-right">涨跌幅</th>
            <th className="px-3 py-2.5 font-medium text-right">PE</th>
            <th className="px-3 py-2.5 font-medium text-right">PB</th>
            <th className="px-3 py-2.5 font-medium text-right">总市值</th>
            <th className="px-3 py-2.5 font-medium text-right">量比</th>
            <th className="px-3 py-2.5 font-medium text-right">换手率</th>
          </tr>
        </thead>
        <tbody>
          {stocks.map((stock) => {
            const changePct = stock.changePct;
            const changeColor = changePct != null
              ? changePct > 0 ? 'text-red-400' : changePct < 0 ? 'text-emerald-400' : 'text-foreground'
              : 'text-muted-text';

            return (
              <tr key={stock.code} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                <td className="px-3 py-2.5 font-mono text-cyan">{stock.code}</td>
                <td className="px-3 py-2.5 text-foreground">{stock.name}</td>
                <td className="px-3 py-2.5 text-right font-mono text-foreground">
                  {stock.price != null ? stock.price.toFixed(2) : '--'}
                </td>
                <td className={`px-3 py-2.5 text-right font-mono ${changeColor}`}>
                  {changePct != null ? `${changePct > 0 ? '+' : ''}${changePct.toFixed(2)}%` : '--'}
                </td>
                <td className="px-3 py-2.5 text-right font-mono text-secondary-text">
                  {stock.peRatio != null ? stock.peRatio.toFixed(1) : '--'}
                </td>
                <td className="px-3 py-2.5 text-right font-mono text-secondary-text">
                  {stock.pbRatio != null ? stock.pbRatio.toFixed(2) : '--'}
                </td>
                <td className="px-3 py-2.5 text-right font-mono text-secondary-text">
                  {formatMv(stock.totalMv)}
                </td>
                <td className="px-3 py-2.5 text-right font-mono text-secondary-text">
                  {stock.volumeRatio != null ? stock.volumeRatio.toFixed(2) : '--'}
                </td>
                <td className="px-3 py-2.5 text-right font-mono text-secondary-text">
                  {stock.turnoverRate != null ? `${stock.turnoverRate.toFixed(2)}%` : '--'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

// ============ History Card ============
const HistoryCard: React.FC<{ result: ScreenerResult; onClick: () => void }> = ({ result, onClick }) => (
  <button
    type="button"
    onClick={onClick}
    className="w-full text-left rounded-xl border border-white/8 bg-card/50 p-4 hover:border-cyan/20 hover:bg-card/70 transition-all"
  >
    <div className="flex items-center justify-between">
      <div>
        <span className="text-sm font-medium text-foreground">{result.templateName || '自定义规则'}</span>
        <span className="ml-2 text-xs text-muted-text">{result.runDate}</span>
      </div>
      <div className="flex items-center gap-2">
        <Badge variant="info">{result.matchedCount} 只命中</Badge>
        <span className="text-xs text-muted-text">{result.durationSeconds.toFixed(1)}s</span>
      </div>
    </div>
  </button>
);

// ============ Main Page ============
const ScreenerPage: React.FC = () => {
  // State
  const [indicators, setIndicators] = useState<IndicatorMeta[]>([]);
  const [templates, setTemplates] = useState<ScreenerTemplate[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('');
  const [rules, setRules] = useState<ScreenerCondition>({ logic: 'AND', conditions: [] });
  const [templateName, setTemplateName] = useState('');
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<ScreenerRunResponse | null>(null);
  const [error, setError] = useState<ParsedApiError | null>(null);
  const [activeTab, setActiveTab] = useState<'builder' | 'history'>('builder');
  const [notify, setNotify] = useState(false);

  // History state
  const [history, setHistory] = useState<ScreenerResult[]>([]);
  const [historyPage, setHistoryPage] = useState(1);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [selectedHistory, setSelectedHistory] = useState<ScreenerResult | null>(null);

  // Load indicators and templates on mount
  useEffect(() => {
    screenerApi.getIndicators()
      .then(res => setIndicators(res.indicators || []))
      .catch(() => {});
    loadTemplates();
  }, []);

  const loadTemplates = useCallback(async () => {
    try {
      const list = await screenerApi.listTemplates();
      setTemplates(list);
    } catch {}
  }, []);

  const loadHistory = useCallback(async () => {
    try {
      const res = await screenerApi.getResults({ page: historyPage, limit: 10 });
      setHistory(res.items);
      setHistoryTotal(res.total);
    } catch {}
  }, [historyPage]);

  useEffect(() => {
    if (activeTab === 'history') loadHistory();
  }, [activeTab, loadHistory]);

  // Load template rules
  const handleSelectTemplate = (id: string) => {
    setSelectedTemplateId(id);
    if (!id) {
      setRules({ logic: 'AND', conditions: [] });
      setTemplateName('');
      return;
    }
    const t = templates.find(t => t.id === Number(id));
    if (t) {
      setRules(t.rules || { logic: 'AND', conditions: [] });
      setTemplateName(t.name);
    }
  };

  // Run screener
  const handleRun = async () => {
    setError(null);
    setRunning(true);
    setRunResult(null);
    try {
      const result = await screenerApi.run({
        templateId: selectedTemplateId ? Number(selectedTemplateId) : undefined,
        rules: selectedTemplateId ? undefined : rules,
        notify,
      });
      setRunResult(result);
    } catch (err) {
      setError(getParsedApiError(err));
    } finally {
      setRunning(false);
    }
  };

  // Save template
  const handleSaveTemplate = async () => {
    if (!templateName.trim()) return;
    setError(null);
    try {
      if (selectedTemplateId) {
        await screenerApi.updateTemplate(Number(selectedTemplateId), {
          name: templateName,
          rules,
        });
      } else {
        const created = await screenerApi.createTemplate({
          name: templateName,
          rules,
        });
        setSelectedTemplateId(String(created.id));
      }
      await loadTemplates();
    } catch (err) {
      setError(getParsedApiError(err));
    }
  };

  // Delete template
  const handleDeleteTemplate = async () => {
    if (!selectedTemplateId) return;
    try {
      await screenerApi.deleteTemplate(Number(selectedTemplateId));
      setSelectedTemplateId('');
      setRules({ logic: 'AND', conditions: [] });
      setTemplateName('');
      await loadTemplates();
    } catch (err) {
      setError(getParsedApiError(err));
    }
  };

  const conditionCount = (rules.conditions || []).length;

  return (
    <main className="mx-auto min-h-screen w-full max-w-7xl px-4 pb-8 pt-4 md:px-6 lg:px-8">
      <PageHeader
        eyebrow="STOCK SCREENER"
        title="智能选股器"
        description="组合技术面、基本面、行情条件，扫描全市场寻找目标股票"
        actions={
          <div className="flex items-center gap-2">
            {/* Tab switch */}
            <div className="flex rounded-xl border border-white/10 overflow-hidden">
              <button
                type="button"
                onClick={() => setActiveTab('builder')}
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  activeTab === 'builder' ? 'bg-cyan/15 text-cyan' : 'text-secondary-text hover:text-foreground'
                }`}
              >
                条件构建
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('history')}
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  activeTab === 'history' ? 'bg-cyan/15 text-cyan' : 'text-secondary-text hover:text-foreground'
                }`}
              >
                历史记录
              </button>
            </div>
          </div>
        }
      />

      {error && <div className="mt-4"><ApiErrorAlert error={error} /></div>}

      <div className="mt-6 space-y-6">
        {activeTab === 'builder' ? (
          <>
            {/* Template selector */}
            <Card variant="default" padding="md">
              <div className="flex flex-wrap items-end gap-3">
                <div className="flex-1 min-w-[200px]">
                  <Select
                    label="选股模板"
                    value={selectedTemplateId}
                    onChange={handleSelectTemplate}
                    options={templates.map(t => ({
                      value: String(t.id),
                      label: `${t.name}${t.isBuiltin ? ' (内置)' : ''}`,
                    }))}
                    placeholder="新建规则 / 选择模板"
                  />
                </div>
                <div className="flex-1 min-w-[200px]">
                  <label className="mb-2 block text-sm font-medium text-foreground">模板名称</label>
                  <input
                    type="text"
                    value={templateName}
                    onChange={e => setTemplateName(e.target.value)}
                    placeholder="输入模板名称以保存"
                    className="h-11 w-full rounded-xl border border-white/10 bg-card px-4 text-sm text-foreground shadow-soft-card focus:outline-none focus:ring-4 focus:ring-cyan/15 focus:border-cyan/40"
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={handleSaveTemplate}
                    disabled={!templateName.trim()}
                    className="btn-secondary h-11 px-4"
                  >
                    保存模板
                  </button>
                  {selectedTemplateId && (
                    <button
                      type="button"
                      onClick={handleDeleteTemplate}
                      className="h-11 px-4 rounded-xl border border-red-400/20 text-red-400 text-sm font-medium hover:bg-red-400/10 transition-colors"
                    >
                      删除
                    </button>
                  )}
                </div>
              </div>
            </Card>

            {/* Condition builder */}
            <Card variant="default" padding="md">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-foreground">筛选条件</h2>
                <Badge variant={conditionCount > 0 ? 'info' : 'default'}>
                  {conditionCount} 个条件
                </Badge>
              </div>
              <ConditionGroup
                group={rules}
                indicators={indicators}
                onChange={setRules}
              />
            </Card>

            {/* Run button */}
            <div className="flex items-center gap-4">
              <button
                type="button"
                onClick={handleRun}
                disabled={running || conditionCount === 0}
                className="btn-primary h-12 px-8 text-base font-semibold disabled:opacity-50"
              >
                {running ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                    扫描中...
                  </span>
                ) : (
                  '开始选股'
                )}
              </button>
              <label className="flex items-center gap-2 text-sm text-secondary-text cursor-pointer">
                <input
                  type="checkbox"
                  checked={notify}
                  onChange={e => setNotify(e.target.checked)}
                  className="h-4 w-4 rounded border-white/20 bg-card text-cyan focus:ring-cyan/30"
                />
                推送通知
              </label>
            </div>

            {/* Results */}
            {runResult && (
              <Card variant="gradient" padding="md" className="animate-fade-in">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-lg font-semibold text-foreground">
                      选股结果
                      {runResult.templateName && (
                        <span className="ml-2 text-sm font-normal text-secondary-text">
                          — {runResult.templateName}
                        </span>
                      )}
                    </h2>
                    <p className="text-sm text-secondary-text mt-1">
                      扫描 {runResult.totalScanned} 只 · 命中{' '}
                      <span className="text-cyan font-semibold">{runResult.matchedCount}</span> 只
                      · 耗时 {runResult.durationSeconds.toFixed(1)}s
                    </p>
                  </div>
                  <Badge variant="success" size="md" glow>
                    {runResult.matchedCount} 只
                  </Badge>
                </div>
                <ResultsTable stocks={runResult.matchedStocks} />
              </Card>
            )}
          </>
        ) : (
          /* History tab */
          <>
            <div className="space-y-3">
              {history.length === 0 ? (
                <Card variant="default" padding="md">
                  <p className="text-center text-secondary-text py-8">暂无选股历史记录</p>
                </Card>
              ) : (
                history.map(r => (
                  <HistoryCard key={r.id} result={r} onClick={() => setSelectedHistory(r)} />
                ))
              )}
            </div>
            {historyTotal > 10 && (
              <Pagination
                current={historyPage}
                total={Math.ceil(historyTotal / 10)}
                onChange={setHistoryPage}
              />
            )}

            {/* History detail */}
            {selectedHistory && (
              <Card variant="gradient" padding="md" className="animate-fade-in">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-lg font-semibold text-foreground">
                      {selectedHistory.templateName || '自定义规则'}
                    </h2>
                    <p className="text-sm text-secondary-text mt-1">
                      {selectedHistory.runDate} · 扫描 {selectedHistory.totalScanned} 只 · 命中{' '}
                      <span className="text-cyan font-semibold">{selectedHistory.matchedCount}</span> 只
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setSelectedHistory(null)}
                    className="text-secondary-text hover:text-foreground"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
                <ResultsTable stocks={selectedHistory.matchedStocks} />
              </Card>
            )}
          </>
        )}
      </div>
    </main>
  );
};

export default ScreenerPage;
