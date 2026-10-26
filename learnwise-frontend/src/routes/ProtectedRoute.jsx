import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

function getRouteRole(backendRole) {
    const map = { etudiant: 'student', professeur: 'teacher', admin: 'admin' };
    return map[backendRole] || 'student';
}

export function ProtectedRoute({ role, children }) {
    const { user } = useAuth();
    const location = useLocation();
    if (!user)
        return <Navigate to={`/auth/login?next=${encodeURIComponent(location.pathname)}`} replace/>;
    if (getRouteRole(user.role) !== role)
        return <Navigate to={`/${getRouteRole(user.role)}/dashboard`} replace/>;
    return <>{children}</>;
}
