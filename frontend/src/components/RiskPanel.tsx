/**
 * Risk panel – displays risk entries with level badges.
 * Clicking highlights evidence in the PDF viewer.
 */

import { useAppStore } from '../stores/appStore';
import type { RiskItem } from '../types/api';

interface RiskPanelProps {
  risks: RiskItem[];
}

const LEVEL_LABELS: Record<string, string> = {
  high: '高风险',
  medium: '中风险',
  low: '低风险',
};

export default function RiskPanel({ risks }: RiskPanelProps) {
  const { setHighlights } = useAppStore();

  const handleClick = (r: RiskItem) => {
    if (r.evidence_refs.length > 0) {
      setHighlights(r.evidence_refs, r.evidence_refs[0].page_no);
    }
  };

  return (
    <div className="space-y-3">
      {risks.map((r) => (
        <div
          key={r.risk_id}
          className={`risk-entry ${r.level}`}
          onClick={() => handleClick(r)}
        >
          <div className="flex items-center gap-2 mb-1">
            <span
              className={`badge ${
                r.level === 'high'
                  ? 'badge-risk'
                  : r.level === 'medium'
                  ? 'badge-info'
                  : 'badge-success'
              }`}
            >
              {LEVEL_LABELS[r.level] || r.level}
            </span>
            {r.needs_review && (
              <span className="badge badge-info text-[10px]">需复核</span>
            )}
          </div>
          <h4 className="text-text-primary font-medium text-sm">{r.title}</h4>
          {r.description && (
            <p className="text-text-secondary text-xs mt-1 line-clamp-2">{r.description}</p>
          )}
          {r.recommendation && (
            <p className="text-primary-electric text-xs mt-1">
              建议: {r.recommendation}
            </p>
          )}
          {r.evidence_refs.length > 0 && (
            <p className="text-text-muted text-[10px] mt-2">
              来源: {r.evidence_refs.map((e) => `第${e.page_no}页`).join(', ')}
            </p>
          )}
        </div>
      ))}

      {risks.length === 0 && (
        <p className="text-text-muted text-sm text-center py-4">暂无风险提示</p>
      )}
    </div>
  );
}
