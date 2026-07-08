import { Link, useLocation } from 'react-router-dom';
import { LogOut, User } from 'lucide-react';
import { useAuth } from '../lib/auth';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ThemeToggle } from './ThemeToggle';

// Each section carries its own ink: kanji = pink, vocab = purple, dashboard = paper.
const NAV_LINKS = [
  { to: '/', label: 'ダッシュボード', ink: 'text-foreground', rule: 'bg-foreground' },
  { to: '/kanji', label: '漢字', ink: 'text-wk-kanji', rule: 'bg-wk-kanji' },
  { to: '/vocab', label: '語彙', ink: 'text-wk-vocab', rule: 'bg-wk-vocab' },
  { to: '/sentences', label: '作文', ink: 'text-wk-sentence', rule: 'bg-wk-sentence' },
];

export function Navbar() {
  const { user, logout } = useAuth();
  const location = useLocation();

  return (
    <nav className="sticky top-0 z-30 border-b border-border bg-background/85 backdrop-blur">
      <div className="mx-auto grid h-14 max-w-6xl grid-cols-[1fr_auto_1fr] items-center gap-4 px-4">
        <Link to="/" className="flex items-center gap-2.5 justify-self-start">
          <span
            lang="ja"
            className="grid size-7 place-items-center bg-foreground font-[family-name:var(--font-mincho)] text-sm text-background"
          >
            字
          </span>
          <span className="hidden font-mono text-sm font-bold tracking-[0.18em] uppercase sm:inline">
            pache
          </span>
        </Link>

        <div className="flex h-full items-stretch gap-1 justify-self-center">
          {NAV_LINKS.map(({ to, label, rule }) => {
            const active = location.pathname === to;
            return (
              <Link
                key={to}
                to={to}
                className={cn(
                  'relative flex items-center px-4 font-mono text-xs font-semibold tracking-wider uppercase transition-colors',
                  active ? 'text-foreground' : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {label}
                {/* thin type-ink underline is the only color accent (kanji pink / vocab purple) */}
                {active && <span className={cn('absolute inset-x-0 bottom-0 h-0.5', rule)} />}
              </Link>
            );
          })}
        </div>

        <div className="flex items-center gap-1 justify-self-end">
          <ThemeToggle />
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" className="gap-2 normal-case tracking-normal">
                <span className="grid size-6 place-items-center bg-secondary font-mono text-xs font-bold text-foreground">
                  {user?.username?.[0]?.toUpperCase() ?? '?'}
                </span>
                <span className="hidden max-w-28 truncate font-mono text-xs sm:inline">
                  {user?.username}
                </span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-44">
              <DropdownMenuLabel className="truncate font-mono text-xs uppercase tracking-wider">
                {user?.username}
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link to="/account">
                  <User className="size-4" />
                  アカウント
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem variant="destructive" onSelect={() => logout()}>
                <LogOut className="size-4" />
                ログアウト
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </nav>
  );
}
