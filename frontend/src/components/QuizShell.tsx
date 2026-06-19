import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { cn } from '@/lib/utils';

// Exit affordance styled to echo the site navbar: a back-arrow + monospace,
// uppercase, wide-tracked label, muted until hover. Matches the nav links and
// the progress readout on the right so the immersive shell still feels native.
const exitClass = cn(
  'inline-flex items-center gap-1.5 -ml-1 rounded-md px-2 py-1',
  'font-mono text-xs font-semibold uppercase tracking-wider',
  'text-muted-foreground transition-colors hover:text-foreground',
);

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
    <div className="fixed inset-0 z-50 flex flex-col overflow-y-auto bg-background">
      <header className="flex h-12 shrink-0 items-center justify-between border-b border-border px-4">
        {exitTo ? (
          <Link to={exitTo} className={exitClass} title="ホームへ戻る">
            <ArrowLeft className="size-3.5" />
            ホーム
          </Link>
        ) : (
          <button type="button" onClick={onExit} className={exitClass} title="ホームへ戻る">
            <ArrowLeft className="size-3.5" />
            ホーム
          </button>
        )}
        <div className="font-mono text-xs tracking-wider text-muted-foreground uppercase">{right}</div>
      </header>
      <div className="flex flex-1 flex-col">{children}</div>
    </div>
  );
}
