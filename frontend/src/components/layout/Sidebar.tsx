import { NavLink } from 'react-router-dom';
import { clsx } from 'clsx';
import {
  LayoutDashboard,
  Inbox,
  Target,
  Users,
  CheckSquare,
  FileText,
  Bot,
  ChevronLeft,
  ChevronRight,
  LogOut,
  BarChart3,
  Database,
  Briefcase,
} from 'lucide-react';
import { useUIStore } from '@/stores/uiStore';
import { useAuthStore } from '@/stores/authStore';

interface NavItem {
  label: string;
  path: string;
  icon: React.ReactNode;
}

const mainNav: NavItem[] = [
  { label: 'My Work', path: '/my-work', icon: <Briefcase size={18} /> },
  { label: 'Dashboard', path: '/dashboard', icon: <LayoutDashboard size={18} /> },
  { label: 'Requests', path: '/requests', icon: <Inbox size={18} /> },
  { label: 'Initiatives', path: '/initiatives', icon: <Target size={18} /> },
  { label: 'Actions', path: '/actions', icon: <CheckSquare size={18} /> },
];

const dataNav: NavItem[] = [
  { label: 'Data & Analysis', path: '/data', icon: <Database size={18} /> },
  { label: 'Reports', path: '/reports', icon: <FileText size={18} /> },
];

const teamNav: NavItem[] = [
  { label: 'Teams', path: '/teams', icon: <Users size={18} /> },
  { label: 'Pipeline', path: '/pipeline', icon: <BarChart3 size={18} /> },
];

function NavSection({ title, items, collapsed }: { title: string; items: NavItem[]; collapsed: boolean }) {
  return (
    <div className="mb-4">
      {!collapsed && (
        <div className="px-4 py-1 text-[10px] font-semibold text-surface-muted uppercase tracking-widest">
          {title}
        </div>
      )}
      <nav className="space-y-0.5 px-2">
        {items.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                isActive
                  ? 'bg-brand-500/15 text-brand-400'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-surface-hover',
                collapsed && 'justify-center',
              )
            }
            title={collapsed ? item.label : undefined}
          >
            {item.icon}
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebar } = useUIStore();
  const { user, logout } = useAuthStore();

  return (
    <aside
      className={clsx(
        'fixed left-0 top-0 h-screen bg-surface-card border-r border-surface-border flex flex-col z-30 transition-all duration-200',
        sidebarCollapsed ? 'w-16' : 'w-56',
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-2 h-14 px-4 border-b border-surface-border shrink-0">
        <div className="w-7 h-7 rounded bg-brand-500 flex items-center justify-center text-white font-bold text-xs">
          BB
        </div>
        {!sidebarCollapsed && (
          <span className="text-sm font-semibold text-gray-100 truncate">BB Command</span>
        )}
      </div>

      {/* Nav groups */}
      <div className="flex-1 overflow-y-auto py-4">
        <NavSection title="Command" items={mainNav} collapsed={sidebarCollapsed} />
        <NavSection title="Analysis" items={dataNav} collapsed={sidebarCollapsed} />
        <NavSection title="Organization" items={teamNav} collapsed={sidebarCollapsed} />
      </div>

      {/* Bottom: AI, user, collapse */}
      <div className="border-t border-surface-border p-2 space-y-1">
        <button
          onClick={() => useUIStore.getState().toggleAIPanel()}
          className={clsx(
            'flex items-center gap-3 w-full px-3 py-2 rounded-md text-sm font-medium text-teal-400 hover:bg-teal-500/10 transition-colors',
            sidebarCollapsed && 'justify-center',
          )}
          title="AI Assistant"
        >
          <Bot size={18} />
          {!sidebarCollapsed && <span>AI Assistant</span>}
        </button>

        {user && !sidebarCollapsed && (
          <div className="px-3 py-1.5 text-xs text-surface-muted truncate" title={user.email}>
            {user.full_name}
          </div>
        )}

        <div className="flex items-center gap-1">
          <button
            onClick={logout}
            className={clsx(
              'flex items-center gap-2 px-3 py-2 rounded-md text-sm text-surface-muted hover:text-gray-200 hover:bg-surface-hover transition-colors',
              sidebarCollapsed ? 'w-full justify-center' : '',
            )}
            title="Sign out"
          >
            <LogOut size={16} />
            {!sidebarCollapsed && <span className="text-xs">Sign out</span>}
          </button>
          <button
            onClick={toggleSidebar}
            className="ml-auto p-1.5 rounded-md text-surface-muted hover:text-gray-200 hover:bg-surface-hover transition-colors"
            title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {sidebarCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>
      </div>
    </aside>
  );
}
