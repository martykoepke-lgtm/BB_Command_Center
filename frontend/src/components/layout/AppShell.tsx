import { Outlet } from 'react-router-dom';
import { clsx } from 'clsx';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { AIPanel } from './AIPanel';
import { useUIStore } from '@/stores/uiStore';

export function AppShell() {
  const { sidebarCollapsed, aiPanelOpen } = useUIStore();

  return (
    <div className="min-h-screen bg-surface-bg">
      <Sidebar />
      <AIPanel />

      <div
        className={clsx(
          'transition-all duration-200',
          sidebarCollapsed ? 'ml-16' : 'ml-56',
          aiPanelOpen && 'mr-96',
        )}
      >
        <TopBar />
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
