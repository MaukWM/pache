import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Home } from 'lucide-react';
import { Button } from '@/components/ui/button';

// Full-screen immersive shell shared by the review session and the lesson quiz,
// so both have an identical feel: a thin top bar with an exit button on the
// left (home/back) and optional progress on the right, then the body filling
// the rest of the viewport. Renders over everything (no site navbar).
export function QuizShell({
  exitTo,
  onExit,
  right,
  children,
}: {
  /** Route to navigate to on exit (rendered as a link). */
  exitTo?: string;
  /** Or a callback to run on exit (rendered as a button). */
  onExit?: () => void;
  right?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="fixed inset-0 flex flex-col overflow-y-auto bg-background">
      <header className="flex h-12 shrink-0 items-center justify-between px-4">
        {exitTo ? (
          <Button asChild variant="ghost" size="icon" title="Exit" aria-label="Exit">
            <Link to={exitTo}>
              <Home className="size-5" />
            </Link>
          </Button>
        ) : (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onExit}
            title="Exit"
            aria-label="Exit"
          >
            <Home className="size-5" />
          </Button>
        )}
        <div className="text-sm font-medium text-muted-foreground">{right}</div>
      </header>
      <div className="flex flex-1 flex-col">{children}</div>
    </div>
  );
}
