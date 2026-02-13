import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Target, CheckSquare, AlertTriangle, CalendarClock, Briefcase } from 'lucide-react';
import { myWorkApi, type MyWorkResponse } from '@/api/myWork';
import { MetricCard } from '@/components/shared/MetricCard';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { PriorityTag } from '@/components/shared/PriorityTag';
import { WorkTypeBadge } from '@/components/shared/WorkTypeBadge';
import type { Priority } from '@/types/api';
import { PageLoader } from '@/components/shared/LoadingSpinner';
import { EmptyState } from '@/components/shared/EmptyState';

function isOverdue(dueDate: string | null): boolean {
  if (!dueDate) return false;
  return new Date(dueDate) < new Date(new Date().toDateString());
}

function isDueThisWeek(dueDate: string | null): boolean {
  if (!dueDate) return false;
  const d = new Date(dueDate);
  const today = new Date(new Date().toDateString());
  const weekEnd = new Date(today);
  weekEnd.setDate(weekEnd.getDate() + 7);
  return d >= today && d <= weekEnd;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function MyWork() {
  const navigate = useNavigate();
  const [data, setData] = useState<MyWorkResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    myWorkApi.get()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <PageLoader />;
  if (!data) return <EmptyState icon={<Briefcase size={40} />} title="Unable to load" description="Could not fetch your work items." />;

  const { stats, initiatives, actions } = data;

  // Group actions
  const overdueActions = actions.filter((a) => isOverdue(a.due_date));
  const dueThisWeek = actions.filter((a) => !isOverdue(a.due_date) && isDueThisWeek(a.due_date));
  const otherActions = actions.filter((a) => !isOverdue(a.due_date) && !isDueThisWeek(a.due_date));

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold text-gray-100">My Work</h2>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard label="Active Initiatives" value={stats.active_initiatives} icon={<Target size={18} />} color="blue" />
        <MetricCard label="Open Actions" value={stats.open_actions} icon={<CheckSquare size={18} />} color="teal" />
        <MetricCard label="Overdue" value={stats.overdue_actions} icon={<AlertTriangle size={18} />} color="red" />
        <MetricCard label="Due This Week" value={stats.due_this_week} icon={<CalendarClock size={18} />} color="yellow" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* My Initiatives */}
        <div className="lg:col-span-1">
          <div className="card p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-gray-200">My Initiatives</h3>
              <span className="text-xs font-mono text-surface-muted">{initiatives.length}</span>
            </div>
            {initiatives.length === 0 ? (
              <p className="text-xs text-surface-muted py-4 text-center">No initiatives assigned to you.</p>
            ) : (
              <div className="space-y-2">
                {initiatives.map((init) => (
                  <div key={init.id}
                    className="p-3 rounded-lg bg-surface-bg hover:bg-surface-hover cursor-pointer transition-colors"
                    onClick={() => navigate(`/initiatives/${init.id}`)}>
                    <div className="flex items-center gap-1.5 mb-1">
                      <span className="text-[10px] font-mono text-surface-muted">{init.initiative_number}</span>
                      <WorkTypeBadge type={init.initiative_type} />
                    </div>
                    <p className="text-sm font-medium text-gray-200 line-clamp-1">{init.title}</p>
                    <div className="flex items-center gap-2 mt-2">
                      <PriorityTag priority={init.priority as Priority} />
                      <StatusBadge status={init.status} size="sm" />
                      <span className="text-[10px] text-surface-muted capitalize ml-auto">{init.current_phase.replace(/_/g, ' ')}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* My Actions */}
        <div className="lg:col-span-2">
          <div className="card p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-gray-200">My Action Items</h3>
              <span className="text-xs font-mono text-surface-muted">{actions.length}</span>
            </div>

            {actions.length === 0 ? (
              <p className="text-xs text-surface-muted py-4 text-center">No open action items assigned to you.</p>
            ) : (
              <div className="space-y-4">
                {/* Overdue */}
                {overdueActions.length > 0 && (
                  <ActionGroup label="Overdue" color="text-red-400" items={overdueActions} navigate={navigate} />
                )}

                {/* Due this week */}
                {dueThisWeek.length > 0 && (
                  <ActionGroup label="Due This Week" color="text-yellow-400" items={dueThisWeek} navigate={navigate} />
                )}

                {/* Other open */}
                {otherActions.length > 0 && (
                  <ActionGroup label="Open" color="text-gray-400" items={otherActions} navigate={navigate} />
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ---- Action Group Sub-component ---- */

interface ActionGroupProps {
  label: string;
  color: string;
  items: MyWorkResponse['actions'];
  navigate: ReturnType<typeof useNavigate>;
}

function ActionGroup({ label, color, items, navigate }: ActionGroupProps) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <span className={`text-xs font-semibold uppercase tracking-wider ${color}`}>{label}</span>
        <span className="text-[10px] font-mono text-surface-muted">{items.length}</span>
      </div>
      <div className="space-y-1.5">
        {items.map((a) => (
          <div key={a.id}
            className="flex items-center gap-3 p-3 rounded-lg bg-surface-bg hover:bg-surface-hover cursor-pointer transition-colors"
            onClick={() => navigate(`/initiatives/${a.initiative_id}`)}>
            <div className={`w-2 h-2 rounded-full shrink-0 ${
              a.status === 'in_progress' ? 'bg-yellow-500' : 'bg-blue-500'
            }`} />
            <div className="flex-1 min-w-0">
              <span className="text-sm text-gray-200 block truncate">{a.title}</span>
              {a.initiative_number && (
                <span className="text-[10px] text-surface-muted">{a.initiative_number} &middot; {a.initiative_title}</span>
              )}
            </div>
            <PriorityTag priority={a.priority as Priority} />
            {a.due_date && (
              <span className={`text-xs font-mono ${isOverdue(a.due_date) ? 'text-red-400' : 'text-surface-muted'}`}>
                {formatDate(a.due_date)}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
