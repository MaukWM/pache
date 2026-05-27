import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../lib/auth';

const NAV_LINKS = [
  { to: '/', label: 'Dashboard' },
  { to: '/kanji', label: 'Kanji' },
  { to: '/vocab', label: 'Vocab' },
];

export function Navbar() {
  const { user } = useAuth();
  const location = useLocation();

  return (
    <nav className="bg-wk-kanji text-white shadow-lg">
      <div className="max-w-6xl mx-auto px-4">
        <div className="flex items-center justify-between h-14">
          <Link to="/" className="text-lg font-bold tracking-wide">
            iwkisgwitnwk2
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
            <Link
              to="/account"
              className={`text-sm px-3 py-1.5 rounded transition-colors ${
                location.pathname === '/account' ? 'bg-white/20' : 'hover:bg-white/10'
              }`}
            >
              {user?.username}
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}
