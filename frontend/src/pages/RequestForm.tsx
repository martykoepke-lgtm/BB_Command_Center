import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, ArrowLeft, ChevronRight, ChevronLeft } from 'lucide-react';
import { requestsApi } from '@/api/requests';
import type { Urgency } from '@/types/api';

const STEPS = ['Problem', 'Outcome', 'Impact', 'Requester'];

export function RequestForm() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const [form, setForm] = useState({
    title: '',
    problem_statement: '',
    desired_outcome: '',
    business_impact: '',
    urgency: 'medium' as Urgency,
    requester_name: '',
    requester_email: '',
    requester_dept: '',
    description: '',
  });

  const update = (field: string, value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = async () => {
    setError('');
    setSubmitting(true);
    try {
      const result = await requestsApi.create(form);
      navigate(`/requests/${result.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Submission failed');
      setSubmitting(false);
    }
  };

  const canAdvance = () => {
    switch (step) {
      case 0: return form.title.trim() && form.problem_statement.trim();
      case 1: return form.desired_outcome.trim();
      case 2: return true;
      case 3: return form.requester_name.trim();
      default: return false;
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Back */}
      <button onClick={() => navigate('/requests')} className="btn-ghost btn-sm">
        <ArrowLeft size={14} /> Back to Queue
      </button>

      {/* Progress */}
      <div className="flex items-center gap-2">
        {STEPS.map((label, i) => (
          <div key={label} className="flex items-center gap-2">
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold ${
                i <= step ? 'bg-brand-500 text-white' : 'bg-surface-hover text-surface-muted'
              }`}
            >
              {i + 1}
            </div>
            <span className={`text-xs ${i <= step ? 'text-gray-200' : 'text-surface-muted'}`}>{label}</span>
            {i < STEPS.length - 1 && <div className="w-8 h-0.5 bg-surface-hover" />}
          </div>
        ))}
      </div>

      {/* Form card */}
      <div className="card p-6 space-y-4">
        {step === 0 && (
          <>
            <h3 className="text-lg font-semibold text-gray-100">Problem Statement</h3>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Request Title</label>
              <input
                value={form.title}
                onChange={(e) => update('title', e.target.value)}
                className="input-field"
                placeholder="Brief title for this request"
                autoFocus
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Problem Statement</label>
              <textarea
                value={form.problem_statement}
                onChange={(e) => update('problem_statement', e.target.value)}
                className="input-field h-28 resize-none"
                placeholder="What is the problem or opportunity? Be specific about what's happening, where, and who is affected."
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Additional Description</label>
              <textarea
                value={form.description}
                onChange={(e) => update('description', e.target.value)}
                className="input-field h-20 resize-none"
                placeholder="Any additional context..."
              />
            </div>
          </>
        )}

        {step === 1 && (
          <>
            <h3 className="text-lg font-semibold text-gray-100">Desired Outcome</h3>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">What does success look like?</label>
              <textarea
                value={form.desired_outcome}
                onChange={(e) => update('desired_outcome', e.target.value)}
                className="input-field h-28 resize-none"
                placeholder="Describe the desired end state. What should be different when this is resolved?"
                autoFocus
              />
            </div>
          </>
        )}

        {step === 2 && (
          <>
            <h3 className="text-lg font-semibold text-gray-100">Business Impact</h3>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Business Impact</label>
              <textarea
                value={form.business_impact}
                onChange={(e) => update('business_impact', e.target.value)}
                className="input-field h-28 resize-none"
                placeholder="What is the business impact? Include cost, quality, safety, or compliance implications."
                autoFocus
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Urgency</label>
              <select
                value={form.urgency}
                onChange={(e) => update('urgency', e.target.value)}
                className="input-field"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
          </>
        )}

        {step === 3 && (
          <>
            <h3 className="text-lg font-semibold text-gray-100">Requester Information</h3>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Your Name</label>
              <input
                value={form.requester_name}
                onChange={(e) => update('requester_name', e.target.value)}
                className="input-field"
                placeholder="Full name"
                autoFocus
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Email</label>
              <input
                type="email"
                value={form.requester_email}
                onChange={(e) => update('requester_email', e.target.value)}
                className="input-field"
                placeholder="email@company.com"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Department</label>
              <input
                value={form.requester_dept}
                onChange={(e) => update('requester_dept', e.target.value)}
                className="input-field"
                placeholder="Department or business unit"
              />
            </div>
          </>
        )}

        {error && (
          <div className="px-3 py-2 rounded-md bg-red-500/10 border border-red-500/30 text-sm text-red-400">
            {error}
          </div>
        )}

        {/* Navigation */}
        <div className="flex items-center justify-between pt-2">
          <button
            onClick={() => setStep((s) => s - 1)}
            disabled={step === 0}
            className="btn-secondary btn-sm"
          >
            <ChevronLeft size={14} /> Back
          </button>

          {step < STEPS.length - 1 ? (
            <button
              onClick={() => setStep((s) => s + 1)}
              disabled={!canAdvance()}
              className="btn-primary btn-sm"
            >
              Next <ChevronRight size={14} />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={!canAdvance() || submitting}
              className="btn-primary btn-sm"
            >
              <Send size={14} /> {submitting ? 'Submitting...' : 'Submit Request'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
