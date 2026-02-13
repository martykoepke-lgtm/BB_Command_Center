import { clsx } from 'clsx';

type Status = 'active' | 'on_track' | 'at_risk' | 'blocked' | 'on_hold' | 'completed' | 'cancelled' | 'overdue' |
  'submitted' | 'under_review' | 'accepted' | 'declined' | 'converted' |
  'open' | 'in_progress' | 'not_started' | 'skipped' | 'pending' | 'running' | 'failed';

const statusColors: Record<string, string> = {
  active: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  on_track: 'bg-green-500/20 text-green-400 border-green-500/30',
  at_risk: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  blocked: 'bg-red-500/20 text-red-400 border-red-500/30',
  overdue: 'bg-red-500/20 text-red-400 border-red-500/30',
  on_hold: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  completed: 'bg-green-500/20 text-green-400 border-green-500/30',
  cancelled: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  submitted: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  under_review: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  accepted: 'bg-green-500/20 text-green-400 border-green-500/30',
  declined: 'bg-red-500/20 text-red-400 border-red-500/30',
  converted: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  open: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  in_progress: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  not_started: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  skipped: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  pending: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  running: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  failed: 'bg-red-500/20 text-red-400 border-red-500/30',
};

const formatLabel = (status: string) =>
  status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

interface StatusBadgeProps {
  status: Status | string;
  size?: 'sm' | 'md';
  className?: string;
}

export function StatusBadge({ status, size = 'md', className }: StatusBadgeProps) {
  const colors = statusColors[status] ?? 'bg-gray-500/20 text-gray-400 border-gray-500/30';
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full border font-medium',
        size === 'sm' ? 'px-1.5 py-0.5 text-[10px]' : 'px-2 py-0.5 text-xs',
        colors,
        className,
      )}
    >
      {formatLabel(status)}
    </span>
  );
}
