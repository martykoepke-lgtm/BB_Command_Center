import { useState, useMemo } from 'react';
import { ChevronUp, ChevronDown, ChevronsUpDown, ChevronLeft, ChevronRight } from 'lucide-react';
import { clsx } from 'clsx';

export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => React.ReactNode;
  sortable?: boolean;
  width?: string;
  align?: 'left' | 'center' | 'right';
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyField?: string;
  onRowClick?: (row: T) => void;
  page?: number;
  perPage?: number;
  total?: number;
  onPageChange?: (page: number) => void;
  isLoading?: boolean;
  emptyMessage?: string;
  dense?: boolean;
}

type SortDir = 'asc' | 'desc' | null;

export function DataTable<T extends object>({
  columns, data, keyField = 'id', onRowClick,
  page, perPage = 25, total, onPageChange,
  isLoading, emptyMessage = 'No data found', dense = false,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>(null);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : sortDir === 'desc' ? null : 'asc');
      if (sortDir === 'desc') setSortKey(null);
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const field = (row: T, key: string): unknown => (row as Record<string, unknown>)[key];

  const sortedData = useMemo(() => {
    if (!sortKey || !sortDir) return data;
    return [...data].sort((a, b) => {
      const aVal = field(a, sortKey); const bVal = field(b, sortKey);
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      const cmp = String(aVal).localeCompare(String(bVal), undefined, { numeric: true });
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [data, sortKey, sortDir]);

  const totalPages = total ? Math.ceil(total / perPage) : 1;

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-surface-border">
            {columns.map((col) => (
              <th key={col.key}
                className={clsx('px-4 py-3 text-xs font-medium text-surface-muted uppercase tracking-wider text-left',
                  col.sortable && 'cursor-pointer select-none hover:text-gray-300',
                  col.align === 'center' && 'text-center', col.align === 'right' && 'text-right')}
                style={col.width ? { width: col.width } : undefined}
                onClick={() => col.sortable && handleSort(col.key)}>
                <span className="inline-flex items-center gap-1">
                  {col.header}
                  {col.sortable && (sortKey === col.key
                    ? (sortDir === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />)
                    : <ChevronsUpDown size={14} className="opacity-30" />)}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {isLoading ? (
            <tr><td colSpan={columns.length} className="px-4 py-12 text-center text-surface-muted">
              <div className="flex items-center justify-center gap-2">
                <div className="w-4 h-4 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />Loading...
              </div>
            </td></tr>
          ) : sortedData.length === 0 ? (
            <tr><td colSpan={columns.length} className="px-4 py-12 text-center text-surface-muted">{emptyMessage}</td></tr>
          ) : sortedData.map((row) => (
            <tr key={String(field(row, keyField))}
              className={clsx('border-b border-surface-border/50 transition-colors', onRowClick && 'cursor-pointer hover:bg-surface-hover/50')}
              onClick={() => onRowClick?.(row)}>
              {columns.map((col) => (
                <td key={col.key} className={clsx('px-4', dense ? 'py-2' : 'py-3', 'text-sm text-gray-200',
                  col.align === 'center' && 'text-center', col.align === 'right' && 'text-right')}>
                  {col.render ? col.render(row) : String(field(row, col.key) ?? '-')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {page !== undefined && onPageChange && total !== undefined && totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-surface-border">
          <span className="text-sm text-surface-muted">{((page - 1) * perPage) + 1}–{Math.min(page * perPage, total)} of {total}</span>
          <div className="flex items-center gap-1">
            <button className="btn-ghost btn-sm" disabled={page <= 1} onClick={() => onPageChange(page - 1)}><ChevronLeft size={16} /></button>
            <span className="px-2 text-sm text-gray-300">{page} / {totalPages}</span>
            <button className="btn-ghost btn-sm" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}><ChevronRight size={16} /></button>
          </div>
        </div>
      )}
    </div>
  );
}
