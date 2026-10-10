import { Menu, Moon, Search, Sun } from 'lucide-react';
import { NotificationBell } from '../ui/NotificationBell';

export function TopNavbar({ dark, onToggle, onMenu }) {
  return (
    <header className="app-topbar">
      <button className="icon-button menu-button" onClick={onMenu} aria-label="Open navigation"><Menu size={20} /></button>
      <span className="breadcrumb"><b>Workspace</b></span>
      <div className="top-actions">
        <button className="icon-button" aria-label="Search"><Search size={18} /></button>
        <button className="icon-button" onClick={onToggle} aria-label="Toggle color theme">{dark ? <Sun size={18} /> : <Moon size={18} />}</button>
        <NotificationBell />
      </div>
    </header>
  );
}
