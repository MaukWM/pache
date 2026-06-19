import { useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';
import { Button } from '@/components/ui/button';

// Minimal theme switch: toggles `.dark` on <html> and remembers the choice.
// ponytail: no provider/context — one localStorage key is enough for an app-wide flag.
function apply(dark: boolean) {
  document.documentElement.classList.toggle('dark', dark);
}

export function ThemeToggle({ className }: { className?: string }) {
  const [dark, setDark] = useState(
    () => document.documentElement.classList.contains('dark'),
  );

  useEffect(() => {
    apply(dark);
    localStorage.setItem('theme', dark ? 'dark' : 'light');
  }, [dark]);

  return (
    <Button
      variant="ghost"
      size="icon"
      className={className}
      aria-label="Toggle theme"
      onClick={() => setDark((d) => !d)}
    >
      {dark ? <Sun className="size-4" /> : <Moon className="size-4" />}
    </Button>
  );
}
