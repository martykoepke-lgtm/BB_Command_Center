import { useLocation } from 'react-router-dom';
import { Bell, Search, Bot } from 'lucide-react';
import { useUIStore } from '@/stores/uiStore';

const routeTitles: Record<string, string> = {
  '/dashboard': 'Portfolio Dashboard',
  '/requests': 'Request Queue',
  '/requests/new': 'New Request',
  '/initiatives': 'Initiatives',
  '/actions': 'Action Items',
  '/data': 'Data & Analysis',
  '/reports': 'Reports',
  '/teams': 'Teams',
  '/pipeline': 'Pipeline',
  '/settings': 'Settings',
};

function getTitle(pathname: string): string {
  if (routeTitles[pathname]) return routeTitles[pathname];
  if (pathname.startsWith('/initiatives/') && pathname.includes('/')) return 'Initiative';
  if (pathname.startsWith('/requests/')) return 'Request Detail';
  if (pathname.startsWith('/teams/')) return 'Team';
  return 'BB Enabled Command';
}

export function TopBar() {
  const location = useLocation();
  const title = getTitle(location.pathname);
  const { toggleAIPanel } = useUIStore();

  return (
    <header className="h-14 bg-surface-card/80 backdrop-blur border-b border-surface-border flex items-center justify-between px-6 sticky top-0 z-20">
      <div>
        <h1 className="text-base font-semibold text-gray-100">{title}</h1>
      </div>

      <div className="flex items-center gap-2">
        <button className="btn-ghost btn-sm" title="Search">
          <Search size={16} />
        </button>
        <button className="btn-ghost btn-sm relative" title="Notifications">
          <Bell size={16} />
          <span className="absolute top-1 right-1 w-1.5 h-1.5 bg-red-500 rounded-full" />
        </button>
        <button
          onClick={toggleAIPanel}
          className="btn-ghost btn-sm text-teal-400 hover:text-teal-300"
          title="AI Assistant"
        >
          <Bot size={16} />
        </button>
      </div>
    </header>
  );
}
