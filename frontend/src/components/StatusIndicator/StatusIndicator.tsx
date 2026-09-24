import React from 'react';
import { AlertCircle, CheckCircle, Clock, LoaderCircle, X } from 'lucide-react';
import './StatusIndicator.css';

interface StatusIndicatorProps {
  status: 'loading' | 'success' | 'error' | 'warning';
  message: string;
  closing?: boolean;
  onDismiss?: () => void;
  tone?: 'default' | 'backend-wake';
}

const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  message,
  closing = false,
  onDismiss,
  tone = 'default',
}) => {
  const icon = {
    loading: <LoaderCircle />,
    success: <CheckCircle />,
    error: <AlertCircle />,
    warning: <Clock />,
  }[status];

  return (
    <div
      className={`status-toast status-toast--${status} ${tone === 'backend-wake' ? 'status-toast--backend-wake' : ''} ${closing ? 'status-toast--closing' : ''}`}
      role="status"
      aria-live="polite"
    >
      <div className="status-indicator">
        <div className="status-indicator__inner">
          <div className={`status-indicator__icon ${status === 'loading' ? 'status-indicator__icon--loading' : ''}`}>
            {icon}
          </div>

          <p className="status-indicator__message-clean">{message}</p>

          {onDismiss && status !== 'loading' && (
            <button type="button" onClick={onDismiss} className="status-indicator__dismiss" aria-label="Dismiss status">
              <X />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default StatusIndicator;
