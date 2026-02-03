/**
 * KPI metric cards grid – click to highlight evidence in the PDF viewer.
 */

import { useAppStore } from '../stores/appStore';
import type { MetricValue } from '../types/api';

interface KpiGridProps {
  metrics: MetricValue[];
}

export default function KpiGrid({ metrics }: KpiGridProps) {
  const { setHighlights } = useAppStore();

  const handleClick = (m: MetricValue) => {
    if (m.evidence_refs.length > 0) {
      setHighlights(m.evidence_refs, m.evidence_refs[0].page_no);
    }
  };

  return (
    <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
      {metrics.map((m) => (
        <div
          key={m.mv_id}
          className="kpi-card"
          onClick={() => handleClick(m)}
        >
          <div className="flex items-start justify-between mb-2">
            <span className="text-text-secondary text-xs">{m.metric_name_cn}</span>
            {m.needs_review && (
              <span className="badge badge-info text-[10px]">需复核</span>
            )}
          </div>
          <div className="text-2xl font-bold text-text-primary">
            {m.value !== null ? m.value.toLocaleString() : m.value_text || '-'}
          </div>
          <div className="flex items-center justify-between mt-1">
            <span className="text-text-muted text-xs">{m.unit || ''}</span>
            {m.yoy_change !== null && m.yoy_change !== undefined && (
              <span
                className={`text-xs font-medium ${
                  m.yoy_change >= 0 ? 'text-status-success' : 'text-status-risk-light'
                }`}
              >
                {m.yoy_change >= 0 ? '+' : ''}
                {m.yoy_change.toFixed(1)}%
              </span>
            )}
          </div>
          {/* Evidence indicator */}
          {m.evidence_refs.length > 0 && (
            <div className="mt-2 text-text-muted text-[10px]">
              来源: 第{m.evidence_refs[0].page_no}页
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
