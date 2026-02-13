import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, CheckCircle, XCircle, ArrowRight, Brain } from 'lucide-react';
import { requestsApi } from '@/api/requests';
import type { RequestOut } from '@/types/api';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { PriorityTag } from '@/components/shared/PriorityTag';
import { PageLoader } from '@/components/shared/LoadingSpinner';

export function RequestDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [request, setRequest] = useState<RequestOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [reviewNotes, setReviewNotes] = useState('');

  useEffect(() => {
    if (!id) return;
    requestsApi.get(id)
      .then(setRequest)
      .catch(() => navigate('/requests'))
      .finally(() => setLoading(false));
  }, [id, navigate]);

  const handleAction = async (action: 'accepted' | 'declined') => {
    if (!id) return;
    try {
      const updated = await requestsApi.update(id, { status: action, review_notes: reviewNotes });
      setRequest(updated);
    } catch { /* handle error */ }
  };

  const handleConvert = async () => {
    if (!id) return;
    try {
      const result = await requestsApi.convertToInitiative(id, {});
      navigate(`/initiatives/${result.initiative_id}`);
    } catch { /* handle error */ }
  };

  if (loading) return <PageLoader />;
  if (!request) return null;

  const canReview = request.status === 'submitted' || request.status === 'under_review';
  const canConvert = request.status === 'accepted';

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <button onClick={() => navigate('/requests')} className="btn-ghost btn-sm">
        <ArrowLeft size={14} /> Back to Queue
      </button>

      {/* Header */}
      <div className="card p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <span className="text-xs font-mono text-surface-muted">{request.request_number}</span>
            <h2 className="text-xl font-semibold text-gray-100 mt-1">{request.title}</h2>
          </div>
          <div className="flex items-center gap-2">
            <PriorityTag priority={request.urgency} />
            <StatusBadge status={request.status} />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-surface-muted">Requester</span>
            <p className="text-gray-200">{request.requester_name}</p>
          </div>
          <div>
            <span className="text-surface-muted">Department</span>
            <p className="text-gray-200">{request.requester_dept || '-'}</p>
          </div>
          <div>
            <span className="text-surface-muted">Submitted</span>
            <p className="text-gray-200">{new Date(request.submitted_at).toLocaleString()}</p>
          </div>
          <div>
            <span className="text-surface-muted">Email</span>
            <p className="text-gray-200">{request.requester_email || '-'}</p>
          </div>
        </div>
      </div>

      {/* Content sections */}
      <div className="space-y-4">
        {request.problem_statement && (
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-200 mb-2">Problem Statement</h3>
            <p className="text-sm text-gray-400 whitespace-pre-wrap">{request.problem_statement}</p>
          </div>
        )}
        {request.desired_outcome && (
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-200 mb-2">Desired Outcome</h3>
            <p className="text-sm text-gray-400 whitespace-pre-wrap">{request.desired_outcome}</p>
          </div>
        )}
        {request.business_impact && (
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-200 mb-2">Business Impact</h3>
            <p className="text-sm text-gray-400 whitespace-pre-wrap">{request.business_impact}</p>
          </div>
        )}
      </div>

      {/* AI Triage */}
      {(request.complexity_score != null || request.recommended_methodology) && (
        <div className="card p-5 border-teal-500/30">
          <div className="flex items-center gap-2 mb-3">
            <Brain size={16} className="text-teal-400" />
            <h3 className="text-sm font-semibold text-teal-400">AI Triage Assessment</h3>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {request.complexity_score != null && (
              <div>
                <span className="text-xs text-surface-muted">Complexity Score</span>
                <p className="text-lg font-semibold font-mono text-gray-100">{request.complexity_score}/10</p>
              </div>
            )}
            {request.recommended_methodology && (
              <div>
                <span className="text-xs text-surface-muted">Recommended Methodology</span>
                <p className="text-lg font-semibold text-gray-100">{request.recommended_methodology}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Review actions */}
      {canReview && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-200 mb-3">Review Decision</h3>
          <textarea
            value={reviewNotes}
            onChange={(e) => setReviewNotes(e.target.value)}
            className="input-field h-20 resize-none mb-3"
            placeholder="Review notes (optional)..."
          />
          <div className="flex items-center gap-2">
            <button onClick={() => handleAction('accepted')} className="btn-primary btn-sm">
              <CheckCircle size={14} /> Accept
            </button>
            <button onClick={() => handleAction('declined')} className="btn-danger btn-sm">
              <XCircle size={14} /> Decline
            </button>
          </div>
        </div>
      )}

      {/* Convert to initiative */}
      {canConvert && (
        <div className="card p-5 border-brand-500/30">
          <h3 className="text-sm font-semibold text-gray-200 mb-2">Ready to Convert</h3>
          <p className="text-sm text-gray-400 mb-3">
            This request has been accepted. Convert it to an initiative to begin work.
          </p>
          <button onClick={handleConvert} className="btn-primary btn-sm">
            <ArrowRight size={14} /> Convert to Initiative
          </button>
        </div>
      )}

      {/* Review notes display */}
      {request.review_notes && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-200 mb-2">Review Notes</h3>
          <p className="text-sm text-gray-400 whitespace-pre-wrap">{request.review_notes}</p>
          {request.reviewed_at && (
            <p className="text-xs text-surface-muted mt-2">
              Reviewed {new Date(request.reviewed_at).toLocaleString()}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
