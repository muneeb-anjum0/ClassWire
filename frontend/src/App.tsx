import React from 'react';
import './App.css';
import LegalPage from './components/LegalPage/LegalPage';
import { AuthProvider } from './context/AuthContext';
import DashboardPage from './features/dashboard/DashboardPage';

function App() {
  const pathName = typeof window === 'undefined' ? '/' : window.location.pathname;

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
