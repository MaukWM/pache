import { Toaster as Sonner, type ToasterProps } from 'sonner';

// Reads the app's own .dark class rather than next-themes (we manage theme
// directly on <html>), so toasts match light/dark without an extra provider.
function Toaster(props: ToasterProps) {
  const theme =
    typeof document !== 'undefined' && document.documentElement.classList.contains('dark')
      ? 'dark'
      : 'light';
  return (
    <Sonner
      theme={theme}
      className="toaster group"
      style={
        {
          '--normal-bg': 'var(--popover)',
          '--normal-text': 'var(--popover-foreground)',
          '--normal-border': 'var(--border)',
        } as React.CSSProperties
      }
      {...props}
    />
  );
}

export { Toaster };
