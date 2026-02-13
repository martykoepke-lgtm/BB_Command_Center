import { useState } from 'react';
import { FileText, Download, Send, Eye } from 'lucide-react';
import { reportsApi, type ReportOut } from '@/api/reports';
import { EmptyState } from '@/components/shared/EmptyState';

const REPORT_TYPES = [
  { value: 'phase_gate', label: 'Phase Gate Review', description: 'Formal gate review for phase transition' },
  { value: 'executive_summary', label: 'Executive Summary', description: 'High-level overview for leadership' },
  { value: 'statistical_results', label: 'Statistical Results', description: 'Translated analysis results' },
  { value: 'close_out', label: 'Close-out Report', description: 'Final project close-out documentation' },
  { value: 'portfolio_rollup', label: 'Portfolio Roll-up', description: 'Cross-initiative portfolio summary' },
];

export function ReportsPage() {
  const [selectedType, setSelectedType] = useState('');
  const [generating, setGenerating] = useState(false);
  const [reports, setReports] = useState<ReportOut[]>([]);
  const handleGenerate = async () => {
    if (!selectedType) return; setGenerating(true);
    try { const r = await reportsApi.generate({ report_type: selectedType }); setReports((p) => [r, ...p]); setSelectedType(''); }
    catch { /* handle */ } finally { setGenerating(false); }
  };
  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold text-gray-100">Reports</h2>
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-gray-200 mb-3">Generate Report</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {REPORT_TYPES.map((t) => (
            <button key={t.value} onClick={() => setSelectedType(t.value)}
              className={`text-left p-3 rounded-lg border transition-colors ${selectedType === t.value ? 'border-brand-500 bg-brand-500/10' : 'border-surface-border hover:border-surface-muted'}`}>
              <p className="text-sm font-medium text-gray-200">{t.label}</p>
              <p className="text-xs text-surface-muted mt-0.5">{t.description}</p>
            </button>))}
        </div>
        {selectedType && <div className="mt-4"><button onClick={handleGenerate} disabled={generating} className="btn-primary btn-sm"><FileText size={14} /> {generating ? 'Generating...' : 'Generate Report'}</button></div>}
      </div>
      {reports.length === 0 ? <EmptyState icon={<FileText size={40} />} title="No reports generated" description="Select a report type above to generate your first report." /> : (
        <div className="space-y-3"><h3 className="text-sm font-semibold text-gray-200">Generated Reports</h3>
          {reports.map((r) => (
            <div key={r.id} className="card p-4 flex items-center justify-between">
              <div><p className="text-sm font-medium text-gray-200">{r.title}</p><p className="text-xs text-surface-muted">{r.report_type.replace(/_/g, ' ')} · {new Date(r.generated_at).toLocaleString()}</p></div>
              <div className="flex items-center gap-1"><button className="btn-ghost btn-sm" title="Preview"><Eye size={14} /></button><button className="btn-ghost btn-sm" title="Download"><Download size={14} /></button><button className="btn-ghost btn-sm" title="Send"><Send size={14} /></button></div>
            </div>))}
        </div>
      )}
    </div>
  );
}
