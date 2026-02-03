/**
 * Admin console page (optional).
 *
 * Route: /admin
 * Features: DLQ replay, audit log viewer.
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/client';

interface AuditLogEntry {
  log_id: string;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  user_id: string | null;
  detail: Record<string, unknown> | null;
  created_at: string | null;
}

export default function AdminConsolePage() {
  const navigate = useNavigate();
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetch = async () => {
      try {
        const token = localStorage.getItem('access_token');
        if (!token) {
          await apiClient.devLogin();
        }
        const res = await (apiClient as any).http.get('/admin/audit-logs');
        setLogs(res.data.data || []);
      } catch {
        // Not admin or no data
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, []);

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/')} className="text-text-muted hover:text-text-primary">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <h1 className="text-2xl font-bold text-text-primary">Admin Console</h1>
          </div>
        </div>

        {/* Audit Logs */}
        <div className="glass-card p-6">
          <h2 className="text-text-primary font-medium mb-4">Audit Logs</h2>

          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="skeleton h-12 rounded-lg" />
              ))}
            </div>
          ) : logs.length === 0 ? (
            <p className="text-text-muted text-sm text-center py-8">No audit logs found</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-text-secondary text-left border-b border-white/10">
                    <th className="pb-3 pr-4">Action</th>
                    <th className="pb-3 pr-4">Resource</th>
                    <th className="pb-3 pr-4">User</th>
                    <th className="pb-3">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <tr key={log.log_id} className="border-b border-white/5 hover:bg-surface-elevated/30">
                      <td className="py-3 pr-4 text-text-primary">{log.action}</td>
                      <td className="py-3 pr-4 text-text-secondary">
                        {log.resource_type}:{log.resource_id?.slice(0, 12)}...
                      </td>
                      <td className="py-3 pr-4 text-text-muted">{log.user_id?.slice(0, 12)}...</td>
                      <td className="py-3 text-text-muted">{log.created_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
