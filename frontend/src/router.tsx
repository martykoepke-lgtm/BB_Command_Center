import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppShell } from '@/components/layout/AppShell';
import { LoginPage } from '@/pages/LoginPage';
import { RegisterPage } from '@/pages/RegisterPage';
import { PortfolioDashboard } from '@/pages/PortfolioDashboard';
import { RequestQueue } from '@/pages/RequestQueue';
import { RequestForm } from '@/pages/RequestForm';
import { RequestDetail } from '@/pages/RequestDetail';
import { InitiativeList } from '@/pages/InitiativeList';
import { InitiativeProfile } from '@/pages/InitiativeProfile';
import { PhaseWorkspace } from '@/pages/PhaseWorkspace';
import { ActionBoard } from '@/pages/ActionBoard';
import { DataView } from '@/pages/DataView';
import { ReportsPage } from '@/pages/ReportsPage';
import { TeamsPage } from '@/pages/TeamsPage';
import { PipelineDashboard } from '@/pages/PipelineDashboard';
import { MyWork } from '@/pages/MyWork';
import { AuthGuard } from '@/components/auth/AuthGuard';

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/register',
    element: <RegisterPage />,
  },
  {
    path: '/',
    element: (
      <AuthGuard>
        <AppShell />
      </AuthGuard>
    ),
    children: [
      { index: true, element: <Navigate to="/my-work" replace /> },
      { path: 'my-work', element: <MyWork /> },
      { path: 'dashboard', element: <PortfolioDashboard /> },
      { path: 'requests', element: <RequestQueue /> },
      { path: 'requests/new', element: <RequestForm /> },
      { path: 'requests/:id', element: <RequestDetail /> },
      { path: 'initiatives', element: <InitiativeList /> },
      { path: 'initiatives/:id', element: <InitiativeProfile /> },
      { path: 'initiatives/:id/:phase', element: <PhaseWorkspace /> },
      { path: 'actions', element: <ActionBoard /> },
      { path: 'data', element: <DataView /> },
      { path: 'reports', element: <ReportsPage /> },
      { path: 'teams', element: <TeamsPage /> },
      { path: 'pipeline', element: <PipelineDashboard /> },
    ],
  },
]);
