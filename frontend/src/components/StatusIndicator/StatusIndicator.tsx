import React from 'react';
import './StatusIndicator.css';
import { AlertCircle, CheckCircle, Clock, Loader, X } from 'lucide-react';

interface StatusIndicatorProps {
  status: 'loading' | 'success' | 'error' | 'warning';
  message: string;
  closing?: boolean;
  onDismiss?: () => void;
}

const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  message,
  closing = false,
  onDismiss,
}) => {
  const getStatusIcon = () => {
    switch (status) {
      case 'loading':
        return <Loader className="animate-spin h-5 w-5" />;
      case 'success':
        return <CheckCircle className="h-5 w-5" />;
      case 'error':
        return <AlertCircle className="h-5 w-5" />;
      case 'warning':
        return <Clock className="h-5 w-5" />;
      default:
        return <AlertCircle className="h-5 w-5" />;
    }
  };

  const getStatusTheme = () => {
    switch (status) {
      case 'loading':
        return {
          accent: 'status-indicator--loading',
          glass: 'status-indicator-glass--loading',
          badge: 'status-indicator__badge--loading',
          title: 'theme-text-primary',
          subtitle: 'theme-text-secondary',
        };
      case 'success':
        return {
          accent: 'status-indicator--success',
          glass: 'status-indicator-glass--success',
          badge: 'status-indicator__badge--success',
          title: 'theme-text-primary',
          subtitle: 'theme-text-secondary',
        };
      case 'error':
        return {
          accent: 'status-indicator--error',
          glass: 'status-indicator-glass--error',
          badge: 'status-indicator__badge--error',
          title: 'theme-text-primary',
          subtitle: 'theme-text-secondary',
        };
      case 'warning':
        return {
          accent: 'status-indicator--warning',
          glass: 'status-indicator-glass--warning',
          badge: 'status-indicator__badge--warning',
          title: 'theme-text-primary',
          subtitle: 'theme-text-secondary',
        };
      default:
        return {
          accent: 'status-indicator--idle',
          glass: 'status-indicator-glass--loading',
          badge: 'status-indicator__badge--loading',
          title: 'theme-text-primary',
          subtitle: 'theme-text-secondary',
        };
    }
  };

  const theme = getStatusTheme();

  return (
    <>
<div className={`status-toast status-toast--${status} ${closing ? 'status-toast--closing' : ''}`}>
        <div
          className={`status-indicator status-indicator-glass ${theme.glass} border shadow-sm overflow-hidden ${theme.accent}`}
        >
          <div className="status-indicator__inner status-indicator__inner-clean flex items-center gap-2 p-2.5">
          <div
            className={`status-indicator__icon status-indicator__icon-clean flex h-9 w-9 items-center justify-center ${
              status === 'loading' ? 'status-indicator__icon--loading' : ''
            }`}
          >
            {getStatusIcon()}
          </div>

            <div className="min-w-0 flex-1">
              <p
                className={`status-indicator__message-clean mt-0.5 text-[0.78rem] leading-snug ${theme.subtitle}`}
                title={message}
              >
                {message}
              </p>
            </div>

            {onDismiss && status !== 'loading' && (
              <button
                type="button"
                onClick={onDismiss}
                className="status-indicator__dismiss"
                aria-label="Dismiss status"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  );
};

export default StatusIndicator;
