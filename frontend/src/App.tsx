import React, { Suspense, lazy } from 'react';
import './App.css';
import { AuthProvider, useAuth } from './context/AuthContext';

const DashboardPage = lazy(() => import('./features/dashboard/DashboardPage'));
const LegalPage = lazy(() => import('./components/LegalPage/LegalPage'));
const LoginScreen = lazy(() => import('./components/LoginScreen/LoginScreen'));

const SITE_URL = 'https://class-wire.vercel.app';
const PAGE_METADATA: Record<string, { title: string; description: string }> = {
  '/': {
    title: 'SZABIST Timetable & Class Schedule Search | ClassWire',
    description: 'Search SZABIST Islamabad timetables, class schedules, courses, sections, and faculty availability from your timetable emails.',
  },
  '/privacy': {
    title: 'Privacy Policy | ClassWire',
    description: 'Learn how ClassWire handles Gmail access, SZABIST timetable data, authentication, and optional schedule delivery.',
  },
  '/terms': {
    title: 'Terms of Service | ClassWire',
    description: 'Read the terms for using ClassWire to search and organize SZABIST timetable emails and class schedules.',
  },
};

const updateMetaContent = (selector: string, value: string) => {
  document.querySelector<HTMLMetaElement>(selector)?.setAttribute('content', value);
};

const PageFallback = () => (
  <main className="app-loading" aria-label="Loading ClassWire">
    <span>ClassWire</span>
  </main>
);

function AuthenticatedApp() {
  const auth = useAuth();
  return auth.isAuthenticated ? <DashboardPage /> : <LoginScreen />;
}

function App() {
  const pathName = typeof window === 'undefined' ? '/' : window.location.pathname;
  const metadata = PAGE_METADATA[pathName] || PAGE_METADATA['/'];

  React.useEffect(() => {
    const canonicalUrl = `${SITE_URL}${pathName === '/' ? '/' : pathName}`;
    document.title = metadata.title;
    document.querySelector<HTMLLinkElement>('link[rel="canonical"]')?.setAttribute('href', canonicalUrl);
    updateMetaContent('meta[name="description"]', metadata.description);
    updateMetaContent('meta[property="og:title"]', metadata.title);
    updateMetaContent('meta[property="og:description"]', metadata.description);
    updateMetaContent('meta[property="og:url"]', canonicalUrl);
    updateMetaContent('meta[name="twitter:title"]', metadata.title);
    updateMetaContent('meta[name="twitter:description"]', metadata.description);
  }, [metadata.description, metadata.title, pathName]);

  if (pathName === '/privacy') {
    return <Suspense fallback={<PageFallback />}><LegalPage kind="privacy" /></Suspense>;
  }

  if (pathName === '/terms') {
    return <Suspense fallback={<PageFallback />}><LegalPage kind="terms" /></Suspense>;
  }

  return (
    <AuthProvider>
      <Suspense fallback={<PageFallback />}>
        <AuthenticatedApp />
      </Suspense>
    </AuthProvider>
  );
}

export default App;
