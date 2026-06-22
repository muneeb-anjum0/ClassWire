import { useCallback, useEffect, useState } from 'react';
import { BACKEND_WAKE_EVENT } from '../../services/api';
import { DashboardStatus } from './dashboardControllerTypes';
import { STATUS_TOAST_DURATION_MS, STATUS_TOAST_FADE_MS } from './utils';

export function useDashboardStatusToast() {
  const [status, setStatus] = useState<DashboardStatus>('idle');
  const [message, setMessage] = useState('');
  const [isBackendWaking, setIsBackendWaking] = useState(false);
  const [isStatusToastClosing, setIsStatusToastClosing] = useState(false);

  const showStatus = useCallback((nextStatus: DashboardStatus, nextMessage: string) => {
    setStatus(nextStatus);
    setMessage(nextMessage);
  }, []);

  const dismissStatus = useCallback(() => {
    if (isBackendWaking || status === 'loading') {
      return;
    }

    setIsStatusToastClosing(true);
  }, [isBackendWaking, status]);

  useEffect(() => {
    const handleBackendWakeState = (event: Event) => {
      const { active, message: wakeMessage } = (event as CustomEvent<{
        active: boolean;
        message?: string;
      }>).detail;

      setIsBackendWaking(active);
      if (active) {
        showStatus(
          'loading',
          wakeMessage ||
            'Backend is waking up on Render. First request after inactivity can take about a minute.',
        );
      }
    };

    window.addEventListener(BACKEND_WAKE_EVENT, handleBackendWakeState);
    return () => window.removeEventListener(BACKEND_WAKE_EVENT, handleBackendWakeState);
  }, [showStatus]);

  useEffect(() => {
    if (status !== 'idle' || isBackendWaking) {
      setIsStatusToastClosing(false);
    }
  }, [isBackendWaking, message, status]);

  useEffect(() => {
    if (isBackendWaking || status === 'idle' || status === 'loading' || !message) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setIsStatusToastClosing(true);
    }, STATUS_TOAST_DURATION_MS);

    return () => window.clearTimeout(timeoutId);
  }, [isBackendWaking, message, status]);

  useEffect(() => {
    if (!isStatusToastClosing) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setStatus('idle');
      setMessage('');
      setIsStatusToastClosing(false);
    }, STATUS_TOAST_FADE_MS);

    return () => window.clearTimeout(timeoutId);
  }, [isStatusToastClosing]);

  return {
    dismissStatus,
    isBackendWaking,
    isStatusToastClosing,
    message,
    setMessage,
    setStatus,
    showStatus,
    status,
  };
}
