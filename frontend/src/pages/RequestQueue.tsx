import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Filter, Inbox } from 'lucide-react';
import { requestsApi } from '@/api/requests';
import type { RequestOut } from '@/types/api';
import { DataTable, type Column } from '@/components/shared/DataTable';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { PriorityTag } from '@/components/shared/PriorityTag';
import { EmptyState } from '@/components/shared/EmptyState';

export function RequestQueue() {
  const navigate = useNavigate();
  const [requests, setRequests] = useState<RequestOut[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('');

  useEffect(() => {
    setLoading(true);
    requestsApi
      .list({ status: statusFilter || undefined, page, page_size: 25 })
      .then((res) => {
        setRequests(res.items);
        setTotal(res.total);
      })
      .catch(() => setRequests([]))
      .finally(() => setLoading(false));
  }, [page, statusFilter]);

  const columns: Column<RequestOut>[] = [
    {
      key: 'request_number',
      header: '#',
      width: '100px',
      sortable: true,
      render: (row: RequestOut) => (
        <span className="font-mono text-xs text-brand-400">{row.request_number}</span>
      ),
    },
    { key: 'title', header: 'Title', sortable: true },
    {
      key: 'urgency',
      header: 'Urgency',
      width: '100px',
      render: (row: RequestOut) => <PriorityTag priority={row.urgency} />,
    },
    {
      key: 'status',
      header: 'Status',
      width: '120px',
      render: (row: RequestOut) => <StatusBadge status={row.status} size="sm" />,
    },
    {
      key: 'complexity_score',
      header: 'Complexity',
      width: '100px',
      align: 'center',
      render: (row: RequestOut) =>
        row.complexity_score != null ? (
          <span className="font-mono text-xs">{row.complexity_score}/10</span>
        ) : (
          <span className="text-surface-muted text-xs">-</span>
        ),
    },
    { key: 'requester_name', header: 'Requester', sortable: true },
    {
      key: 'submitted_at',
      header: 'Submitted',
      width: '120px',
      sortable: true,
      render: (row: RequestOut) => (
        <span className="text-xs text-surface-muted">
          {new Date(row.submitted_at).toLocaleDateString()}
        </span>
      ),
    },
  ];

  const statuses = ['', 'submitted', 'under_review', 'accepted', 'declined', 'converted'];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-gray-100">Request Queue</h2>
          <span className="badge bg-surface-hover text-gray-400">{total}</span>
        </div>
        <button onClick={() => navigate('/requests/new')} className="btn-primary btn-sm">
          <Plus size={14} /> New Request
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2">
        <Filter size={14} className="text-surface-muted" />
        {statuses.map((s) => (
          <button
            key={s || 'all'}
            onClick={() => { setStatusFilter(s); setPage(1); }}
            className={`btn-sm rounded-full ${
              statusFilter === s ? 'bg-brand-500/20 text-brand-400' : 'btn-ghost'
            }`}
          >
            {s ? s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : 'All'}
          </button>
        ))}
      </div>

      {/* Table */}
      {!loading && requests.length === 0 ? (
        <EmptyState
          icon={<Inbox size={40} />}
          title="No requests found"
          description="Submit a new request to get started with the intake process."
          action={
            <button onClick={() => navigate('/requests/new')} className="btn-primary">
              <Plus size={16} /> Submit Request
            </button>
          }
        />
      ) : (
        <div className="card overflow-hidden">
          <DataTable
            columns={columns}
            data={requests}
            onRowClick={(row) => navigate(`/requests/${row.id}`)}
            page={page}
            perPage={25}
            total={total}
            onPageChange={setPage}
            isLoading={loading}
            dense
          />
        </div>
      )}
    </div>
  );
}
