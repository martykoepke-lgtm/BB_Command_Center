import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Calendar, FileText, BarChart3, Bot, ChevronRight, Clock, DollarSign, Plus, Trash2, Users, UserPlus } from 'lucide-react';
import { initiativesApi } from '@/api/initiatives';
import { actionsApi } from '@/api/actions';
import { notesApi } from '@/api/notes';
import { usersApi } from '@/api/users';
import { stakeholdersApi, type StakeholderOut } from '@/api/stakeholders';
import type { InitiativeOut, PhaseOut, ActionItemOut, UserOut } from '@/types/api';
import type { NoteOut } from '@/api/notes';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { PriorityTag } from '@/components/shared/PriorityTag';
import { PhaseIndicator } from '@/components/shared/PhaseIndicator';
import { MethodologyBadge } from '@/components/shared/MethodologyBadge';
import { WorkTypeBadge } from '@/components/shared/WorkTypeBadge';
import { PageLoader } from '@/components/shared/LoadingSpinner';
import { Modal } from '@/components/shared/Modal';
import { AIRefinementPanel } from '@/components/initiative/AIRefinementPanel';
import { useAIStore } from '@/stores/aiStore';

type Tab = string;

const STAKEHOLDER_ROLES = ['sponsor', 'lead', 'contributor', 'reviewer', 'informed', 'SME'] as const;

function getTabsForInitiative(init: InitiativeOut): { key: Tab; label: string }[] {
  const isFullInitiative = !init.initiative_type || init.initiative_type === 'initiative';

  if (!isFullInitiative) {
    return [
      { key: 'overview', label: 'Overview' },
      { key: 'actions', label: 'Actions' },
      { key: 'notes', label: 'Notes' },
      { key: 'stakeholders', label: 'Stakeholders' },
    ];
  }

  const baseTabs: { key: Tab; label: string }[] = [{ key: 'overview', label: 'Overview' }];

  if (init.phases && init.phases.length > 0) {
    const sorted = [...init.phases].sort((a, b) => a.phase_order - b.phase_order);
    for (const phase of sorted) {
      baseTabs.push({
        key: phase.phase_name,
        label: phase.phase_name.replace(/_/g, ' ').replace(/\b\w/g, (ch: string) => ch.toUpperCase()),
      });
    }
  } else {
    baseTabs.push(
      { key: 'define', label: 'Define' }, { key: 'measure', label: 'Measure' },
      { key: 'analyze', label: 'Analyze' }, { key: 'improve', label: 'Improve' },
      { key: 'control', label: 'Control' },
    );
  }

  baseTabs.push({ key: 'stakeholders', label: 'Stakeholders' }, { key: 'data', label: 'Data' }, { key: 'reports', label: 'Reports' });
  return baseTabs;
}

export function InitiativeProfile() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [initiative, setInitiative] = useState<InitiativeOut | null>(null);
  const [phases, setPhases] = useState<PhaseOut[]>([]);
  const [actions, setActions] = useState<ActionItemOut[]>([]);
  const [notes, setNotes] = useState<NoteOut[]>([]);
  const [stakeholders, setStakeholders] = useState<StakeholderOut[]>([]);
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [loading, setLoading] = useState(true);
  const [users, setUsers] = useState<UserOut[]>([]);
  const { setContext } = useAIStore();

  // Note creation state
  const [noteContent, setNoteContent] = useState('');
  const [noteType, setNoteType] = useState('general');
  const [noteSaving, setNoteSaving] = useState(false);

  // Action creation state
  const [actionModal, setActionModal] = useState(false);
  const [actionForm, setActionForm] = useState({ title: '', description: '', assigned_to: '', priority: 'medium', due_date: '' });
  const [actionSaving, setActionSaving] = useState(false);

  // Stakeholder add state
  const [shModal, setShModal] = useState(false);
  const [shForm, setShForm] = useState({ user_id: '', role: 'contributor' });
  const [shSaving, setShSaving] = useState(false);

  useEffect(() => {
    if (!id) return;
    setContext(id);
    Promise.all([
      initiativesApi.get(id), initiativesApi.getPhases(id),
      actionsApi.list({ initiative_id: id } as Record<string, string>).catch(() => ({ items: [], total: 0 })),
      notesApi.list(id).catch(() => []),
      usersApi.list({ page_size: 100 }).catch(() => ({ items: [] })),
      stakeholdersApi.list(id).catch(() => []),
    ]).then(([init, ph, act, n, u, sh]) => {
      setInitiative(init); setPhases(ph);
      setActions('items' in act ? (act as { items: ActionItemOut[] }).items : []);
      setNotes(n as NoteOut[]);
      setUsers('items' in u ? u.items : []);
      setStakeholders(sh as StakeholderOut[]);
    }).catch(() => navigate('/initiatives')).finally(() => setLoading(false));
    return () => setContext(null);
  }, [id, navigate, setContext]);

  if (loading) return <PageLoader />;
  if (!initiative) return null;

  const isFullInitiative = !initiative.initiative_type || initiative.initiative_type === 'initiative';
  const tabs = getTabsForInitiative(initiative);

  const assignLead = async (userId: string | null) => {
    if (!id) return;
    try {
      const updated = await initiativesApi.update(id, { lead_analyst_id: userId } as Partial<InitiativeOut>);
      setInitiative(updated);
    } catch { /* silent */ }
  };

  // Note handlers
  const addNote = async () => {
    if (!id || !noteContent.trim()) return;
    setNoteSaving(true);
    try {
      const created = await notesApi.create(id, { content: noteContent.trim(), note_type: noteType });
      setNotes((prev) => [created, ...prev]);
      setNoteContent('');
    } catch { /* silent */ }
    setNoteSaving(false);
  };

  const deleteNote = async (noteId: string) => {
    try {
      await notesApi.delete(noteId);
      setNotes((prev) => prev.filter((n) => n.id !== noteId));
    } catch { /* silent */ }
  };

  // Action handlers
  const openAddAction = () => {
    setActionForm({ title: '', description: '', assigned_to: '', priority: 'medium', due_date: '' });
    setActionModal(true);
  };

  const saveAction = async () => {
    if (!id || !actionForm.title.trim()) return;
    setActionSaving(true);
    try {
      const data: Record<string, unknown> = { initiative_id: id, title: actionForm.title.trim() };
      if (actionForm.description.trim()) data.description = actionForm.description.trim();
      if (actionForm.assigned_to) data.assigned_to = actionForm.assigned_to;
      if (actionForm.priority) data.priority = actionForm.priority;
      if (actionForm.due_date) data.due_date = actionForm.due_date;
      const created = await actionsApi.create(data as unknown as Parameters<typeof actionsApi.create>[0]);
      setActions((prev) => [...prev, created]);
      setActionModal(false);
    } catch { /* silent */ }
    setActionSaving(false);
  };

  // Stakeholder handlers
  const addStakeholder = async () => {
    if (!id || !shForm.user_id) return;
    setShSaving(true);
    try {
      const created = await stakeholdersApi.add(id, { user_id: shForm.user_id, role: shForm.role });
      setStakeholders((prev) => [...prev, created]);
      setShModal(false);
    } catch { /* silent */ }
    setShSaving(false);
  };

  const removeStakeholder = async (userId: string) => {
    if (!id) return;
    try {
      await stakeholdersApi.remove(id, userId);
      setStakeholders((prev) => prev.filter((s) => s.user_id !== userId));
    } catch { /* silent */ }
  };

  const phaseNames = phases.map((p) => p.phase_name);
  const isPhaseTab = phaseNames.includes(activeTab);

  // Users not yet added as stakeholders
  const availableUsers = users.filter((u) => !stakeholders.some((s) => s.user_id === u.id));

  return (
    <div className="space-y-4">
      <button onClick={() => navigate('/initiatives')} className="btn-ghost btn-sm">
        <ArrowLeft size={14} /> Initiatives
      </button>

      {/* Header Card */}
      <div className="card p-5">
        <div className="flex items-start justify-between mb-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-mono text-surface-muted">{initiative.initiative_number}</span>
              <WorkTypeBadge type={initiative.initiative_type} />
              {isFullInitiative && <MethodologyBadge methodology={initiative.methodology} />}
              <PriorityTag priority={initiative.priority} />
              <StatusBadge status={initiative.status} />
            </div>
            <h2 className="text-xl font-semibold text-gray-100">{initiative.title}</h2>
          </div>
          {isFullInitiative && (
            <PhaseIndicator currentPhase={initiative.current_phase} phaseProgress={initiative.phase_progress} size="md" />
          )}
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-sm mt-4">
          {initiative.start_date && (
            <div className="flex items-center gap-2 text-gray-400">
              <Calendar size={14} className="text-surface-muted" />
              <span>Started {new Date(initiative.start_date).toLocaleDateString()}</span>
            </div>
          )}
          {initiative.target_completion && (
            <div className="flex items-center gap-2 text-gray-400">
              <Clock size={14} className="text-surface-muted" />
              <span>Target {new Date(initiative.target_completion).toLocaleDateString()}</span>
            </div>
          )}
          {initiative.projected_savings != null && (
            <div className="flex items-center gap-2 text-gray-400">
              <DollarSign size={14} className="text-surface-muted" />
              <span>Projected ${initiative.projected_savings.toLocaleString()}</span>
            </div>
          )}
          {initiative.actual_savings != null && (
            <div className="flex items-center gap-2 text-green-400">
              <DollarSign size={14} />
              <span>Actual ${initiative.actual_savings.toLocaleString()}</span>
            </div>
          )}
        </div>
      </div>

      {/* Tab Bar */}
      <div className="flex items-center gap-1 border-b border-surface-border pb-0 overflow-x-auto">
        {tabs.map((tab) => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)}
            className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors -mb-px whitespace-nowrap ${
              activeTab === tab.key ? 'border-brand-500 text-brand-400' : 'border-transparent text-surface-muted hover:text-gray-300'
            }`}>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <>
              {initiative.problem_statement && (
                <div className="card p-5">
                  <h3 className="text-sm font-semibold text-gray-200 mb-2">Problem Statement</h3>
                  <p className="text-sm text-gray-400 whitespace-pre-wrap">{initiative.problem_statement}</p>
                </div>
              )}
              {initiative.desired_outcome && (
                <div className="card p-5">
                  <h3 className="text-sm font-semibold text-gray-200 mb-2">Desired Outcome</h3>
                  <p className="text-sm text-gray-400 whitespace-pre-wrap">{initiative.desired_outcome}</p>
                </div>
              )}
              {initiative.scope && (
                <div className="card p-5">
                  <h3 className="text-sm font-semibold text-gray-200 mb-2">Scope</h3>
                  <p className="text-sm text-gray-400">{initiative.scope}</p>
                </div>
              )}
              {initiative.business_case && (
                <div className="card p-5">
                  <h3 className="text-sm font-semibold text-gray-200 mb-2">Business Case</h3>
                  <p className="text-sm text-gray-400 whitespace-pre-wrap">{initiative.business_case}</p>
                </div>
              )}

              {/* Recent Notes with add form */}
              <div className="card p-5">
                <h3 className="text-sm font-semibold text-gray-200 mb-3">Notes</h3>
                <div className="flex gap-2 mb-3">
                  <textarea
                    value={noteContent}
                    onChange={(e) => setNoteContent(e.target.value)}
                    placeholder="Add a quick note..."
                    className="input-field flex-1 h-12 resize-none text-sm py-2"
                  />
                  <button onClick={addNote} disabled={!noteContent.trim() || noteSaving} className="btn-primary btn-sm self-end shrink-0">
                    {noteSaving ? '...' : 'Add'}
                  </button>
                </div>
                {notes.length > 0 ? (
                  <div className="space-y-2">
                    {notes.slice(0, 5).map((note) => (
                      <div key={note.id} className="p-3 rounded-lg bg-surface-bg group">
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-[10px] font-semibold uppercase tracking-wider text-surface-muted">{note.note_type}</span>
                              <span className="text-[10px] text-surface-muted">{new Date(note.created_at).toLocaleDateString()}</span>
                            </div>
                            <p className="text-sm text-gray-300">{note.content}</p>
                          </div>
                          <button onClick={() => deleteNote(note.id)} className="p-1 rounded opacity-0 group-hover:opacity-100 text-surface-muted hover:text-red-400 transition-all">
                            <Trash2 size={12} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-surface-muted">No notes yet.</p>
                )}
              </div>

              {/* AI Refinement */}
              <AIRefinementPanel initiative={initiative} onUpdated={(updated) => setInitiative(updated)} />
            </>
          )}

          {/* Phase Tabs (full initiative only) */}
          {isPhaseTab && (
            <div className="card p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-gray-200 capitalize">{activeTab.replace(/_/g, ' ')} Phase</h3>
                <Link to={`/initiatives/${id}/${activeTab}`} className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1">
                  Open workspace <ChevronRight size={12} />
                </Link>
              </div>
              {phases.filter((p) => p.phase_name === activeTab).map((phase) => (
                <div key={phase.id} className="space-y-3">
                  <div className="flex items-center gap-3">
                    <StatusBadge status={phase.status} size="sm" />
                    <div className="flex-1 h-2 rounded-full bg-surface-hover">
                      <div className="h-full rounded-full bg-brand-500 transition-all" style={{ width: `${phase.completeness_score * 100}%` }} />
                    </div>
                    <span className="text-xs font-mono text-surface-muted">{Math.round(phase.completeness_score * 100)}%</span>
                  </div>
                  {phase.ai_summary && (
                    <div className="p-3 rounded-lg bg-teal-500/5 border border-teal-500/20">
                      <div className="flex items-center gap-1 mb-1">
                        <Bot size={12} className="text-teal-400" />
                        <span className="text-[10px] font-semibold text-teal-400">AI Summary</span>
                      </div>
                      <p className="text-xs text-gray-400">{phase.ai_summary}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Actions Tab */}
          {activeTab === 'actions' && (
            <div className="card p-5">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-200">Action Items</h3>
                <button onClick={openAddAction} className="btn-ghost btn-sm"><Plus size={14} /> Add</button>
              </div>
              {actions.length === 0 ? (
                <p className="text-sm text-surface-muted">No action items yet.</p>
              ) : (
                <div className="space-y-2">
                  {actions.map((a) => (
                    <div key={a.id} className="flex items-center gap-3 p-3 rounded-lg bg-surface-bg">
                      <div className={`w-2 h-2 rounded-full shrink-0 ${a.status === 'completed' ? 'bg-green-500' : a.status === 'in_progress' ? 'bg-yellow-500' : 'bg-blue-500'}`} />
                      <div className="flex-1 min-w-0">
                        <span className="text-sm text-gray-200 block truncate">{a.title}</span>
                        {a.description && <p className="text-xs text-surface-muted truncate">{a.description}</p>}
                      </div>
                      <PriorityTag priority={a.priority} />
                      <StatusBadge status={a.status} size="sm" />
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Notes Tab */}
          {activeTab === 'notes' && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-200 mb-3">Notes</h3>
              <div className="mb-4 space-y-2">
                <div className="flex items-center gap-2">
                  <select value={noteType} onChange={(e) => setNoteType(e.target.value)} className="input-field text-xs py-1.5 w-36">
                    <option value="general">General</option>
                    <option value="decision">Decision</option>
                    <option value="blocker">Blocker</option>
                    <option value="meeting">Meeting</option>
                  </select>
                </div>
                <div className="flex gap-2">
                  <textarea
                    value={noteContent}
                    onChange={(e) => setNoteContent(e.target.value)}
                    placeholder="Add a note..."
                    className="input-field flex-1 h-16 resize-none text-sm py-2"
                  />
                  <button onClick={addNote} disabled={!noteContent.trim() || noteSaving} className="btn-primary btn-sm self-end shrink-0">
                    {noteSaving ? 'Saving...' : 'Add'}
                  </button>
                </div>
              </div>
              {notes.length === 0 ? (
                <p className="text-sm text-surface-muted">No notes yet.</p>
              ) : (
                <div className="space-y-2">
                  {notes.map((note) => (
                    <div key={note.id} className="p-3 rounded-lg bg-surface-bg group">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-[10px] font-semibold uppercase tracking-wider text-surface-muted">{note.note_type}</span>
                            <span className="text-[10px] text-surface-muted">{new Date(note.created_at).toLocaleDateString()}</span>
                          </div>
                          <p className="text-sm text-gray-300 whitespace-pre-wrap">{note.content}</p>
                        </div>
                        <button onClick={() => deleteNote(note.id)} className="p-1 rounded opacity-0 group-hover:opacity-100 text-surface-muted hover:text-red-400 transition-all">
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Stakeholders Tab */}
          {activeTab === 'stakeholders' && (
            <div className="card p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Users size={16} className="text-surface-muted" />
                  <h3 className="text-sm font-semibold text-gray-200">Stakeholders</h3>
                </div>
                <button onClick={() => { setShForm({ user_id: '', role: 'contributor' }); setShModal(true); }} className="btn-ghost btn-sm">
                  <UserPlus size={14} /> Add
                </button>
              </div>
              {stakeholders.length === 0 ? (
                <p className="text-sm text-surface-muted">No stakeholders assigned yet. Add team members involved in this work.</p>
              ) : (
                <div className="space-y-2">
                  {stakeholders.map((sh) => (
                    <div key={sh.user_id} className="flex items-center gap-3 p-3 rounded-lg bg-surface-bg group">
                      <div className="w-8 h-8 rounded-full bg-brand-500/20 flex items-center justify-center text-xs font-semibold text-brand-400">
                        {(sh.user_name || '?').charAt(0).toUpperCase()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <span className="text-sm text-gray-200 block truncate">{sh.user_name || 'Unknown User'}</span>
                        {sh.user_email && <span className="text-xs text-surface-muted truncate block">{sh.user_email}</span>}
                      </div>
                      <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-surface-hover text-surface-muted">
                        {sh.role}
                      </span>
                      <button onClick={() => removeStakeholder(sh.user_id)} className="p-1 rounded opacity-0 group-hover:opacity-100 text-surface-muted hover:text-red-400 transition-all">
                        <Trash2 size={12} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'data' && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-200 mb-2">Datasets & Analysis</h3>
              <button onClick={() => navigate(`/data?initiative=${id}`)} className="btn-primary btn-sm mt-3">
                <BarChart3 size={14} /> Open Data Workspace
              </button>
            </div>
          )}
          {activeTab === 'reports' && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-200 mb-2">Reports</h3>
              <button onClick={() => navigate(`/reports?initiative=${id}`)} className="btn-primary btn-sm mt-3">
                <FileText size={14} /> Open Reports
              </button>
            </div>
          )}
        </div>

        {/* Right Sidebar */}
        <div className="space-y-4">
          <div className="card p-4">
            <h4 className="text-xs font-semibold text-surface-muted uppercase tracking-wider mb-3">Properties</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-surface-muted">Type</span><WorkTypeBadge type={initiative.initiative_type} /></div>
              <div className="flex justify-between"><span className="text-surface-muted">Status</span><StatusBadge status={initiative.status} size="sm" /></div>
              <div className="flex justify-between"><span className="text-surface-muted">Priority</span><PriorityTag priority={initiative.priority} /></div>
              {isFullInitiative && (
                <>
                  <div className="flex justify-between"><span className="text-surface-muted">Methodology</span><MethodologyBadge methodology={initiative.methodology} /></div>
                  <div className="flex justify-between"><span className="text-surface-muted">Phase</span><span className="text-gray-300 capitalize">{initiative.current_phase.replace(/_/g, ' ')}</span></div>
                </>
              )}
              <div className="pt-2 border-t border-surface-border">
                <label className="block text-xs text-surface-muted mb-1">Lead Analyst</label>
                <select
                  value={initiative.lead_analyst_id ?? ''}
                  onChange={(e) => assignLead(e.target.value || null)}
                  className="input-field text-xs py-1"
                >
                  <option value="">Unassigned</option>
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>{u.full_name}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="card p-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-semibold text-surface-muted uppercase tracking-wider">Action Items</h4>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-surface-muted">{actions.length}</span>
                <button onClick={openAddAction} className="p-0.5 rounded text-gray-400 hover:text-brand-400 hover:bg-surface-hover transition-colors" title="Add action item">
                  <Plus size={14} />
                </button>
              </div>
            </div>
            {actions.length === 0 ? (
              <button onClick={openAddAction} className="w-full p-3 rounded-lg border border-dashed border-surface-border text-xs text-gray-400 hover:text-brand-400 hover:border-brand-500/30 transition-colors">
                + Add first action item
              </button>
            ) : (
              <div className="space-y-1.5">
                {actions.slice(0, 5).map((a) => (
                  <div key={a.id} className="flex items-center gap-2 p-2 rounded bg-surface-bg">
                    <div className={`w-1.5 h-1.5 rounded-full ${a.status === 'completed' ? 'bg-green-500' : a.status === 'in_progress' ? 'bg-yellow-500' : 'bg-blue-500'}`} />
                    <span className="text-xs text-gray-300 truncate flex-1">{a.title}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Stakeholder sidebar summary */}
          <div className="card p-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-semibold text-surface-muted uppercase tracking-wider">Stakeholders</h4>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-surface-muted">{stakeholders.length}</span>
                <button onClick={() => { setShForm({ user_id: '', role: 'contributor' }); setShModal(true); }} className="p-0.5 rounded text-gray-400 hover:text-brand-400 hover:bg-surface-hover transition-colors" title="Add stakeholder">
                  <Plus size={14} />
                </button>
              </div>
            </div>
            {stakeholders.length === 0 ? (
              <button onClick={() => { setShForm({ user_id: '', role: 'contributor' }); setShModal(true); }} className="w-full p-3 rounded-lg border border-dashed border-surface-border text-xs text-gray-400 hover:text-brand-400 hover:border-brand-500/30 transition-colors">
                + Add first stakeholder
              </button>
            ) : (
              <div className="space-y-1.5">
                {stakeholders.slice(0, 5).map((sh) => (
                  <div key={sh.user_id} className="flex items-center gap-2 p-2 rounded bg-surface-bg">
                    <div className="w-5 h-5 rounded-full bg-brand-500/20 flex items-center justify-center text-[9px] font-semibold text-brand-400">
                      {(sh.user_name || '?').charAt(0).toUpperCase()}
                    </div>
                    <span className="text-xs text-gray-300 truncate flex-1">{sh.user_name}</span>
                    <span className="text-[9px] text-surface-muted">{sh.role}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {isFullInitiative && (
            <button
              onClick={() => { useAIStore.getState().setContext(id!); useAIStore.getState().setActiveAgent('coach'); }}
              className="w-full card p-4 text-left hover:border-teal-500/30 transition-colors cursor-pointer">
              <div className="flex items-center gap-2 mb-1">
                <Bot size={14} className="text-teal-400" />
                <span className="text-xs font-semibold text-teal-400">AI Coach</span>
              </div>
              <p className="text-xs text-gray-400">Get phase-specific guidance and methodology coaching.</p>
            </button>
          )}
        </div>
      </div>

      {/* Add Action Modal */}
      <Modal open={actionModal} onClose={() => setActionModal(false)} title="Add Action Item">
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-surface-muted mb-1">Title *</label>
            <input
              value={actionForm.title}
              onChange={(e) => setActionForm((f) => ({ ...f, title: e.target.value }))}
              className="input-field w-full text-sm"
              placeholder="Action item title"
            />
          </div>
          <div>
            <label className="block text-xs text-surface-muted mb-1">Description</label>
            <textarea
              value={actionForm.description}
              onChange={(e) => setActionForm((f) => ({ ...f, description: e.target.value }))}
              className="input-field w-full h-20 resize-none text-sm py-2"
              placeholder="Optional description"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-surface-muted mb-1">Assigned To</label>
              <select
                value={actionForm.assigned_to}
                onChange={(e) => setActionForm((f) => ({ ...f, assigned_to: e.target.value }))}
                className="input-field text-sm py-1.5"
              >
                <option value="">Unassigned</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>{u.full_name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-surface-muted mb-1">Priority</label>
              <select
                value={actionForm.priority}
                onChange={(e) => setActionForm((f) => ({ ...f, priority: e.target.value }))}
                className="input-field text-sm py-1.5"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs text-surface-muted mb-1">Due Date</label>
            <input
              type="date"
              value={actionForm.due_date}
              onChange={(e) => setActionForm((f) => ({ ...f, due_date: e.target.value }))}
              className="input-field text-sm py-1.5"
            />
          </div>
          <div className="flex items-center justify-end gap-2 pt-2 border-t border-surface-border">
            <button onClick={() => setActionModal(false)} className="btn-ghost btn-sm">Cancel</button>
            <button onClick={saveAction} disabled={actionSaving || !actionForm.title.trim()} className="btn-primary btn-sm">
              <Plus size={14} /> {actionSaving ? 'Creating...' : 'Create Action'}
            </button>
          </div>
        </div>
      </Modal>

      {/* Add Stakeholder Modal */}
      <Modal open={shModal} onClose={() => setShModal(false)} title="Add Stakeholder">
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-surface-muted mb-1">Team Member *</label>
            <select
              value={shForm.user_id}
              onChange={(e) => setShForm((f) => ({ ...f, user_id: e.target.value }))}
              className="input-field text-sm py-1.5"
            >
              <option value="">Select a user...</option>
              {availableUsers.map((u) => (
                <option key={u.id} value={u.id}>{u.full_name} ({u.email})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-surface-muted mb-1">Role *</label>
            <select
              value={shForm.role}
              onChange={(e) => setShForm((f) => ({ ...f, role: e.target.value }))}
              className="input-field text-sm py-1.5"
            >
              {STAKEHOLDER_ROLES.map((r) => (
                <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center justify-end gap-2 pt-2 border-t border-surface-border">
            <button onClick={() => setShModal(false)} className="btn-ghost btn-sm">Cancel</button>
            <button onClick={addStakeholder} disabled={shSaving || !shForm.user_id} className="btn-primary btn-sm">
              <UserPlus size={14} /> {shSaving ? 'Adding...' : 'Add Stakeholder'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
