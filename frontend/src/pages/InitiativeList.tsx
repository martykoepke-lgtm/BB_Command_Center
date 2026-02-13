import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, LayoutGrid, List, Filter, Target, Briefcase, MessageSquare, ClipboardList } from 'lucide-react';
import { initiativesApi } from '@/api/initiatives';
import type { InitiativeSummary, PhaseName, WorkItemType, Methodology, Priority } from '@/types/api';
import { useUIStore } from '@/stores/uiStore';
import { useInitiativeStore } from '@/stores/initiativeStore';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { PriorityTag } from '@/components/shared/PriorityTag';
import { PhaseIndicator } from '@/components/shared/PhaseIndicator';
import { MethodologyBadge } from '@/components/shared/MethodologyBadge';
import { WorkTypeBadge } from '@/components/shared/WorkTypeBadge';
import { DataTable, type Column } from '@/components/shared/DataTable';
import { EmptyState } from '@/components/shared/EmptyState';
import { PageLoader } from '@/components/shared/LoadingSpinner';
import { Modal } from '@/components/shared/Modal';

/* ------------------------------------------------------------------ */
/* Kanban Board                                                        */
/* ------------------------------------------------------------------ */

function KanbanBoard({ initiatives, onSelect }: { initiatives: InitiativeSummary[]; onSelect: (id: string) => void }) {
  const dmaicCols: { phase: PhaseName; label: string; color: string }[] = [
    { phase: 'define', label: 'Define', color: 'border-blue-500/50' },
    { phase: 'measure', label: 'Measure', color: 'border-purple-500/50' },
    { phase: 'analyze', label: 'Analyze', color: 'border-yellow-500/50' },
    { phase: 'improve', label: 'Improve', color: 'border-green-500/50' },
    { phase: 'control', label: 'Control', color: 'border-teal-500/50' },
  ];

  const fullInitiatives = initiatives.filter(
    (i) => !i.initiative_type || i.initiative_type === 'initiative',
  );
  const nonInitiatives = initiatives.filter(
    (i) => i.initiative_type === 'consultation' || i.initiative_type === 'work_assignment',
  );

  return (
    <div className="space-y-4">
      {/* Active consultations / work assignments */}
      {nonInitiatives.length > 0 && (
        <div className="rounded-lg border border-surface-border bg-surface-bg p-3">
          <div className="flex items-center gap-2 mb-3 px-1">
            <span className="text-xs font-semibold text-gray-300 uppercase">Active Work</span>
            <span className="text-[10px] font-mono text-surface-muted">{nonInitiatives.length}</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
            {nonInitiatives.map((item) => (
              <div key={item.id} className="card-hover p-3 cursor-pointer" onClick={() => onSelect(item.id)}>
                <div className="flex items-center gap-1.5 mb-1">
                  <span className="text-[10px] font-mono text-surface-muted">{item.initiative_number}</span>
                  <WorkTypeBadge type={item.initiative_type} />
                  <PriorityTag priority={item.priority} />
                </div>
                <p className="text-xs font-medium text-gray-200 line-clamp-2">{item.title}</p>
                <div className="flex items-center gap-1.5 mt-2">
                  <StatusBadge status={item.status} size="sm" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* DMAIC Kanban */}
      <div className="grid grid-cols-5 gap-3 min-h-[400px]">
        {dmaicCols.map(({ phase, label, color }) => {
          const items = fullInitiatives.filter((i) => i.current_phase === phase && i.status === 'active');
          return (
            <div key={phase} className={`rounded-lg border-t-2 ${color} bg-surface-bg p-2`}>
              <div className="flex items-center justify-between mb-3 px-1">
                <span className="text-xs font-semibold text-gray-300 uppercase">{label}</span>
                <span className="text-[10px] font-mono text-surface-muted">{items.length}</span>
              </div>
              <div className="space-y-2">
                {items.map((item) => (
                  <div key={item.id} className="card-hover p-3 cursor-pointer" onClick={() => onSelect(item.id)}>
                    <div className="flex items-center gap-1.5 mb-1">
                      <span className="text-[10px] font-mono text-surface-muted">{item.initiative_number}</span>
                      <PriorityTag priority={item.priority} />
                    </div>
                    <p className="text-xs font-medium text-gray-200 line-clamp-2">{item.title}</p>
                    <div className="flex items-center gap-1.5 mt-2">
                      <MethodologyBadge methodology={item.methodology} />
                      <StatusBadge status={item.status} size="sm" />
                    </div>
                  </div>
                ))}
                {items.length === 0 && <p className="text-xs text-surface-muted text-center py-4">No items</p>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Create Work Item Modal                                              */
/* ------------------------------------------------------------------ */

const TYPE_OPTIONS: { value: WorkItemType; label: string; desc: string; icon: typeof Briefcase; color: string }[] = [
  { value: 'initiative', label: 'Initiative', desc: 'Full methodology-driven improvement project (DMAIC, A3, etc.)', icon: Briefcase, color: 'border-blue-500 bg-blue-500/10 text-blue-400' },
  { value: 'consultation', label: 'Consultation', desc: 'Advisory engagement — no formal methodology phases', icon: MessageSquare, color: 'border-emerald-500 bg-emerald-500/10 text-emerald-400' },
  { value: 'work_assignment', label: 'Work Assignment', desc: 'Simple task or project — track progress without phases', icon: ClipboardList, color: 'border-orange-500 bg-orange-500/10 text-orange-400' },
];

function CreateWorkItemModal({ onClose, onCreated }: { onClose: () => void; onCreated: (id: string) => void }) {
  const [workType, setWorkType] = useState<WorkItemType>('initiative');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    title: '',
    problem_statement: '',
    desired_outcome: '',
    methodology: 'DMAIC' as Methodology,
    priority: 'medium' as Priority,
    scope: '',
  });

  const update = (field: string, value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const canSubmit = form.title.trim().length >= 5 && form.problem_statement.trim().length >= 10 && form.desired_outcome.trim().length >= 10;

  const handleSubmit = async () => {
    setError('');
    setSubmitting(true);
    try {
      const result = await initiativesApi.create({
        title: form.title,
        problem_statement: form.problem_statement,
        desired_outcome: form.desired_outcome,
        initiative_type: workType,
        methodology: workType === 'initiative' ? form.methodology : undefined,
        priority: form.priority,
        scope: form.scope || undefined,
      });
      onCreated(result.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Creation failed');
      setSubmitting(false);
    }
  };

  return (
    <Modal open title="Create Work Item" size="lg" onClose={onClose}
      footer={
        <>
          <button onClick={onClose} className="btn-ghost btn-sm">Cancel</button>
          <button onClick={handleSubmit} disabled={!canSubmit || submitting} className="btn-primary btn-sm">
            <Plus size={14} /> {submitting ? 'Creating...' : 'Create'}
          </button>
        </>
      }
    >
      <div className="space-y-5">
        {/* Work type selector */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Work Type</label>
          <div className="grid grid-cols-3 gap-3">
            {TYPE_OPTIONS.map((opt) => {
              const Icon = opt.icon;
              const selected = workType === opt.value;
              return (
                <button key={opt.value} type="button" onClick={() => setWorkType(opt.value)}
                  className={`p-3 rounded-lg border-2 text-left transition-all ${
                    selected ? opt.color : 'border-surface-border bg-surface-bg text-surface-muted hover:border-gray-600'
                  }`}>
                  <div className="flex items-center gap-2 mb-1">
                    <Icon size={14} />
                    <span className="text-sm font-semibold">{opt.label}</span>
                  </div>
                  <p className="text-[11px] leading-snug opacity-80">{opt.desc}</p>
                </button>
              );
            })}
          </div>
        </div>

        {/* Common fields */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Title</label>
          <input value={form.title} onChange={(e) => update('title', e.target.value)}
            className="input-field" placeholder="Brief descriptive title" autoFocus />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Problem Statement</label>
          <textarea value={form.problem_statement} onChange={(e) => update('problem_statement', e.target.value)}
            className="input-field h-20 resize-none" placeholder="What is the problem or opportunity?" />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Desired Outcome</label>
          <textarea value={form.desired_outcome} onChange={(e) => update('desired_outcome', e.target.value)}
            className="input-field h-20 resize-none" placeholder="What does success look like?" />
        </div>

        <div className="grid grid-cols-2 gap-4">
          {/* Methodology — only for full initiatives */}
          {workType === 'initiative' && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Methodology</label>
              <select value={form.methodology} onChange={(e) => update('methodology', e.target.value)} className="input-field">
                <option value="DMAIC">DMAIC</option>
                <option value="A3">A3</option>
                <option value="PDSA">PDSA</option>
                <option value="Kaizen">Kaizen</option>
              </select>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Priority</label>
            <select value={form.priority} onChange={(e) => update('priority', e.target.value)} className="input-field">
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Scope <span className="text-surface-muted">(optional)</span></label>
          <textarea value={form.scope} onChange={(e) => update('scope', e.target.value)}
            className="input-field h-16 resize-none" placeholder="What's in scope for this work?" />
        </div>

        {error && (
          <div className="px-3 py-2 rounded-md bg-red-500/10 border border-red-500/30 text-sm text-red-400">{error}</div>
        )}
      </div>
    </Modal>
  );
}

/* ------------------------------------------------------------------ */
/* Main Page                                                           */
/* ------------------------------------------------------------------ */

export function InitiativeList() {
  const navigate = useNavigate();
  const { viewMode, setViewMode } = useUIStore();
  const { initiatives, total, page, isLoading, setInitiatives, setLoading, setPage } = useInitiativeStore();
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => {
    setLoading(true);
    initiativesApi.list({
      status: statusFilter || undefined,
      initiative_type: typeFilter || undefined,
      page,
      page_size: 50,
    }).then((res) => setInitiatives(res.items, res.total))
      .catch(() => setInitiatives([], 0));
  }, [page, statusFilter, typeFilter, setInitiatives, setLoading]);

  const columns: Column<InitiativeSummary>[] = [
    { key: 'initiative_number', header: '#', width: '90px', sortable: true, render: (r: InitiativeSummary) => <span className="font-mono text-xs text-brand-400">{r.initiative_number}</span> },
    { key: 'title', header: 'Title', sortable: true },
    { key: 'initiative_type', header: 'Type', width: '120px', render: (r: InitiativeSummary) => <WorkTypeBadge type={r.initiative_type} /> },
    { key: 'methodology', header: 'Method', width: '80px', render: (r: InitiativeSummary) => (
      r.initiative_type && r.initiative_type !== 'initiative' ? <span className="text-xs text-surface-muted">—</span> : <MethodologyBadge methodology={r.methodology} />
    ) },
    { key: 'priority', header: 'Priority', width: '80px', render: (r: InitiativeSummary) => <PriorityTag priority={r.priority} /> },
    { key: 'status', header: 'Status', width: '100px', render: (r: InitiativeSummary) => <StatusBadge status={r.status} size="sm" /> },
    { key: 'current_phase', header: 'Phase', width: '180px', render: (r: InitiativeSummary) => (
      r.initiative_type && r.initiative_type !== 'initiative'
        ? <span className="text-xs text-gray-400 capitalize">{r.current_phase.replace(/_/g, ' ')}</span>
        : <PhaseIndicator currentPhase={r.current_phase as PhaseName} size="sm" />
    ) },
  ];

  const statuses = ['', 'active', 'on_hold', 'completed', 'cancelled'];
  const workTypes = ['', 'initiative', 'consultation', 'work_assignment'];
  const workTypeLabels: Record<string, string> = { '': 'All Types', initiative: 'Initiatives', consultation: 'Consultations', work_assignment: 'Work Assignments' };

  if (isLoading && initiatives.length === 0) return <PageLoader />;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-gray-100">Initiatives</h2>
          <span className="badge bg-surface-hover text-gray-400">{total}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center border border-surface-border rounded-md overflow-hidden">
            <button onClick={() => setViewMode('board')} className={`p-1.5 ${viewMode === 'board' ? 'bg-brand-500/20 text-brand-400' : 'text-surface-muted hover:text-gray-200'}`} title="Board"><LayoutGrid size={14} /></button>
            <button onClick={() => setViewMode('list')} className={`p-1.5 ${viewMode === 'list' ? 'bg-brand-500/20 text-brand-400' : 'text-surface-muted hover:text-gray-200'}`} title="List"><List size={14} /></button>
          </div>
          <button onClick={() => setShowCreate(true)} className="btn-primary btn-sm"><Plus size={14} /> New</button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 flex-wrap">
        {/* Status filter */}
        <div className="flex items-center gap-2">
          <Filter size={14} className="text-surface-muted" />
          {statuses.map((s) => (
            <button key={s || 'all'} onClick={() => { setStatusFilter(s); setPage(1); }}
              className={`btn-sm rounded-full ${statusFilter === s ? 'bg-brand-500/20 text-brand-400' : 'btn-ghost'}`}>
              {s ? s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) : 'All'}
            </button>
          ))}
        </div>
        {/* Work type filter */}
        <div className="flex items-center gap-2 border-l border-surface-border pl-4">
          {workTypes.map((t) => (
            <button key={t || 'all-types'} onClick={() => { setTypeFilter(t); setPage(1); }}
              className={`btn-sm rounded-full ${typeFilter === t ? 'bg-brand-500/20 text-brand-400' : 'btn-ghost'}`}>
              {workTypeLabels[t]}
            </button>
          ))}
        </div>
      </div>

      {initiatives.length === 0 ? (
        <EmptyState icon={<Target size={40} />} title="No initiatives yet" description="Create your first work item to get started." />
      ) : viewMode === 'board' ? (
        <KanbanBoard initiatives={initiatives} onSelect={(id) => navigate(`/initiatives/${id}`)} />
      ) : (
        <div className="card overflow-hidden">
          <DataTable columns={columns} data={initiatives}
            onRowClick={(row) => navigate(`/initiatives/${row.id}`)}
            page={page} perPage={50} total={total} onPageChange={setPage} isLoading={isLoading} dense />
        </div>
      )}

      {/* Create modal */}
      {showCreate && (
        <CreateWorkItemModal
          onClose={() => setShowCreate(false)}
          onCreated={(id) => { setShowCreate(false); navigate(`/initiatives/${id}`); }}
        />
      )}
    </div>
  );
}
