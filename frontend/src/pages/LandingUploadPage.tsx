/**
 * F2 – Landing & Upload page.
 *
 * Route: /
 * Features: Drag-drop frosted card, chunked upload with progress bar, error handling.
 */

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/client';
import { useAppStore } from '../stores/appStore';

const CHUNK_SIZE = 5 * 1024 * 1024; // 5 MB

export default function LandingUploadPage() {
  const navigate = useNavigate();
  const { token, setAuth, setCurrentDoc, setCurrentJob } = useAppStore();

  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [stage, setStage] = useState<string>('');

  // Auto-login for dev
  const ensureAuth = useCallback(async () => {
    if (!token) {
      const res = await apiClient.devLogin();
      setAuth(res.access_token, res.tenant_id, res.user_id);
    }
  }, [token, setAuth]);

  const handleUpload = useCallback(
    async (file: File) => {
      setUploading(true);
      setError(null);
      setProgress(0);

      try {
        await ensureAuth();

        // 1. Init upload
        setStage('Initializing...');
        const totalParts = Math.ceil(file.size / CHUNK_SIZE);
        const { upload_id, doc_id } = await apiClient.initUpload(
          file.name,
          file.size,
          totalParts
        );

        // 2. Chunked upload
        setStage('Uploading...');
        for (let i = 0; i < totalParts; i++) {
          const start = i * CHUNK_SIZE;
          const end = Math.min(start + CHUNK_SIZE, file.size);
          const chunk = await file.slice(start, end).arrayBuffer();
          await apiClient.uploadPart(upload_id, i, chunk);
          setProgress(Math.round(((i + 1) / totalParts) * 60));
        }

        // 3. Complete upload
        setStage('Merging...');
        setProgress(65);
        await apiClient.completeUpload(upload_id);

        // 4. Fetch version & start job
        setStage('Starting analysis...');
        setProgress(70);
        const versions = await apiClient.listVersions(doc_id);
        const version = versions[0];
        setCurrentDoc(doc_id, version.version_id);

        const job = await apiClient.createJob(version.version_id);
        setCurrentJob(job.job_id, job);
        setProgress(100);

        // Navigate to processing page
        navigate(`/jobs/${job.job_id}`);
      } catch (err: any) {
        setError(err?.response?.data?.message || err?.message || 'Upload failed');
      } finally {
        setUploading(false);
      }
    },
    [ensureAuth, navigate, setCurrentDoc, setCurrentJob]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (files) => files[0] && handleUpload(files[0]),
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    disabled: uploading,
  });

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8">
      {/* Header */}
      <div className="text-center mb-12 animate-fade-in">
        <h1 className="text-4xl font-bold text-text-primary mb-3">
          年报智能解析平台
        </h1>
        <p className="text-text-secondary text-lg">
          上传年报 PDF，AI 自动解析关键指标、风险与洞察
        </p>
      </div>

      {/* Upload Card */}
      <div
        {...getRootProps()}
        className={`
          glass-card w-full max-w-xl p-12 text-center cursor-pointer
          transition-all duration-300 animate-slide-up
          ${isDragActive ? 'border-primary-electric shadow-glow scale-[1.02]' : ''}
          ${uploading ? 'pointer-events-none opacity-80' : 'hover:shadow-glow hover:border-white/20'}
        `}
      >
        <input {...getInputProps()} />

        {!uploading ? (
          <>
            <div className="mb-6">
              <svg
                className="mx-auto h-16 w-16 text-text-muted"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
            </div>
            <p className="text-text-primary text-lg mb-2">
              {isDragActive ? '释放文件以上传' : '拖拽 PDF 到此处，或点击选择'}
            </p>
            <p className="text-text-muted text-sm">
              支持扫描件和电子版年报，最大 200 MB
            </p>
          </>
        ) : (
          <div className="space-y-4">
            <p className="text-text-primary text-lg">{stage}</p>
            {/* Progress bar */}
            <div className="w-full bg-surface rounded-full h-3 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-primary-electric to-primary-hover rounded-full transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-text-secondary text-sm">{progress}%</p>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="mt-6 glass-card border-status-risk-light/50 p-4 max-w-xl w-full animate-slide-up">
          <p className="text-status-risk-light text-sm">{error}</p>
        </div>
      )}

      {/* Footer hint */}
      <p className="mt-8 text-text-muted text-xs">
        ReportLens v1.0 &middot; B2B FinTech
      </p>
    </div>
  );
}
