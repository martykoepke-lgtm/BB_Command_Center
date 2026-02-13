import { useEffect, useState } from 'react';
import { Plus, CheckSquare, Clock, AlertTriangle } from 'lucide-react';
import { actionsApi } from '@/api/actions';
import type { ActionItemOut } from '@/types/api';
import { PriorityTag } from '@/components/shared/PriorityTag';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { PageLoader } from '@/components/shared/LoadingSpinner';
import { EmptyState } from '@/components/shared/EmptyState';

function isOverdue(d: string | null): boolean { if (!d) return false; return new Date(d) < new Date(); }
function isDueThisWeek(d: string | null): boolean {
  if (!d) return false;
  const due = new Date(d), now = new Date();
  return due >= now && due <= new Date(now.getTime() + 7*24*60*60*1000);
}

function ActionColumn({ title, icon, items, color }: { title: string; icon: React.ReactNode; items: ActionItemOut[]; color: string }) {
  return (
    <div className={`rounded-lg border-t-2 ${color} bg-surface-bg p-3`}>
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="flex items-center gap-2">{icon}<span className="text-xs font-semibold text-gray-300 uppercase">{title}</span></div>
        <span className="text-[10px] font-mono text-surface-muted">{items.length}</span>
      </div>
      <div className="space-y-2">
        {items.map((item) => (
          <div key={item.id} className="card-hover p-3">
            <p className="text-xs font-medium text-gray-200 mb-1.5">{item.title}</p>
            <div className="flex items-center gap-1.5"><PriorityTag priority={item.priority} /><StatusBadge status={item.status} size="sm" /></div>
            {item.due_date && <p className={`text-[10px] font-mono mt-1.5 ${isOverdue(item.due_date) ? 'text-red-400' : 'text-surface-muted'}`}>Due {new Date(item.due_date).toLocaleDateString()}</p>}
          </div>
        ))}
        {items.length === 0 && <p className="text-xs text-surface-muted text-center py-4">No items</p>}
      </div>
    </div>
  );
}

export function ActionBoard() {
  const [actions, setActions] = useState<ActionItemOut[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { actionsApi.list({ page_size: 200 }).then((r) => setActions(r.items)).catch(() => setActions([])).finally(() => setLoading(false)); }, []);
  if (loading) return <PageLoader />;
  if (actions.length === 0) return <EmptyState icon={<CheckSquare size={40} />} title="No action items" description="Action items will appear here when created from initiative phases." />;
  const open = actions.filter((a) => a.status !== 'completed' && a.status !== 'cancelled');
  const overdue = open.filter((a) => isOverdue(a.due_date));
  const week = open.filter((a) => !isOverdue(a.due_date) && isDueThisWeek(a.due_date));
  const rest = open.filter((a) => !isOverdue(a.due_date) && !isDueThisWeek(a.due_date));
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between"><h2 className="text-lg font-semibold text-gray-100">Action Items</h2><button className="btn-primary btn-sm"><Plus size={14} /> New Action</button></div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <ActionColumn title="Overdue" icon={<AlertTriangle size={14} className="text-red-400" />} items={overdue} color="border-red-500/50" />
        <ActionColumn title="Due This Week" icon={<Clock size={14} className="text-yellow-400" />} items={week} color="border-yellow-500/50" />
        <ActionColumn title="Open" icon={<CheckSquare size={14} className="text-blue-400" />} items={rest} color="border-blue-500/50" />
      </div>
    </div>
  );
}
