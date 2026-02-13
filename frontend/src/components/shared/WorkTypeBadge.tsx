import { Briefcase, MessageSquare, ClipboardList } from 'lucide-react';
import type { WorkItemType } from '@/types/api';

const CONFIG: Record<string, { label: string; color: string; icon: typeof Briefcase }> = {
  initiative: { label: 'Initiative', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30', icon: Briefcase },
  consultation: { label: 'Consultation', color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30', icon: MessageSquare },
  work_assignment: { label: 'Work Assignment', color: 'bg-orange-500/20 text-orange-400 border-orange-500/30', icon: ClipboardList },
};

export function WorkTypeBadge({ type }: { type: WorkItemType | string | null | undefined }) {
  const cfg = CONFIG[type ?? 'initiative'] ?? CONFIG.initiative;
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded border ${cfg.color}`}>
      <Icon size={10} />
      {cfg.label}
    </span>
  );
}
