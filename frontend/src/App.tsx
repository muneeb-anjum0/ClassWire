import React from 'react';
import './App.css';
import LegalPage from './components/LegalPage/LegalPage';
import { AuthProvider } from './context/AuthContext';
import DashboardPage from './features/dashboard/DashboardPage';

const SITE_URL = 'https://class-wire.vercel.app';
const PAGE_METADATA: Record<string, { title: string; description: string }> = {
  '/': {
    title: 'SZABIST Timetable Search & Class Schedule | ClassWire',
    description: 'Search SZABIST class schedules, courses, sections, and faculty availability from timetable emails with ClassWire.',
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
    return <LegalPage kind="privacy" />;
  }

  if (pathName === '/terms') {
    return <LegalPage kind="terms" />;
  }

  return (
    <AuthProvider>
      <DashboardPage />
    </AuthProvider>
  );
}

export default App;
