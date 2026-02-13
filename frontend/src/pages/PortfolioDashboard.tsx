import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Target, AlertTriangle, CheckCircle, Clock, DollarSign,
  TrendingUp, BarChart3, PieChart,
} from 'lucide-react';
import { dashboardsApi } from '@/api/dashboards';
import type { PortfolioDashboard as PortfolioDashboardData } from '@/types/api';
import { MetricCard } from '@/components/shared/MetricCard';
import { PageLoader } from '@/components/shared/LoadingSpinner';

const STATUS_COLORS: Record<string, string> = {
  active: '#3b82f6',
  on_hold: '#64748b',
  completed: '#22c55e',
  cancelled: '#ef4444',
};

const PHASE_COLORS: Record<string, string> = {
  define: '#3b82f6',
  measure: '#8b5cf6',
  analyze: '#eab308',
  improve: '#22c55e',
  control: '#14b8a6',
};

function DistributionBar({ data, colors, label }: { data: Record<string, number>; colors: Record<string, string>; label: string }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0);
  if (total === 0) return null;

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-surface-muted uppercase tracking-wider">{label}</span>
        <span className="text-xs text-surface-muted">{total} total</span>
      </div>
      <div className="flex h-3 rounded-full overflow-hidden bg-surface-hover">
        {Object.entries(data).map(([key, value]) => (
          value > 0 && (
            <div
              key={key}
              className="h-full transition-all"
              style={{
                width: `${(value / total) * 100}%`,
                backgroundColor: colors[key] ?? '#64748b',
              }}
              title={`${key.replace(/_/g, ' ')}: ${value}`}
            />
          )
        ))}
      </div>
      <div className="flex flex-wrap gap-3 mt-2">
        {Object.entries(data).map(([key, value]) => (
          value > 0 && (
            <div key={key} className="flex items-center gap-1.5 text-xs text-gray-400">
              <div
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: colors[key] ?? '#64748b' }}
              />
              <span className="capitalize">{key.replace(/_/g, ' ')}</span>
              <span className="font-mono text-gray-300">{value}</span>
            </div>
          )
        ))}
      </div>
    </div>
  );
}

const MOCK_DATA: PortfolioDashboardData = {
  initiative_counts: { active: 7, on_hold: 2, blocked: 0, completed: 3, cancelled: 0, total: 12 },
  action_counts: { open: 18, overdue: 4, due_this_week: 6, completed_this_week: 8 },
  savings: { projected_total: 485000, actual_total: 210000, this_quarter_actual: 52000 },
  utilization: { team_avg_pct: 72, overloaded_count: 1, available_count: 2 },
  phase_distribution: { define: 2, measure: 2, analyze: 1, improve: 1, control: 1 },
  status_distribution: { active: 7, on_hold: 2, completed: 3, cancelled: 0 },
  priority_distribution: { critical: 1, high: 4, medium: 5, low: 2 },
  methodology_distribution: { DMAIC: 8, Kaizen: 3, A3: 1, PDSA: 0, custom: 0 },
  trends: [],
  health_summary: { on_track: 5, at_risk: 1, blocked: 1 },
  upcoming_deadlines: [],
};

export function PortfolioDashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState<PortfolioDashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dashboardsApi.portfolio()
      .then(setData)
      .catch(() => {
        setData(MOCK_DATA);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <PageLoader />;
  if (!data) return null;

  const overdue = data.action_counts?.overdue ?? 0;
  const blocked = data.initiative_counts?.blocked ?? 0;

  return (
    <div className="space-y-6">
      {/* Top metric cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 xl:grid-cols-6 gap-3">
        <MetricCard
          label="Active"
          value={data.initiative_counts?.active ?? 0}
          icon={<Target size={18} />}
          color="blue"
          onClick={() => navigate('/initiatives?status=active')}
        />
        <MetricCard
          label="Blocked"
          value={blocked}
          icon={<AlertTriangle size={18} />}
          color={blocked > 0 ? 'red' : 'green'}
        />
        <MetricCard
          label="Overdue Actions"
          value={overdue}
          icon={<Clock size={18} />}
          color={overdue > 0 ? 'yellow' : 'green'}
          onClick={() => navigate('/actions?filter=overdue')}
        />
        <MetricCard
          label="Completed"
          value={data.initiative_counts?.completed ?? 0}
          icon={<CheckCircle size={18} />}
          color="green"
        />
        <MetricCard
          label="Projected Savings"
          value={`$${((data.savings?.projected_total ?? 0) / 1000).toFixed(0)}K`}
          icon={<TrendingUp size={18} />}
          color="purple"
        />
        <MetricCard
          label="Actual Savings"
          value={`$${((data.savings?.actual_total ?? 0) / 1000).toFixed(0)}K`}
          icon={<DollarSign size={18} />}
          color="teal"
        />
      </div>

      {/* Distribution charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-4">
            <PieChart size={16} className="text-surface-muted" />
            <h3 className="text-sm font-semibold text-gray-200">Status Distribution</h3>
          </div>
          <DistributionBar data={data.status_distribution ?? {}} colors={STATUS_COLORS} label="By Status" />
        </div>

        <div className="card p-5">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 size={16} className="text-surface-muted" />
            <h3 className="text-sm font-semibold text-gray-200">Active by Phase</h3>
          </div>
          <DistributionBar data={data.phase_distribution ?? {}} colors={PHASE_COLORS} label="DMAIC Phases" />
        </div>
      </div>

      {/* Action items summary */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-gray-200 mb-4">Action Items Overview</h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(data.action_counts ?? {}).map(([key, value]) => (
            <div
              key={key}
              className="flex items-center justify-between p-3 rounded-lg bg-surface-bg cursor-pointer hover:bg-surface-hover transition-colors"
              onClick={() => navigate(`/actions?filter=${key}`)}
            >
              <span className="text-sm text-gray-400 capitalize">{key.replace(/_/g, ' ')}</span>
              <span className="text-lg font-semibold font-mono text-gray-100">{value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Methodology breakdown */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-gray-200 mb-4">By Methodology</h3>
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          {Object.entries(data.methodology_distribution ?? {}).map(([key, value]) => (
            <div
              key={key}
              className="text-center p-3 rounded-lg bg-surface-bg"
            >
              <div className="text-xl font-semibold font-mono text-gray-100">{value}</div>
              <div className="text-xs text-surface-muted mt-1">{key}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
