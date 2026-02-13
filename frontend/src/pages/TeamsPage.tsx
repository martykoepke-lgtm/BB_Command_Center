import { useEffect, useState } from 'react';
import {
  Users, Plus, ChevronRight, ArrowLeft, UserPlus, X, Search,
  Shield, Pencil, Trash2, Target, Clock, CheckCircle, AlertTriangle,
  Activity,
} from 'lucide-react';
import { teamsApi } from '@/api/teams';
import { usersApi } from '@/api/users';
import { dashboardsApi } from '@/api/dashboards';
import type { TeamOut, TeamMemberOut, TeamMetrics, UserOut } from '@/types/api';
import { PageLoader } from '@/components/shared/LoadingSpinner';
import { EmptyState } from '@/components/shared/EmptyState';
import { Modal } from '@/components/shared/Modal';

// ─── Shared Types ────────────────────────────────────────────────────────────

interface TeamForm {
  name: string;
  description: string;
  department: string;
  organization: string;
}

const EMPTY_FORM: TeamForm = { name: '', description: '', department: '', organization: '' };

const ROLE_BADGES: Record<string, string> = {
  admin: 'bg-red-500/20 text-red-400 border-red-500/30',
  manager: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  analyst: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  viewer: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  sponsor: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  lead: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  member: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
  contributor: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
  observer: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
};

const PRIORITY_COLORS: Record<string, string> = {
  critical: 'text-red-400',
  high: 'text-orange-400',
  medium: 'text-yellow-400',
  low: 'text-gray-400',
};

const PHASE_COLORS: Record<string, string> = {
  define: 'bg-blue-500',
  measure: 'bg-purple-500',
  analyze: 'bg-yellow-500',
  improve: 'bg-green-500',
  control: 'bg-teal-500',
};

function Initials({ name }: { name: string }) {
  const initials = name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2);
  return (
    <div className="w-8 h-8 rounded-full bg-brand-500/20 flex items-center justify-center text-brand-400 text-xs font-semibold shrink-0">
      {initials}
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export function TeamsPage() {
  const [teams, setTeams] = useState<TeamOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<TeamForm>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTeam, setSelectedTeam] = useState<TeamOut | null>(null);

  const loadTeams = () => {
    teamsApi.list({ page_size: 100 })
      .then((res) => setTeams(res.items))
      .catch(() => setTeams([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadTeams(); }, []);

  const handleCreate = async () => {
    if (!form.name.trim()) {
      setError('Team name is required.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const created = await teamsApi.create({
        name: form.name.trim(),
        description: form.description.trim() || undefined,
        department: form.department.trim() || undefined,
        organization: form.organization.trim() || undefined,
      });
      setTeams((prev) => [...prev, created]);
      setShowCreate(false);
      setForm(EMPTY_FORM);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create team';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const openCreateModal = () => {
    setForm(EMPTY_FORM);
    setError(null);
    setShowCreate(true);
  };

  const refreshTeams = () => {
    teamsApi.list({ page_size: 100 })
      .then((res) => {
        setTeams(res.items);
        if (selectedTeam) {
          const updated = res.items.find((t) => t.id === selectedTeam.id);
          if (updated) setSelectedTeam(updated);
        }
      })
      .catch(() => {});
  };

  const handleTeamDeleted = (teamId: string) => {
    setTeams((prev) => prev.filter((t) => t.id !== teamId));
    setSelectedTeam(null);
  };

  if (loading) return <PageLoader />;

  // ── Detail View ──────────────────────────────────────────────────────────
  if (selectedTeam) {
    return (
      <TeamDetailView
        team={selectedTeam}
        onBack={() => setSelectedTeam(null)}
        onTeamUpdated={refreshTeams}
        onTeamDeleted={handleTeamDeleted}
      />
    );
  }

  // ── Empty State ──────────────────────────────────────────────────────────
  if (teams.length === 0) {
    return (
      <>
        <EmptyState
          icon={<Users size={40} />}
          title="No teams yet"
          description="Create a team to organize analysts and track workload."
          action={<button className="btn-primary" onClick={openCreateModal}><Plus size={16} /> Create Team</button>}
        />
        <TeamFormModal
          open={showCreate}
          onClose={() => setShowCreate(false)}
          title="Create Team"
          form={form}
          setForm={setForm}
          onSubmit={handleCreate}
          submitting={submitting}
          error={error}
          submitLabel="Create Team"
        />
      </>
    );
  }

  // ── Team List ────────────────────────────────────────────────────────────
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-100">Teams</h2>
        <button className="btn-primary btn-sm" onClick={openCreateModal}>
          <Plus size={14} /> New Team
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {teams.map((team) => (
          <div
            key={team.id}
            className="card-hover p-5 cursor-pointer"
            onClick={() => setSelectedTeam(team)}
          >
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-sm font-semibold text-gray-100">{team.name}</h3>
                {team.department && (
                  <p className="text-xs text-surface-muted mt-0.5">{team.department}</p>
                )}
              </div>
              <ChevronRight size={16} className="text-surface-muted" />
            </div>
            {team.description && (
              <p className="text-xs text-gray-400 mt-2 line-clamp-2">{team.description}</p>
            )}
            <div className="mt-3 text-xs text-surface-muted">
              {team.member_count ?? 0} member{(team.member_count ?? 0) !== 1 ? 's' : ''}
            </div>
          </div>
        ))}
      </div>

      <TeamFormModal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title="Create Team"
        form={form}
        setForm={setForm}
        onSubmit={handleCreate}
        submitting={submitting}
        error={error}
        submitLabel="Create Team"
      />
    </div>
  );
}

// ─── Team Detail View ────────────────────────────────────────────────────────

function TeamDetailView({
  team,
  onBack,
  onTeamUpdated,
  onTeamDeleted,
}: {
  team: TeamOut;
  onBack: () => void;
  onTeamUpdated: () => void;
  onTeamDeleted: (id: string) => void;
}) {
  const [members, setMembers] = useState<TeamMemberOut[]>([]);
  const [loadingMembers, setLoadingMembers] = useState(true);
  const [metrics, setMetrics] = useState<TeamMetrics | null>(null);
  const [showAddMember, setShowAddMember] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [removing, setRemoving] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Edit form state
  const [editForm, setEditForm] = useState<TeamForm>(EMPTY_FORM);
  const [editManagerId, setEditManagerId] = useState<string>('');
  const [editSubmitting, setEditSubmitting] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const loadMembers = () => {
    setLoadingMembers(true);
    teamsApi.members(team.id)
      .then(setMembers)
      .catch(() => setMembers([]))
      .finally(() => setLoadingMembers(false));
  };

  const loadMetrics = () => {
    dashboardsApi.team(team.id)
      .then(setMetrics)
      .catch(() => setMetrics(null));
  };

  useEffect(() => {
    loadMembers();
    loadMetrics();
  }, [team.id]);

  const handleRemove = async (userId: string, name: string) => {
    if (!confirm(`Remove ${name} from this team?`)) return;
    setRemoving(userId);
    try {
      await teamsApi.removeMember(team.id, userId);
      setMembers((prev) => prev.filter((m) => m.user_id !== userId));
      onTeamUpdated();
      loadMetrics();
    } catch {
      alert('Failed to remove member.');
    } finally {
      setRemoving(null);
    }
  };

  const handleMemberAdded = () => {
    loadMembers();
    onTeamUpdated();
    loadMetrics();
    setShowAddMember(false);
  };

  const openEditModal = () => {
    setEditForm({
      name: team.name,
      description: team.description ?? '',
      department: team.department ?? '',
      organization: team.organization ?? '',
    });
    setEditManagerId(team.manager_id ?? '');
    setEditError(null);
    setShowEdit(true);
  };

  const handleEdit = async () => {
    if (!editForm.name.trim()) {
      setEditError('Team name is required.');
      return;
    }
    setEditSubmitting(true);
    setEditError(null);
    try {
      await teamsApi.update(team.id, {
        name: editForm.name.trim(),
        description: editForm.description.trim() || undefined,
        department: editForm.department.trim() || undefined,
        organization: editForm.organization.trim() || undefined,
        manager_id: editManagerId || undefined,
      });
      setShowEdit(false);
      onTeamUpdated();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update team';
      setEditError(msg);
    } finally {
      setEditSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm(`Delete team "${team.name}"? This will remove all member associations.`)) return;
    setDeleting(true);
    try {
      await teamsApi.delete(team.id);
      onTeamDeleted(team.id);
    } catch {
      alert('Failed to delete team.');
      setDeleting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="p-2 rounded-lg text-surface-muted hover:text-gray-100 hover:bg-surface-hover transition-colors"
        >
          <ArrowLeft size={18} />
        </button>
        <div className="flex-1">
          <h2 className="text-lg font-semibold text-gray-100">{team.name}</h2>
          <div className="flex items-center gap-3 mt-0.5">
            {team.department && (
              <span className="text-xs text-surface-muted">{team.department}</span>
            )}
            {team.organization && (
              <>
                <span className="text-xs text-gray-600">|</span>
                <span className="text-xs text-surface-muted">{team.organization}</span>
              </>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={openEditModal}
            className="p-2 rounded-lg text-surface-muted hover:text-gray-100 hover:bg-surface-hover transition-colors"
            title="Edit team"
          >
            <Pencil size={16} />
          </button>
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="p-2 rounded-lg text-surface-muted hover:text-red-400 hover:bg-red-400/10 transition-colors disabled:opacity-50"
            title="Delete team"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>

      {team.description && (
        <div className="card p-4">
          <p className="text-sm text-gray-300">{team.description}</p>
        </div>
      )}

      {/* Team Metrics Dashboard */}
      <TeamDashboard metrics={metrics} />

      {/* Members Section */}
      <div className="card">
        <div className="flex items-center justify-between px-5 py-4 border-b border-surface-border">
          <div className="flex items-center gap-2">
            <Users size={16} className="text-surface-muted" />
            <h3 className="text-sm font-semibold text-gray-200">
              Team Members ({members.length})
            </h3>
          </div>
          <button
            className="btn-primary btn-sm"
            onClick={() => setShowAddMember(true)}
          >
            <UserPlus size={14} /> Add Member
          </button>
        </div>

        {loadingMembers ? (
          <div className="p-8 text-center text-surface-muted text-sm">Loading members...</div>
        ) : members.length === 0 ? (
          <div className="p-8 text-center">
            <Users size={32} className="mx-auto text-surface-muted mb-3" />
            <p className="text-sm text-surface-muted">No members yet.</p>
            <p className="text-xs text-gray-500 mt-1">Add users to this team to get started.</p>
            <button
              className="btn-primary btn-sm mt-4"
              onClick={() => setShowAddMember(true)}
            >
              <UserPlus size={14} /> Add First Member
            </button>
          </div>
        ) : (
          <div className="divide-y divide-surface-border">
            {members.map((member) => {
              const memberMetric = metrics?.members.find((m) => m.user_id === member.user_id);
              const isManager = team.manager_id === member.user_id;
              return (
                <div
                  key={member.user_id}
                  className="flex items-center justify-between px-5 py-3 hover:bg-surface-hover/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <Initials name={member.full_name} />
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-100">{member.full_name}</span>
                        {isManager && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30 font-medium">
                            Manager
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-surface-muted">{member.email}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {memberMetric && (
                      <span className="text-xs text-surface-muted font-mono mr-2" title="Utilization">
                        {memberMetric.utilization_pct.toFixed(0)}%
                      </span>
                    )}
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${ROLE_BADGES[member.role_in_team] ?? ROLE_BADGES.member}`}>
                      {member.role_in_team}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${ROLE_BADGES[member.role] ?? ROLE_BADGES.member}`}>
                      <Shield size={10} className="inline mr-1" />
                      {member.role}
                    </span>
                    <button
                      onClick={() => handleRemove(member.user_id, member.full_name)}
                      disabled={removing === member.user_id}
                      className="p-1.5 rounded-md text-surface-muted hover:text-red-400 hover:bg-red-400/10 transition-colors disabled:opacity-50"
                      title="Remove from team"
                    >
                      <X size={14} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Team Initiatives */}
      {metrics && metrics.initiatives.length > 0 && (
        <div className="card">
          <div className="flex items-center gap-2 px-5 py-4 border-b border-surface-border">
            <Target size={16} className="text-surface-muted" />
            <h3 className="text-sm font-semibold text-gray-200">
              Team Initiatives ({metrics.initiatives.length})
            </h3>
          </div>
          <div className="divide-y divide-surface-border">
            {metrics.initiatives.map((init) => (
              <div key={init.id} className="flex items-center justify-between px-5 py-3 hover:bg-surface-hover/50 transition-colors">
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${PHASE_COLORS[init.current_phase] ?? 'bg-gray-500'}`} />
                  <div>
                    <div className="text-sm text-gray-100">
                      <span className="font-mono text-xs text-surface-muted mr-2">{init.initiative_number}</span>
                      {init.title}
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-xs text-surface-muted capitalize">{init.current_phase}</span>
                      {init.methodology && (
                        <>
                          <span className="text-xs text-gray-600">|</span>
                          <span className="text-xs text-surface-muted">{init.methodology}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {init.health_score && (
                    <span className={`text-xs ${
                      init.health_score === 'on_track' ? 'text-green-400' :
                      init.health_score === 'at_risk' ? 'text-yellow-400' : 'text-red-400'
                    }`}>
                      {init.health_score.replace(/_/g, ' ')}
                    </span>
                  )}
                  <span className={`text-xs ${PRIORITY_COLORS[init.priority] ?? 'text-gray-400'}`}>
                    {init.priority}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded-full border ${
                    init.status === 'active' ? 'bg-blue-500/20 text-blue-400 border-blue-500/30' :
                    init.status === 'completed' ? 'bg-green-500/20 text-green-400 border-green-500/30' :
                    init.status === 'on_hold' ? 'bg-gray-500/20 text-gray-400 border-gray-500/30' :
                    'bg-red-500/20 text-red-400 border-red-500/30'
                  }`}>
                    {init.status.replace(/_/g, ' ')}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Add Member Modal */}
      <AddMemberModal
        open={showAddMember}
        onClose={() => setShowAddMember(false)}
        teamId={team.id}
        existingMemberIds={members.map((m) => m.user_id)}
        onAdded={handleMemberAdded}
      />

      {/* Edit Team Modal */}
      <EditTeamModal
        open={showEdit}
        onClose={() => setShowEdit(false)}
        form={editForm}
        setForm={setEditForm}
        managerId={editManagerId}
        setManagerId={setEditManagerId}
        members={members}
        onSubmit={handleEdit}
        submitting={editSubmitting}
        error={editError}
      />
    </div>
  );
}

// ─── Team Dashboard Metrics ──────────────────────────────────────────────────

function TeamDashboard({ metrics }: { metrics: TeamMetrics | null }) {
  if (!metrics) return null;

  const overdue = metrics.action_compliance?.overdue_count ?? 0;
  const completed = metrics.action_compliance?.total_completed ?? 0;
  const onTimePct = metrics.action_compliance?.on_time_pct ?? 0;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div className="card p-4">
        <div className="flex items-center gap-2 mb-1">
          <Activity size={14} className="text-blue-400" />
          <span className="text-xs text-surface-muted">Avg Utilization</span>
        </div>
        <div className="text-xl font-semibold font-mono text-gray-100">
          {metrics.average_utilization.toFixed(0)}%
        </div>
        <div className="mt-1.5 w-full h-1.5 rounded-full bg-surface-hover overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              metrics.average_utilization > 90 ? 'bg-red-500' :
              metrics.average_utilization > 70 ? 'bg-yellow-500' : 'bg-green-500'
            }`}
            style={{ width: `${Math.min(metrics.average_utilization, 100)}%` }}
          />
        </div>
      </div>

      <div className="card p-4">
        <div className="flex items-center gap-2 mb-1">
          <Target size={14} className="text-purple-400" />
          <span className="text-xs text-surface-muted">Initiatives</span>
        </div>
        <div className="text-xl font-semibold font-mono text-gray-100">
          {metrics.initiatives.length}
        </div>
        <div className="text-xs text-surface-muted mt-1">
          {metrics.initiatives.filter((i) => i.status === 'active').length} active
        </div>
      </div>

      <div className="card p-4">
        <div className="flex items-center gap-2 mb-1">
          <CheckCircle size={14} className="text-green-400" />
          <span className="text-xs text-surface-muted">Actions Completed</span>
        </div>
        <div className="text-xl font-semibold font-mono text-gray-100">{completed}</div>
        <div className="text-xs text-surface-muted mt-1">
          {onTimePct > 0 ? `${onTimePct.toFixed(0)}% on-time` : 'No data yet'}
        </div>
      </div>

      <div className="card p-4">
        <div className="flex items-center gap-2 mb-1">
          {overdue > 0 ? (
            <AlertTriangle size={14} className="text-red-400" />
          ) : (
            <Clock size={14} className="text-green-400" />
          )}
          <span className="text-xs text-surface-muted">Overdue Actions</span>
        </div>
        <div className={`text-xl font-semibold font-mono ${overdue > 0 ? 'text-red-400' : 'text-green-400'}`}>
          {overdue}
        </div>
        <div className="text-xs text-surface-muted mt-1">
          {metrics.overloaded.length > 0
            ? `${metrics.overloaded.length} overloaded`
            : metrics.available.length > 0
              ? `${metrics.available.length} available`
              : 'Team balanced'}
        </div>
      </div>
    </div>
  );
}

// ─── Edit Team Modal ─────────────────────────────────────────────────────────

function EditTeamModal({
  open, onClose, form, setForm, managerId, setManagerId, members,
  onSubmit, submitting, error,
}: {
  open: boolean;
  onClose: () => void;
  form: TeamForm;
  setForm: React.Dispatch<React.SetStateAction<TeamForm>>;
  managerId: string;
  setManagerId: (id: string) => void;
  members: TeamMemberOut[];
  onSubmit: () => void;
  submitting: boolean;
  error: string | null;
}) {
  const update = (field: keyof TeamForm, value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Edit Team"
      size="sm"
      footer={
        <>
          <button className="btn-ghost" onClick={onClose} disabled={submitting}>Cancel</button>
          <button className="btn-primary" onClick={onSubmit} disabled={submitting || !form.name.trim()}>
            {submitting ? 'Saving...' : 'Save Changes'}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        {error && (
          <div className="text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">
            {error}
          </div>
        )}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Team Name *</label>
          <input
            type="text"
            className="input-field w-full"
            value={form.name}
            onChange={(e) => update('name', e.target.value)}
            autoFocus
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Description</label>
          <textarea
            className="input-field w-full resize-none"
            rows={2}
            value={form.description}
            onChange={(e) => update('description', e.target.value)}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Department</label>
            <input
              type="text"
              className="input-field w-full"
              placeholder="e.g. Quality"
              value={form.department}
              onChange={(e) => update('department', e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Organization</label>
            <input
              type="text"
              className="input-field w-full"
              placeholder="e.g. Acme Corp"
              value={form.organization}
              onChange={(e) => update('organization', e.target.value)}
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Team Manager</label>
          <select
            className="input-field w-full"
            value={managerId}
            onChange={(e) => setManagerId(e.target.value)}
          >
            <option value="">No manager assigned</option>
            {members.map((m) => (
              <option key={m.user_id} value={m.user_id}>{m.full_name}</option>
            ))}
          </select>
          <p className="text-xs text-surface-muted mt-1">The manager must be a current team member.</p>
        </div>
      </div>
    </Modal>
  );
}

// ─── Add Member Modal ────────────────────────────────────────────────────────

function AddMemberModal({
  open, onClose, teamId, existingMemberIds, onAdded,
}: {
  open: boolean;
  onClose: () => void;
  teamId: string;
  existingMemberIds: string[];
  onAdded: () => void;
}) {
  const [users, setUsers] = useState<UserOut[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedUser, setSelectedUser] = useState<UserOut | null>(null);
  const [roleInTeam, setRoleInTeam] = useState('member');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setLoadingUsers(true);
    setSearch('');
    setSelectedUser(null);
    setRoleInTeam('member');
    setError(null);
    usersApi.list({ page_size: 100 })
      .then((res) => setUsers(res.items))
      .catch(() => setUsers([]))
      .finally(() => setLoadingUsers(false));
  }, [open]);

  const availableUsers = users.filter(
    (u) =>
      !existingMemberIds.includes(u.id) &&
      u.is_active &&
      (search === '' ||
        u.full_name.toLowerCase().includes(search.toLowerCase()) ||
        u.email.toLowerCase().includes(search.toLowerCase()))
  );

  const handleAdd = async () => {
    if (!selectedUser) return;
    setSubmitting(true);
    setError(null);
    try {
      await teamsApi.addMember(teamId, selectedUser.id, roleInTeam);
      onAdded();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to add member';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Add Team Member"
      size="md"
      footer={
        <>
          <button className="btn-ghost" onClick={onClose} disabled={submitting}>Cancel</button>
          <button className="btn-primary" onClick={handleAdd} disabled={submitting || !selectedUser}>
            {submitting ? 'Adding...' : 'Add to Team'}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        {error && (
          <div className="text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">
            {error}
          </div>
        )}

        {/* Search */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Search Users</label>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-muted" />
            <input
              type="text"
              className="input-field w-full pl-9"
              placeholder="Search by name or email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              autoFocus
            />
          </div>
        </div>

        {/* User List */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Select User {selectedUser && <span className="text-brand-400">— {selectedUser.full_name}</span>}
          </label>
          <div className="border border-surface-border rounded-lg max-h-48 overflow-y-auto bg-surface-bg">
            {loadingUsers ? (
              <div className="p-4 text-center text-sm text-surface-muted">Loading users...</div>
            ) : availableUsers.length === 0 ? (
              <div className="p-4 text-center text-sm text-surface-muted">
                {search ? 'No matching users found.' : 'All users are already members.'}
              </div>
            ) : (
              availableUsers.map((user) => (
                <div
                  key={user.id}
                  onClick={() => setSelectedUser(user)}
                  className={`flex items-center gap-3 px-3 py-2.5 cursor-pointer transition-colors ${
                    selectedUser?.id === user.id
                      ? 'bg-brand-500/20 border-l-2 border-brand-400'
                      : 'hover:bg-surface-hover border-l-2 border-transparent'
                  }`}
                >
                  <Initials name={user.full_name} />
                  <div className="min-w-0">
                    <div className="text-sm text-gray-100 truncate">{user.full_name}</div>
                    <div className="text-xs text-surface-muted truncate">{user.email}</div>
                  </div>
                  <span className="ml-auto text-xs text-surface-muted shrink-0">{user.role}</span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Role in Team */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Role in Team</label>
          <select
            className="input-field w-full"
            value={roleInTeam}
            onChange={(e) => setRoleInTeam(e.target.value)}
          >
            <option value="member">Member</option>
            <option value="lead">Lead</option>
            <option value="contributor">Contributor</option>
            <option value="observer">Observer</option>
          </select>
        </div>
      </div>
    </Modal>
  );
}

// ─── Reusable Team Form Modal (Create) ───────────────────────────────────────

function TeamFormModal({
  open, onClose, title, form, setForm, onSubmit, submitting, error, submitLabel,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  form: TeamForm;
  setForm: React.Dispatch<React.SetStateAction<TeamForm>>;
  onSubmit: () => void;
  submitting: boolean;
  error: string | null;
  submitLabel: string;
}) {
  const update = (field: keyof TeamForm, value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      size="sm"
      footer={
        <>
          <button className="btn-ghost" onClick={onClose} disabled={submitting}>Cancel</button>
          <button className="btn-primary" onClick={onSubmit} disabled={submitting || !form.name.trim()}>
            {submitting ? 'Saving...' : submitLabel}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        {error && (
          <div className="text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">
            {error}
          </div>
        )}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Team Name *</label>
          <input
            type="text"
            className="input-field w-full"
            placeholder="e.g. Operations Excellence"
            value={form.name}
            onChange={(e) => update('name', e.target.value)}
            autoFocus
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Description</label>
          <textarea
            className="input-field w-full resize-none"
            rows={2}
            placeholder="What does this team focus on?"
            value={form.description}
            onChange={(e) => update('description', e.target.value)}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Department</label>
            <input
              type="text"
              className="input-field w-full"
              placeholder="e.g. Quality"
              value={form.department}
              onChange={(e) => update('department', e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Organization</label>
            <input
              type="text"
              className="input-field w-full"
              placeholder="e.g. Acme Corp"
              value={form.organization}
              onChange={(e) => update('organization', e.target.value)}
            />
          </div>
        </div>
      </div>
    </Modal>
  );
}
