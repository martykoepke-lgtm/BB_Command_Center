import { clsx } from 'clsx';

type Priority = 'critical' | 'high' | 'medium' | 'low';

const priorityConfig: Record<Priority, { color: string; label: string }> = {
  critical: { color: 'bg-red-500/20 text-red-400', label: 'Critical' },
  high: { color: 'bg-orange-500/20 text-orange-400', label: 'High' },
  medium: { color: 'bg-yellow-500/20 text-yellow-400', label: 'Medium' },
  low: { color: 'bg-green-500/20 text-green-400', label: 'Low' },
};

interface PriorityTagProps {
  priority: Priority;
  className?: string;
}

export function PriorityTag({ priority, className }: PriorityTagProps) {
  const config = priorityConfig[priority];
  return (
    <span className={clsx('badge', config.color, className)}>
      {config.label}
    </span>
  );
}
