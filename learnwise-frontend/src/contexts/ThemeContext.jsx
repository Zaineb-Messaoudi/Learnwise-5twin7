import { createContext, useContext, useEffect, useMemo, useState } from 'react';

const ThemeContext = createContext(null);
function prefersDark() { return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false; }

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => window.localStorage.getItem('learnwise:theme') || 'system');
  const [systemDark, setSystemDark] = useState(prefersDark);
  useEffect(() => {
    const media = window.matchMedia?.('(prefers-color-scheme: dark)');
    const apply = () => {
      const prefersDarkMode = media?.matches ?? false;
      const dark = theme === 'dark' || (theme === 'system' && prefersDarkMode);
      setSystemDark(prefersDarkMode);
      document.documentElement.dataset.theme = dark ? 'dark' : 'light';
      document.documentElement.classList.toggle('dark', dark);
      document.documentElement.style.colorScheme = dark ? 'dark' : 'light';
    };
    apply();
    window.localStorage.setItem('learnwise:theme', theme);
    media?.addEventListener?.('change', apply);
    return () => media?.removeEventListener?.('change', apply);
  }, [theme]);
  const dark = theme === 'dark' || (theme === 'system' && systemDark);
  return <ThemeContext.Provider value={useMemo(() => ({ theme, setTheme, dark }), [theme, dark])}>{children}</ThemeContext.Provider>;
}
export function useTheme() { const value = useContext(ThemeContext); if (!value) throw new Error('useTheme must be used inside ThemeProvider'); return value; }
