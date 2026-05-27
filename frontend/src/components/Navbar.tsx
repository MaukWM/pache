import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../lib/auth';

const NAV_LINKS = [
  { to: '/', label: 'Dashboard' },
  { to: '/reviews', label: 'Reviews' },
  { to: '/lessons', label: 'Lessons' },
  { to: '/vocab', label: 'Vocab' },
  { to: '/kanji', label: 'Kanji' },
  { to: '/progress', label: 'Progress' },
];

export function Navbar() {
  const { user, logout } = useAuth();
  const location = useLocation();

  return (
    <nav className="bg-wk-kanji text-white shadow-lg">
      <div className="max-w-6xl mx-auto px-4">
        <div className="flex items-center justify-between h-14">
          <Link to="/" className="text-lg font-bold tracking-wide">
            KanjiSRS
          </Link>

          <div className="flex items-center gap-1">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                  location.pathname === link.to
                    ? 'bg-white/20'
                    : 'hover:bg-white/10'
                }`}
              >
                {link.label}
              </Link>
            ))}
          </div>

          <div className="flex items-center gap-3">
            <span className="text-sm opacity-80">{user?.username}</span>
            <button
              onClick={logout}
              className="text-sm px-3 py-1 rounded bg-white/10 hover:bg-white/20 transition-colors"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
