import { Outlet, NavLink, useNavigate } from 'react-router';
import { useState } from 'react';
import { useTheme } from 'next-themes';
import { Users, ShieldCheck, Send, FlaskConical, ScrollText, ArrowDownLeft, Menu, Moon, Sun, LogOut } from 'lucide-react';
import { Button } from '../ui/button';
import { cn } from '../ui/utils';
import { useAuth } from '../../../contexts/AuthContext';

const navItems = [
  { to: '/', label: 'Patients', icon: Users, end: true },
  { to: '/claims', label: 'NHCX Claims', icon: ShieldCheck },
  { to: '/callbacks', label: 'Callbacks', icon: ArrowDownLeft },
  { to: '/send', label: 'Send Request', icon: Send },
  { to: '/sandbox', label: 'Sandbox Tools', icon: FlaskConical },
  { to: '/logs', label: 'Request Logs', icon: ScrollText },
];

export function MainLayout() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const { resolvedTheme, setTheme } = useTheme();
  const [collapsed, setCollapsed] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <aside
        className={cn(
          'flex flex-col border-r bg-card transition-all duration-200',
          collapsed ? 'w-16' : 'w-60',
        )}
      >
        <div className="flex h-14 items-center gap-2 border-b px-4">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground text-sm font-bold">
            N
          </div>
          {!collapsed && <span className="truncate font-semibold">NHCX</span>}
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto p-2">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors',
                  isActive
                    ? 'bg-primary/10 font-medium text-primary'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                )
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              {!collapsed && <span className="truncate">{label}</span>}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center gap-3 border-b bg-card px-4">
          <Button variant="ghost" size="icon" onClick={() => setCollapsed((c) => !c)}>
            <Menu className="h-4 w-4" />
          </Button>
          <div className="ml-auto flex items-center gap-1">
            <Button variant="ghost" size="icon" onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}>
              {resolvedTheme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>
            <Button variant="ghost" size="icon" onClick={handleLogout} title="Logout">
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
