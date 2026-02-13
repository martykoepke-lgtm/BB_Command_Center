import { useState, useCallback } from 'react';
import { Upload, Database, BarChart3, FileSpreadsheet } from 'lucide-react';
import { datasetsApi, type DatasetOut } from '@/api/datasets';
import { EmptyState } from '@/components/shared/EmptyState';

export function DataView() {
  const [datasets, setDatasets] = useState<DatasetOut[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const handleUpload = useCallback(async (file: File) => {
    setUploading(true);
    try { const ds = await datasetsApi.upload('default', file); setDatasets((p) => [ds, ...p]); }
    catch (e) { console.error('Upload failed:', e); }
    finally { setUploading(false); }
  }, []);
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f && (f.name.endsWith('.csv') || f.name.endsWith('.xlsx') || f.name.endsWith('.xls'))) handleUpload(f);
  }, [handleUpload]);
  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => { const f = e.target.files?.[0]; if (f) handleUpload(f); }, [handleUpload]);

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold text-gray-100">Data & Analysis</h2>
      <div className={`card p-8 border-2 border-dashed text-center transition-colors ${dragOver ? 'border-brand-500 bg-brand-500/5' : 'border-surface-border'}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }} onDragLeave={() => setDragOver(false)} onDrop={handleDrop}>
        <Upload size={32} className="mx-auto mb-3 text-surface-muted" />
        <p className="text-sm text-gray-300 mb-1">{uploading ? 'Uploading...' : 'Drag & drop CSV or Excel files here'}</p>
        <p className="text-xs text-surface-muted mb-3">or click to browse</p>
        <label className="btn-primary btn-sm cursor-pointer"><FileSpreadsheet size={14} /> Choose File<input type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={handleFileInput} /></label>
      </div>
      {datasets.length === 0 ? <EmptyState icon={<Database size={40} />} title="No datasets uploaded" description="Upload a CSV or Excel file to start analyzing data." /> : (
        <div className="space-y-3"><h3 className="text-sm font-semibold text-gray-200">Datasets</h3>
          {datasets.map((ds) => (
            <div key={ds.id} className="card-hover p-4 flex items-center gap-4">
              <FileSpreadsheet size={20} className="text-brand-400 shrink-0" />
              <div className="flex-1"><p className="text-sm font-medium text-gray-200">{ds.name}</p><p className="text-xs text-surface-muted">{ds.row_count ?? '?'} rows, {ds.column_count ?? '?'} columns · {ds.file_type}</p></div>
              <button className="btn-secondary btn-sm"><BarChart3 size={14} /> Analyze</button>
            </div>))}
        </div>
      )}
    </div>
  );
}
