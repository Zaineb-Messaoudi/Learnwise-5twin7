import { NavLink } from 'react-router-dom';
import { BarChart3, BookOpen, Grid2X2, Sparkles } from 'lucide-react';
export function MobileNavbar() { return <nav className="mobile-navbar" aria-label="Mobile navigation"><NavLink to="/student/dashboard"><Grid2X2 size={17}/><span>Home</span></NavLink><NavLink to="/student/courses"><BookOpen size={17}/><span>Learning</span></NavLink><NavLink to="/student/assistant"><Sparkles size={17}/><span>AI</span></NavLink><NavLink to="/student/progress"><BarChart3 size={17}/><span>Progress</span></NavLink></nav>; }
