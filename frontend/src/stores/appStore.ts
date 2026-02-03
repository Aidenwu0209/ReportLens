/**
 * Zustand global store – holds auth, current doc/version/job state,
 * active highlights, and Q&A session reference.
 */

import { create } from 'zustand';
import type { DashboardResult, EvidenceRef, JobOut } from '../types/api';

interface AppState {
  // Auth
  token: string | null;
  tenantId: string | null;
  userId: string | null;

  // Upload → Job flow
  currentDocId: string | null;
  currentVersionId: string | null;
  currentJobId: string | null;
  currentJob: JobOut | null;

  // Dashboard result
  dashboardResult: DashboardResult | null;

  // Highlight
  activeHighlights: EvidenceRef[];
  activePage: number;

  // Q&A
  chatSessionId: string | null;

  // Actions
  setAuth: (token: string, tenantId: string, userId: string) => void;
  setCurrentDoc: (docId: string, versionId: string) => void;
  setCurrentJob: (jobId: string, job?: JobOut) => void;
  setDashboardResult: (result: DashboardResult) => void;
  setHighlights: (refs: EvidenceRef[], page?: number) => void;
  clearHighlights: () => void;
  setChatSession: (sessionId: string) => void;
  reset: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  token: localStorage.getItem('access_token'),
  tenantId: localStorage.getItem('tenant_id'),
  userId: localStorage.getItem('user_id'),

  currentDocId: null,
  currentVersionId: null,
  currentJobId: null,
  currentJob: null,
  dashboardResult: null,
  activeHighlights: [],
  activePage: 1,
  chatSessionId: null,

  setAuth: (token, tenantId, userId) =>
    set({ token, tenantId, userId }),

  setCurrentDoc: (docId, versionId) =>
    set({ currentDocId: docId, currentVersionId: versionId }),

  setCurrentJob: (jobId, job) =>
    set({ currentJobId: jobId, currentJob: job ?? null }),

  setDashboardResult: (result) =>
    set({ dashboardResult: result }),

  setHighlights: (refs, page) =>
    set({
      activeHighlights: refs,
      activePage: page ?? (refs.length > 0 ? refs[0].page_no : 1),
    }),

  clearHighlights: () =>
    set({ activeHighlights: [], activePage: 1 }),

  setChatSession: (sessionId) =>
    set({ chatSessionId: sessionId }),

  reset: () =>
    set({
      currentDocId: null,
      currentVersionId: null,
      currentJobId: null,
      currentJob: null,
      dashboardResult: null,
      activeHighlights: [],
      activePage: 1,
      chatSessionId: null,
    }),
}));
