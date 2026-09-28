import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
export function ProtectedRoute({ role, children }) {
    const { user } = useAuth();
    const location = useLocation();
    if (!user)
        return <Navigate to={`/auth/login?next=${encodeURIComponent(location.pathname)}`} replace/>;
    if (user.role !== role)
        return <Navigate to={`/${user.role}/dashboard`} replace/>;
    return <>{children}</>;
}
