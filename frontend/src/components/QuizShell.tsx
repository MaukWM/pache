import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

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
  const exitClass = 'text-text-muted hover:text-text text-2xl leading-none';
  return (
    <div className="fixed inset-0 bg-bg flex flex-col overflow-y-auto">
      <header className="flex items-center justify-between px-4 h-12 shrink-0">
        {exitTo ? (
          <Link to={exitTo} title="Exit" aria-label="Exit" className={exitClass}>
            ⌂
          </Link>
        ) : (
          <button type="button" onClick={onExit} title="Exit" aria-label="Exit" className={exitClass}>
            ⌂
          </button>
        )}
        <div className="text-sm font-medium text-text-muted">{right}</div>
      </header>
      <div className="flex-1 flex flex-col">{children}</div>
    </div>
  );
}
