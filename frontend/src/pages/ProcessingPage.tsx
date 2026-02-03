/**
 * F3 – Processing page.
 *
 * Route: /jobs/:jobId
 * Features: Stage indicator, PDF thumbnail wall with scanning effect,
 *           skeleton screen loading for insights, SSE progress stream.
 */

import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import apiClient from '../api/client';
import { useAppStore } from '../stores/appStore';
import type { JobEventData, JobOut } from '../types/api';

const STAGES = [
  { key: 'queued', label: '排队中' },
  { key: 'preprocess', label: 'PDF 预处理' },
  { key: 'ocr', label: 'OCR 识别' },
  { key: 'extract', label: '指标提取' },
  { key: 'llm', label: 'AI 分析' },
  { key: 'done', label: '完成' },
];

export default function ProcessingPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const { setCurrentDoc } = useAppStore();

  const [job, setJob] = useState<JobOut | null>(null);
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState('queued');
  const [error, setError] = useState<string | null>(null);

  // Poll job status (fallback if SSE is not available)
  useEffect(() => {
    if (!jobId) return;

    const poll = async () => {
      try {
        const data = await apiClient.getJob(jobId);
        setJob(data);
        setProgress(data.progress);
        setStage(data.stage);

        if (data.stage === 'done') {
          setCurrentDoc(data.doc_id, data.version_id);
          setTimeout(() => navigate(`/docs/${data.doc_id}/v/${data.version_id}`), 1500);
          return;
        }

        if (data.stage === 'failed') {
          setError(data.error_message || 'Processing failed');
          return;
        }
      } catch {
        // Will retry on next interval
      }
    };

    poll();
    const interval = setInterval(poll, 2000);
    return () => clearInterval(interval);
  }, [jobId, navigate, setCurrentDoc]);

  // Find current stage index
  const currentStageIdx = STAGES.findIndex((s) => s.key === stage);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8">
      <h1 className="text-2xl font-bold text-text-primary mb-8 animate-fade-in">
        文档解析中
      </h1>

      {/* Stage indicator */}
      <div className="w-full max-w-2xl mb-10">
        <div className="flex items-center justify-between">
          {STAGES.map((s, idx) => (
            <div key={s.key} className="flex flex-col items-center flex-1">
              <div
                className={`
                  w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium
                  transition-all duration-500
                  ${
                    idx < currentStageIdx
                      ? 'bg-status-success text-white'
                      : idx === currentStageIdx
                      ? 'bg-primary-electric text-white animate-pulse-slow'
                      : 'bg-surface-elevated text-text-muted'
                  }
                `}
              >
                {idx < currentStageIdx ? (
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  idx + 1
                )}
              </div>
              <span className={`mt-2 text-xs ${
                idx <= currentStageIdx ? 'text-text-primary' : 'text-text-muted'
              }`}>
                {s.label}
              </span>
            </div>
          ))}
        </div>
        {/* Progress connector line */}
        <div className="relative w-full h-1 bg-surface-elevated rounded-full mt-4">
          <div
            className="absolute top-0 left-0 h-full bg-gradient-to-r from-primary-electric to-status-success rounded-full transition-all duration-700"
            style={{ width: `${progress}%` }}
          />
        </div>
        <p className="text-center text-text-secondary text-sm mt-2">{progress}%</p>
      </div>

      {/* Thumbnail wall with scan effect */}
      <div className="glass-card w-full max-w-2xl p-6 animate-slide-up">
        <div className="relative overflow-hidden rounded-lg bg-surface h-48 flex items-center justify-center">
          {/* Scan line effect */}
          {stage !== 'done' && stage !== 'failed' && (
            <div className="scan-line" />
          )}

          {/* Skeleton thumbnails */}
          <div className="flex gap-3 px-4 overflow-x-auto">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className={`
                  w-24 h-32 rounded-lg flex-shrink-0 transition-all duration-500
                  ${
                    i < Math.floor(progress / 16)
                      ? 'bg-primary-electric/20 border border-primary-electric/30'
                      : 'skeleton'
                  }
                `}
              />
            ))}
          </div>
        </div>

        {/* Insight skeletons */}
        <div className="mt-6 space-y-3">
          {stage === 'done' ? (
            <p className="text-status-success text-center font-medium">
              解析完成，正在跳转...
            </p>
          ) : (
            <>
              <div className="skeleton h-4 w-3/4 rounded" />
              <div className="skeleton h-4 w-1/2 rounded" />
              <div className="skeleton h-4 w-5/6 rounded" />
            </>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mt-6 glass-card border-status-risk-light/50 p-4 max-w-2xl w-full">
          <p className="text-status-risk-light text-sm">{error}</p>
          <button
            className="mt-3 text-primary-electric hover:text-primary-hover text-sm underline"
            onClick={() => navigate('/')}
          >
            返回重新上传
          </button>
        </div>
      )}
    </div>
  );
}
