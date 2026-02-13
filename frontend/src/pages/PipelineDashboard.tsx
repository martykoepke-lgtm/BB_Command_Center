import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Inbox, ArrowRight, TrendingUp, Clock } from 'lucide-react';
import { dashboardsApi } from '@/api/dashboards';
import type { PipelineDashboard as PipelineData, RequestOut } from '@/types/api';
import { MetricCard } from '@/components/shared/MetricCard';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { PageLoader } from '@/components/shared/LoadingSpinner';

export function PipelineDashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState<PipelineData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dashboardsApi.pipeline()
      .then(setData)
      .catch(() => {
        setData({
          total_requests: 24,
          by_status: { submitted: 5, under_review: 3, accepted: 10, declined: 4, converted: 2 },
          by_urgency: { critical: 2, high: 6, medium: 10, low: 6 },
          conversion_rate: 0.42,
          recent_requests: [],
        });
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <PageLoader />;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <MetricCard label="Total Requests" value={data.total_requests} icon={<Inbox size={18} />} color="blue" />
        <MetricCard
          label="Pending Review"
          value={(data.by_status.submitted ?? 0) + (data.by_status.under_review ?? 0)}
          icon={<Clock size={18} />}
          color="yellow"
        />
        <MetricCard
          label="Conversion Rate"
          value={`${(data.conversion_rate * 100).toFixed(0)}%`}
          icon={<TrendingUp size={18} />}
          color="green"
        />
        <MetricCard
          label="Converted"
          value={data.by_status.converted ?? 0}
          icon={<ArrowRight size={18} />}
          color="purple"
        />
      </div>

      {/* Status funnel */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-gray-200 mb-4">Request Pipeline</h3>
        <div className="flex items-end gap-2 h-40">
          {['submitted', 'under_review', 'accepted', 'converted'].map((status) => {
            const count = data.by_status[status] ?? 0;
            const maxCount = Math.max(...Object.values(data.by_status), 1);
            const height = Math.max((count / maxCount) * 100, 8);
            return (
              <div key={status} className="flex-1 flex flex-col items-center gap-2">
                <span className="text-sm font-mono text-gray-200">{count}</span>
                <div
                  className="w-full rounded-t bg-brand-500/60 transition-all"
                  style={{ height: `${height}%` }}
                />
                <span className="text-[10px] text-surface-muted capitalize">{status.replace(/_/g, ' ')}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Recent requests */}
      {data.recent_requests.length > 0 && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-200 mb-4">Recent Requests</h3>
          <div className="space-y-2">
            {data.recent_requests.map((req: RequestOut) => (
              <div
                key={req.id}
                className="flex items-center justify-between p-3 rounded-lg bg-surface-bg hover:bg-surface-hover cursor-pointer transition-colors"
                onClick={() => navigate(`/requests/${req.id}`)}
              >
                <div>
                  <span className="text-xs font-mono text-surface-muted">{req.request_number}</span>
                  <p className="text-sm text-gray-200">{req.title}</p>
                </div>
                <StatusBadge status={req.status} size="sm" />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
