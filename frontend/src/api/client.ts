/**
 * F6 – Typed axios client (API SDK).
 *
 * Base URL: /api/v1
 * Auth:     Bearer JWT
 * Headers:  Idempotency-Key where applicable
 */

import axios, { AxiosInstance } from 'axios';
import type {
  ApiResponse,
  ChatMessage,
  ChatSession,
  CompleteUploadResponse,
  DashboardResult,
  DevLoginResponse,
  DocumentOut,
  DocumentVersionOut,
  ExportOut,
  InitUploadResponse,
  JobOut,
} from '../types/api';

const BASE_URL = '/api/v1';

class ApiClient {
  private http: AxiosInstance;

  constructor() {
    this.http = axios.create({ baseURL: BASE_URL });
    this.http.interceptors.request.use((config) => {
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });
  }

  // ── Auth ────────────────────────────────────────────
  async devLogin(username = 'dev_admin', tenantName = 'default') {
    const res = await this.http.post<ApiResponse<DevLoginResponse>>('/auth/dev-login', {
      username,
      tenant_name: tenantName,
    });
    const data = res.data.data;
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('tenant_id', data.tenant_id);
    localStorage.setItem('user_id', data.user_id);
    return data;
  }

  // ── Upload ──────────────────────────────────────────
  async initUpload(filename: string, fileSize?: number, totalParts?: number) {
    const res = await this.http.post<ApiResponse<InitUploadResponse>>('/documents/init', {
      filename,
      file_size: fileSize,
      total_parts: totalParts,
    });
    return res.data.data;
  }

  async uploadPart(uploadId: string, partNo: number, data: ArrayBuffer) {
    await this.http.put(`/uploads/${uploadId}/parts/${partNo}`, data, {
      headers: { 'Content-Type': 'application/octet-stream' },
    });
  }

  async completeUpload(uploadId: string) {
    const res = await this.http.post<ApiResponse<CompleteUploadResponse>>(
      `/uploads/${uploadId}/complete`
    );
    return res.data.data;
  }

  // ── Documents ───────────────────────────────────────
  async getDocument(docId: string) {
    const res = await this.http.get<ApiResponse<DocumentOut>>(`/documents/${docId}`);
    return res.data.data;
  }

  async listVersions(docId: string) {
    const res = await this.http.get<ApiResponse<DocumentVersionOut[]>>(
      `/documents/${docId}/versions`
    );
    return res.data.data;
  }

  getPageImageUrl(docId: string, verId: string, pageNo: number) {
    return `${BASE_URL}/documents/${docId}/versions/${verId}/pages/${pageNo}`;
  }

  // ── Jobs ────────────────────────────────────────────
  async createJob(versionId: string, idempotencyKey?: string) {
    const res = await this.http.post<ApiResponse<JobOut>>('/jobs', {
      version_id: versionId,
      idempotency_key: idempotencyKey,
    });
    return res.data.data;
  }

  async getJob(jobId: string) {
    const res = await this.http.get<ApiResponse<JobOut>>(`/jobs/${jobId}`);
    return res.data.data;
  }

  createJobEventSource(jobId: string): EventSource {
    const token = localStorage.getItem('access_token');
    return new EventSource(`${BASE_URL}/jobs/${jobId}/events?token=${token}`);
  }

  // ── Results ─────────────────────────────────────────
  async getDashboardResult(docId: string, verId: string) {
    const res = await this.http.get<ApiResponse<DashboardResult>>(
      `/documents/${docId}/versions/${verId}/result`
    );
    return res.data.data;
  }

  // ── Exports ─────────────────────────────────────────
  async createExport(versionId: string, format = 'docx', idempotencyKey?: string) {
    const res = await this.http.post<ApiResponse<ExportOut>>('/exports', {
      version_id: versionId,
      format,
      idempotency_key: idempotencyKey,
    });
    return res.data.data;
  }

  async getExport(exportId: string) {
    const res = await this.http.get<ApiResponse<ExportOut>>(`/exports/${exportId}`);
    return res.data.data;
  }

  getExportDownloadUrl(exportId: string) {
    return `${BASE_URL}/exports/${exportId}/download`;
  }

  // ── Chat / Q&A ─────────────────────────────────────
  async createChatSession(versionId: string, title?: string) {
    const res = await this.http.post<ApiResponse<ChatSession>>('/qa/sessions', {
      version_id: versionId,
      title,
    });
    return res.data.data;
  }

  async sendMessage(sessionId: string, content: string, idempotencyKey?: string) {
    const res = await this.http.post<ApiResponse<ChatMessage>>(
      `/qa/sessions/${sessionId}/messages`,
      { content, idempotency_key: idempotencyKey }
    );
    return res.data.data;
  }

  async listMessages(sessionId: string) {
    const res = await this.http.get<ApiResponse<ChatMessage[]>>(
      `/qa/sessions/${sessionId}/messages`
    );
    return res.data.data;
  }
}

export const apiClient = new ApiClient();
export default apiClient;
