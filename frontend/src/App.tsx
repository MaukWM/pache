import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './lib/auth';
import { Toaster } from '@/components/ui/sonner';
import { Layout } from './components/Layout';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { KanjiPage } from './pages/KanjiPage';
import { KanjiDetailPage } from './pages/KanjiDetailPage';
import { VocabPage } from './pages/VocabPage';
import { VocabDetailPage } from './pages/VocabDetailPage';
import { LessonsPage } from './pages/LessonsPage';
import { ReviewPage } from './pages/ReviewPage';
import { AccountPage } from './pages/AccountPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

function ProtectedRoutes() {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="kanji" element={<KanjiPage />} />
        <Route path="kanji/:char" element={<KanjiDetailPage />} />
        <Route path="vocab" element={<VocabPage />} />
        <Route path="vocab/:id" element={<VocabDetailPage />} />
        <Route path="account" element={<AccountPage />} />
      </Route>
      {/* Lessons + reviews run full-screen (no navbar) for an immersive session. */}
      <Route path="lessons" element={<LessonsPage />} />
      <Route path="reviews" element={<ReviewPage />} />
    </Routes>
  );
}

function AppRoutes() {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />}
      />
      <Route path="/*" element={<ProtectedRoutes />} />
    </Routes>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
        <Toaster position="bottom-right" richColors />
      </AuthProvider>
    </QueryClientProvider>
  );
}
