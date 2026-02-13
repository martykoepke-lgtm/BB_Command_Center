import { clsx } from 'clsx';
import type { Methodology } from '@/types/api';

const methodologyConfig: Record<Methodology, { color: string; label: string }> = {
  DMAIC: { color: 'bg-blue-500/20 text-blue-400', label: 'DMAIC' },
  Kaizen: { color: 'bg-amber-500/20 text-amber-400', label: 'Kaizen' },
  A3: { color: 'bg-purple-500/20 text-purple-400', label: 'A3' },
  PDSA: { color: 'bg-cyan-500/20 text-cyan-400', label: 'PDSA' },
  custom: { color: 'bg-gray-500/20 text-gray-400', label: 'Custom' },
};

interface MethodologyBadgeProps {
  methodology: Methodology;
  className?: string;
}

export function MethodologyBadge({ methodology, className }: MethodologyBadgeProps) {
  const config = methodologyConfig[methodology];
  return (
    <span className={clsx('badge font-mono', config.color, className)}>
      {config.label}
    </span>
  );
}
