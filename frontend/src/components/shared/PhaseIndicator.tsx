import { clsx } from 'clsx';
import type { PhaseName, PhaseStatus } from '@/types/api';

const PHASES: PhaseName[] = ['define', 'measure', 'analyze', 'improve', 'control'];

const phaseLabels: Record<PhaseName, string> = {
  define: 'D',
  measure: 'M',
  analyze: 'A',
  improve: 'I',
  control: 'C',
};

interface PhaseIndicatorProps {
  currentPhase: string;
  phaseProgress?: Record<string, number>;
  phaseStatuses?: Partial<Record<PhaseName, PhaseStatus>>;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function PhaseIndicator({
  currentPhase,
  phaseProgress,
  phaseStatuses,
  size = 'md',
  className,
}: PhaseIndicatorProps) {
  const currentIdx = PHASES.indexOf(currentPhase as PhaseName);

  const getPhaseState = (phase: PhaseName, idx: number) => {
    if (phaseStatuses?.[phase] === 'completed') return 'completed';
    if (phaseStatuses?.[phase] === 'skipped') return 'skipped';
    if (idx === currentIdx) return 'active';
    if (idx < currentIdx && currentIdx >= 0) return 'completed';
    return 'upcoming';
  };

  const sizeClasses = {
    sm: 'w-5 h-5 text-[9px]',
    md: 'w-7 h-7 text-xs',
    lg: 'w-9 h-9 text-sm',
  };

  const lineSize = {
    sm: 'w-3 h-0.5',
    md: 'w-5 h-0.5',
    lg: 'w-8 h-0.5',
  };

  return (
    <div className={clsx('flex items-center', className)}>
      {PHASES.map((phase, idx) => {
        const state = getPhaseState(phase, idx);
        const progress = phaseProgress?.[phase] ?? 0;

        return (
          <div key={phase} className="flex items-center">
            <div
              className={clsx(
                'rounded-full flex items-center justify-center font-semibold transition-colors',
                sizeClasses[size],
                state === 'completed' && 'bg-green-500 text-white',
                state === 'active' && 'bg-brand-500 text-white ring-2 ring-brand-400/50',
                state === 'upcoming' && 'bg-surface-hover text-surface-muted',
                state === 'skipped' && 'bg-surface-hover text-surface-muted line-through',
              )}
              title={`${phase.charAt(0).toUpperCase() + phase.slice(1)}: ${Math.round(progress * 100)}%`}
            >
              {phaseLabels[phase]}
            </div>
            {idx < PHASES.length - 1 && (
              <div
                className={clsx(
                  lineSize[size],
                  idx < currentIdx ? 'bg-green-500' : 'bg-surface-hover',
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
