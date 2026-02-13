import { clsx } from 'clsx';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: number | string;
  change?: number;
  icon?: React.ReactNode;
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'purple' | 'teal';
  onClick?: () => void;
  className?: string;
}

const colorMap = {
  blue: 'border-blue-500/30 bg-blue-500/5',
  green: 'border-green-500/30 bg-green-500/5',
  yellow: 'border-yellow-500/30 bg-yellow-500/5',
  red: 'border-red-500/30 bg-red-500/5',
  purple: 'border-purple-500/30 bg-purple-500/5',
  teal: 'border-teal-500/30 bg-teal-500/5',
};

export function MetricCard({ label, value, change, icon, color = 'blue', onClick, className }: MetricCardProps) {
  return (
    <div
      className={clsx(
        'card p-4 border',
        colorMap[color],
        onClick && 'cursor-pointer hover:bg-surface-hover/30 transition-colors',
        className,
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-surface-muted uppercase tracking-wider">{label}</p>
          <p className="mt-1 text-2xl font-semibold text-gray-100 font-mono">{value}</p>
        </div>
        {icon && <div className="text-surface-muted">{icon}</div>}
      </div>
      {change !== undefined && (
        <div className="mt-2 flex items-center gap-1 text-xs">
          {change > 0 ? (
            <TrendingUp size={14} className="text-green-400" />
          ) : change < 0 ? (
            <TrendingDown size={14} className="text-red-400" />
          ) : (
            <Minus size={14} className="text-surface-muted" />
          )}
          <span className={change > 0 ? 'text-green-400' : change < 0 ? 'text-red-400' : 'text-surface-muted'}>
            {change > 0 ? '+' : ''}{change}%
          </span>
        </div>
      )}
    </div>
  );
}
