import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, CheckCircle, FileText, Bot, Plus, Shield, Save, X, StickyNote, Trash2 } from 'lucide-react';
import { initiativesApi } from '@/api/initiatives';
import { artifactsApi, type ArtifactOut } from '@/api/artifacts';
import { actionsApi } from '@/api/actions';
import { notesApi, type NoteOut } from '@/api/notes';
import { usersApi } from '@/api/users';
import type { InitiativeOut, PhaseOut, PhaseName, ActionItemOut, UserOut } from '@/types/api';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { PageLoader } from '@/components/shared/LoadingSpinner';
import { Modal } from '@/components/shared/Modal';
import { useAIStore } from '@/stores/aiStore';

const PHASE_ARTIFACTS: Record<PhaseName, string[]> = {
  define: ['Project Charter', 'SIPOC', 'Voice of Customer', 'Stakeholder Analysis'],
  measure: ['Data Collection Plan', 'Measurement System Analysis', 'Process Map', 'Baseline Metrics'],
  analyze: ['Root Cause Analysis', 'Fishbone Diagram', 'Statistical Analysis', 'Hypothesis Tests'],
  improve: ['Solution Selection Matrix', 'Pilot Plan', 'Implementation Plan', 'Risk Assessment'],
  control: ['Control Plan', 'SPC Charts', 'Standard Work', 'Training Plan', 'Handoff Documentation'],
};

export function PhaseWorkspace() {
  const { id, phase } = useParams<{ id: string; phase: string }>();
  const navigate = useNavigate();
  const phaseName = phase as PhaseName;
  const [initiative, setInitiative] = useState<InitiativeOut | null>(null);
  const [phaseData, setPhaseData] = useState<PhaseOut | null>(null);
  const [artifacts, setArtifacts] = useState<ArtifactOut[]>([]);
  const [actions, setActions] = useState<ActionItemOut[]>([]);
  const [notes, setNotes] = useState<NoteOut[]>([]);
  const [users, setUsers] = useState<UserOut[]>([]);
  const [loading, setLoading] = useState(true);
  const { setContext } = useAIStore();

  // Modal state
  const [artifactModal, setArtifactModal] = useState<{ open: boolean; name: string; artifact: ArtifactOut | null }>({ open: false, name: '', artifact: null });
  const [artifactContent, setArtifactContent] = useState('');
  const [artifactStatus, setArtifactStatus] = useState('draft');
  const [artifactSaving, setArtifactSaving] = useState(false);

  const [actionModal, setActionModal] = useState(false);
  const [actionForm, setActionForm] = useState({ title: '', description: '', assigned_to: '', priority: 'medium', due_date: '' });
  const [actionSaving, setActionSaving] = useState(false);

  const [noteContent, setNoteContent] = useState('');
  const [noteType, setNoteType] = useState('general');
  const [noteSaving, setNoteSaving] = useState(false);

  useEffect(() => {
    if (!id || !phase) return;
    setContext(id, phase);
    Promise.all([
      initiativesApi.get(id),
      initiativesApi.getPhases(id),
      actionsApi.list({ initiative_id: id } as Record<string, string>).catch(() => ({ items: [] })),
      notesApi.list(id).catch(() => []),
      usersApi.list({ page_size: 100 }).catch(() => ({ items: [] })),
    ]).then(([init, phases, act, n, u]) => {
      setInitiative(init);
      const p = phases.find((ph: PhaseOut) => ph.phase_name === phaseName);
      setPhaseData(p || null);
      if (p) { artifactsApi.list(p.id).then(setArtifacts).catch(() => setArtifacts([])); }
      setActions('items' in act ? (act as { items: ActionItemOut[] }).items : []);
      setNotes(n as NoteOut[]);
      setUsers('items' in u ? u.items : []);
    }).catch(() => navigate(`/initiatives/${id}`)).finally(() => setLoading(false));
    return () => setContext(null);
  }, [id, phase, phaseName, navigate, setContext]);

  if (loading) return <PageLoader />;
  if (!initiative || !phaseData) return null;

  const expectedArtifacts = PHASE_ARTIFACTS[phaseName] || [];
  const completedCount = artifacts.filter((a) => a.status === 'completed').length;
  const progress = expectedArtifacts.length > 0 ? completedCount / expectedArtifacts.length : phaseData.completeness_score;

  // Filter notes for this phase
  const phaseNotes = notes.filter((n) => n.phase_id === phaseData.id || !n.phase_id);

  // ---- Artifact handlers ----
  const openArtifact = (name: string) => {
    const existing = artifacts.find((a) => a.title === name);
    setArtifactModal({ open: true, name, artifact: existing || null });
    setArtifactContent(existing ? (typeof existing.content === 'object' ? (existing.content as Record<string, unknown>).text as string || JSON.stringify(existing.content, null, 2) : String(existing.content)) : '');
    setArtifactStatus(existing?.status || 'draft');
  };

  const saveArtifact = async () => {
    if (!phaseData || !id) return;
    setArtifactSaving(true);
    try {
      const contentObj = { text: artifactContent };
      if (artifactModal.artifact) {
        const updated = await artifactsApi.update(artifactModal.artifact.id, { content: contentObj, status: artifactStatus });
        setArtifacts((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
      } else {
        const created = await artifactsApi.create(phaseData.id, {
          artifact_type: artifactModal.name.toLowerCase().replace(/\s+/g, '_'),
          title: artifactModal.name,
          content: contentObj,
        });
        setArtifacts((prev) => [...prev, created]);
      }
      setArtifactModal({ open: false, name: '', artifact: null });
    } catch { /* silent */ }
    setArtifactSaving(false);
  };

  // ---- Action handlers ----
  const openAddAction = () => {
    setActionForm({ title: '', description: '', assigned_to: '', priority: 'medium', due_date: '' });
    setActionModal(true);
  };

  const saveAction = async () => {
    if (!id || !actionForm.title.trim()) return;
    setActionSaving(true);
    try {
      const data: Record<string, unknown> = {
        initiative_id: id,
        title: actionForm.title.trim(),
        phase_id: phaseData?.id,
      };
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

  // ---- Note handlers ----
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

  return (
    <div className="space-y-4">
      <button onClick={() => navigate(`/initiatives/${id}`)} className="btn-ghost btn-sm">
        <ArrowLeft size={14} /> {initiative.title}
      </button>

      <div className="card p-5">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-100 capitalize">{phaseName} Phase</h2>
            <p className="text-sm text-surface-muted mt-1">{initiative.title}</p>
          </div>
          <StatusBadge status={phaseData.status} />
        </div>
        <div className="mt-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-surface-muted">Progress</span>
            <span className="text-xs font-mono text-gray-300">{Math.round(progress * 100)}%</span>
          </div>
          <div className="h-2 rounded-full bg-surface-hover">
            <div className="h-full rounded-full bg-brand-500 transition-all" style={{ width: `${progress * 100}%` }} />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          {/* Artifacts */}
          <div className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-gray-200">Artifacts</h3>
              <span className="text-xs text-surface-muted">{completedCount}/{expectedArtifacts.length} complete</span>
            </div>
            <div className="space-y-2">
              {expectedArtifacts.map((name) => {
                const artifact = artifacts.find((a) => a.title === name);
                const done = artifact?.status === 'completed';
                return (
                  <div
                    key={name}
                    onClick={() => openArtifact(name)}
                    className="flex items-center gap-3 p-3 rounded-lg bg-surface-bg hover:bg-surface-hover cursor-pointer transition-colors"
                  >
                    {done ? <CheckCircle size={16} className="text-green-500 shrink-0" /> : <FileText size={16} className="text-surface-muted shrink-0" />}
                    <div className="flex-1">
                      <span className={done ? 'text-sm text-gray-300' : 'text-sm text-gray-200'}>{name}</span>
                      {artifact && <span className="ml-2"><StatusBadge status={artifact.status} size="sm" /></span>}
                    </div>
                    {!artifact && <span className="text-[10px] text-surface-muted">Click to create</span>}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Action Items */}
          <div className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-gray-200">Action Items</h3>
              <button onClick={openAddAction} className="btn-ghost btn-sm"><Plus size={14} /> Add</button>
            </div>
            {actions.length === 0 ? (
              <p className="text-sm text-surface-muted">No action items for this phase.</p>
            ) : (
              <div className="space-y-2">
                {actions.map((action) => (
                  <div key={action.id} className="flex items-center gap-3 p-2 rounded bg-surface-bg">
                    <div className={`w-2 h-2 rounded-full ${action.status === 'completed' ? 'bg-green-500' : action.status === 'in_progress' ? 'bg-yellow-500' : 'bg-blue-500'}`} />
                    <span className="text-sm text-gray-300 flex-1">{action.title}</span>
                    <StatusBadge status={action.status} size="sm" />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Notes */}
          <div className="card p-5">
            <div className="flex items-center gap-2 mb-4">
              <StickyNote size={16} className="text-surface-muted" />
              <h3 className="text-sm font-semibold text-gray-200">Notes</h3>
            </div>

            {/* Add Note Form */}
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

            {phaseNotes.length === 0 ? (
              <p className="text-sm text-surface-muted">No notes yet.</p>
            ) : (
              <div className="space-y-2">
                {phaseNotes.map((note) => (
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
        </div>

        <div className="space-y-4">
          <div className="card p-4 border-teal-500/20">
            <div className="flex items-center gap-2 mb-3">
              <Bot size={16} className="text-teal-400" />
              <h4 className="text-sm font-semibold text-teal-400">Phase Coach</h4>
            </div>
            <p className="text-xs text-gray-400 mb-3">Get guidance on completing the {phaseName} phase artifacts.</p>
            <button
              onClick={() => { useAIStore.getState().setContext(id!, phaseName); useAIStore.getState().setActiveAgent('coach'); }}
              className="btn-primary btn-sm w-full">
              <Bot size={14} /> Ask Coach
            </button>
          </div>

          <div className="card p-4">
            <div className="flex items-center gap-2 mb-3">
              <Shield size={16} className="text-surface-muted" />
              <h4 className="text-sm font-semibold text-gray-200">Gate Review</h4>
            </div>
            {phaseData.gate_approved ? (
              <div className="flex items-center gap-2 text-green-400 text-sm">
                <CheckCircle size={14} /><span>Gate approved</span>
              </div>
            ) : (
              <>
                <p className="text-xs text-gray-400 mb-3">Complete all required artifacts to unlock gate review.</p>
                <button disabled={progress < 1} className="btn-secondary btn-sm w-full">
                  <Shield size={14} /> Request Gate Review
                </button>
              </>
            )}
          </div>

          {phaseData.ai_summary && (
            <div className="card p-4 bg-teal-500/5">
              <span className="text-[10px] font-semibold text-teal-400 uppercase tracking-wider">AI Summary</span>
              <p className="text-xs text-gray-400 mt-1">{phaseData.ai_summary}</p>
            </div>
          )}
        </div>
      </div>

      {/* Artifact Edit Modal */}
      <Modal open={artifactModal.open} onClose={() => setArtifactModal({ open: false, name: '', artifact: null })} title={artifactModal.name} size="lg">
        <div className="space-y-4">
          <div>
            <label className="block text-xs text-surface-muted mb-1">Content</label>
            <textarea
              value={artifactContent}
              onChange={(e) => setArtifactContent(e.target.value)}
              className="input-field w-full h-64 resize-y text-sm font-mono py-2"
              placeholder={`Enter content for ${artifactModal.name}...`}
            />
          </div>
          {artifactModal.artifact && (
            <div>
              <label className="block text-xs text-surface-muted mb-1">Status</label>
              <select value={artifactStatus} onChange={(e) => setArtifactStatus(e.target.value)} className="input-field text-sm py-1.5">
                <option value="draft">Draft</option>
                <option value="in_progress">In Progress</option>
                <option value="review">Under Review</option>
                <option value="completed">Completed</option>
              </select>
            </div>
          )}
          <div className="flex items-center justify-end gap-2 pt-2 border-t border-surface-border">
            <button onClick={() => setArtifactModal({ open: false, name: '', artifact: null })} className="btn-ghost btn-sm"><X size={14} /> Cancel</button>
            <button onClick={saveArtifact} disabled={artifactSaving || !artifactContent.trim()} className="btn-primary btn-sm">
              <Save size={14} /> {artifactSaving ? 'Saving...' : artifactModal.artifact ? 'Update' : 'Create'}
            </button>
          </div>
        </div>
      </Modal>

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
    </div>
  );
}
