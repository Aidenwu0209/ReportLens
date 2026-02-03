/**
 * F5 – Dashboard page.
 *
 * Route: /docs/:docId/v/:versionId
 * Layout: Left 40% PDF viewer + Right 60% analysis panel
 * Features: KPI cards, charts, risk panel, Q&A floater, export button.
 */

import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiClient from '../api/client';
import { useAppStore } from '../stores/appStore';
import PdfViewer from '../components/PdfViewer';
import KpiGrid from '../components/KpiGrid';
import MetricsChart from '../components/MetricsChart';
import RiskPanel from '../components/RiskPanel';
import ChatFloater from '../components/ChatFloater';
import type { DashboardResult } from '../types/api';

export default function DashboardPage() {
  const { docId, versionId } = useParams<{ docId: string; versionId: string }>();
  const navigate = useNavigate();
  const { setDashboardResult, clearHighlights } = useAppStore();

  const [result, setResult] = useState<DashboardResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [activeTab, setActiveTab] = useState<'metrics' | 'risks'>('metrics');

  useEffect(() => {
    if (!docId || !versionId) return;
    clearHighlights();

    const fetch = async () => {
      try {
        const data = await apiClient.getDashboardResult(docId, versionId);
        setResult(data);
        setDashboardResult(data);
      } catch (err: any) {
        setError(err?.response?.data?.message || 'Failed to load results');
      } finally {
        setLoading(false);
      }
    };

    fetch();
  }, [docId, versionId, setDashboardResult, clearHighlights]);

  const handleExport = async (format: 'docx' | 'pdf') => {
    if (!versionId) return;
    setExporting(true);
    try {
      const exp = await apiClient.createExport(versionId, format);
      // Poll for completion
      const pollExport = async () => {
        const status = await apiClient.getExport(exp.export_id);
        if (status.status === 'done') {
          window.open(apiClient.getExportDownloadUrl(exp.export_id), '_blank');
          setExporting(false);
        } else if (status.status === 'failed') {
          setExporting(false);
          alert('Export failed: ' + (status.error_message || 'Unknown error'));
        } else {
          setTimeout(pollExport, 2000);
        }
      };
      setTimeout(pollExport, 2000);
    } catch {
      setExporting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-primary-electric/30 border-t-primary-electric rounded-full animate-spin mx-auto mb-4" />
          <p className="text-text-secondary">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass-card p-8 text-center max-w-md">
          <p className="text-status-risk-light mb-4">{error || 'No data'}</p>
          <button onClick={() => navigate('/')} className="text-primary-electric hover:underline text-sm">
            Return to Upload
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Top bar */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-white/10 bg-surface-card backdrop-blur-card">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate('/')} className="text-text-muted hover:text-text-primary transition-colors">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <h1 className="text-text-primary font-medium">分析结果</h1>
          <span className="text-text-muted text-xs">
            {result.page_count} 页
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleExport('docx')}
            disabled={exporting}
            className="glass-card px-4 py-1.5 text-sm text-text-primary hover:shadow-glow transition-all disabled:opacity-50"
          >
            {exporting ? 'Exporting...' : 'Export Word'}
          </button>
          <button
            onClick={() => handleExport('pdf')}
            disabled={exporting}
            className="bg-primary-electric hover:bg-primary-hover text-white px-4 py-1.5 rounded-card text-sm transition-colors disabled:opacity-50"
          >
            Export PDF
          </button>
        </div>
      </header>

      {/* Main content: 40% PDF | 60% Analysis */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: PDF Viewer */}
        <div className="w-2/5 border-r border-white/10">
          <PdfViewer
            docId={result.doc_id}
            versionId={result.version_id}
            pageCount={result.page_count}
          />
        </div>

        {/* Right: Analysis panel */}
        <div className="w-3/5 overflow-y-auto p-6 space-y-6">
          {/* Summary */}
          {result.summary && (
            <div className="glass-card p-5 animate-fade-in">
              <h2 className="text-text-secondary text-xs font-medium mb-2">AI 总结</h2>
              <p className="text-text-primary text-sm leading-relaxed">{result.summary}</p>
            </div>
          )}

          {/* Tab switcher */}
          <div className="flex gap-1 bg-surface rounded-lg p-1">
            <button
              onClick={() => setActiveTab('metrics')}
              className={`flex-1 py-2 text-sm rounded-md transition-all ${
                activeTab === 'metrics'
                  ? 'bg-primary-electric text-white'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              核心指标 ({result.metrics.length})
            </button>
            <button
              onClick={() => setActiveTab('risks')}
              className={`flex-1 py-2 text-sm rounded-md transition-all ${
                activeTab === 'risks'
                  ? 'bg-primary-electric text-white'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              风险提示 ({result.risks.length})
            </button>
          </div>

          {/* Content */}
          {activeTab === 'metrics' ? (
            <div className="space-y-6 animate-fade-in">
              <KpiGrid metrics={result.metrics} />
              <MetricsChart metrics={result.metrics} />
            </div>
          ) : (
            <div className="animate-fade-in">
              <RiskPanel risks={result.risks} />
            </div>
          )}
        </div>
      </div>

      {/* Q&A Floater */}
      <ChatFloater versionId={result.version_id} />
    </div>
  );
}
