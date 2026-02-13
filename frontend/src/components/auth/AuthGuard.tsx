import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { authApi } from '@/api/auth';
import { PageLoader } from '@/components/shared/LoadingSpinner';

interface AuthGuardProps {
  children: React.ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading, setUser, logout, setLoading } = useAuthStore();

  useEffect(() => {
    const token = localStorage.getItem('bb_token');
    if (!token) {
      setLoading(false);
      navigate('/login', { replace: true });
      return;
    }

    authApi.me()
      .then((user) => setUser(user))
      .catch(() => {
        logout();
        navigate('/login', { replace: true });
      });
  }, [navigate, setUser, logout, setLoading]);

  if (isLoading) return <PageLoader />;
  if (!isAuthenticated) return null;

  return <>{children}</>;
}
