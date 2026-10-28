import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

function getRouteRole(backendRole) {
    const map = { etudiant: 'student', professeur: 'teacher', admin: 'admin' };
    return map[backendRole] || 'student';
}

export function ProtectedRoute({ role, children }) {
    const { user } = useAuth();
    const location = useLocation();
    const next = encodeURIComponent(location.pathname + location.search);
    if (!user)
        return <Navigate to={`/auth/login?next=${next}`} replace/>;
    if (getRouteRole(user.role) !== role)
        return <Navigate to={`/${getRouteRole(user.role)}/dashboard`} replace/>;
    return <>{children}</>;
}
