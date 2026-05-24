import React from 'react';
import { AlertCircle, CheckCircle, Clock, Loader } from 'lucide-react';

interface StatusIndicatorProps {
  status: 'loading' | 'success' | 'error' | 'warning';
  message: string;
}

const StatusIndicator: React.FC<StatusIndicatorProps> = ({ status, message }) => {
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

  const statusLabel =
    status === 'loading' && message.toLowerCase().includes('backend is waking')
      ? 'Starting backend'
      : status === 'loading'
      ? 'Running scraper'
      : status === 'success'
      ? 'Ready'
      : status === 'warning'
      ? 'Attention needed'
      : status === 'error'
      ? 'Action required'
      : 'Status';

  return (
    <>
      <style>
        {`
          .status-indicator-glass {
            position: relative;
            overflow: hidden;
            border-radius: 20px;
            backdrop-filter: blur(18px) saturate(150%);
            -webkit-backdrop-filter: blur(18px) saturate(150%);
            box-shadow:
              0 10px 28px rgba(15, 23, 42, 0.09),
              inset 0 1px 0 rgba(255, 255, 255, 0.18);
            animation: statusIndicatorIn 180ms cubic-bezier(.2,.8,.2,1);
            transition:
              transform 160ms ease,
              box-shadow 160ms ease,
              border-color 160ms ease;
          }

          .status-indicator-glass::before {
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
          }

          .status-indicator-glass--loading {
            border: 1px solid rgba(96, 165, 250, 0.28);
            background:
              linear-gradient(
                135deg,
                rgba(239, 246, 255, 0.42),
                rgba(219, 234, 254, 0.24),
                color-mix(in srgb, var(--theme-surface, #ffffff) 76%, transparent)
              );
          }

          .status-indicator-glass--loading::before {
            background:
              radial-gradient(circle at 12% 18%, rgba(147, 197, 253, 0.28), transparent 34%),
              radial-gradient(circle at 92% 80%, rgba(191, 219, 254, 0.18), transparent 34%);
          }

          .status-indicator-glass--success {
            border: 1px solid rgba(134, 239, 172, 0.28);
            background:
              linear-gradient(
                135deg,
                rgba(236, 253, 245, 0.42),
                rgba(220, 252, 231, 0.24),
                color-mix(in srgb, var(--theme-surface, #ffffff) 76%, transparent)
              );
          }

          .status-indicator-glass--success::before {
            background:
              radial-gradient(circle at 12% 18%, rgba(187, 247, 208, 0.28), transparent 34%),
              radial-gradient(circle at 92% 80%, rgba(167, 243, 208, 0.18), transparent 34%);
          }

          .status-indicator-glass--error {
            border: 1px solid rgba(252, 165, 165, 0.3);
            background:
              linear-gradient(
                135deg,
                rgba(254, 242, 242, 0.44),
                rgba(254, 226, 226, 0.24),
                color-mix(in srgb, var(--theme-surface, #ffffff) 76%, transparent)
              );
          }

          .status-indicator-glass--error::before {
            background:
              radial-gradient(circle at 12% 18%, rgba(252, 165, 165, 0.26), transparent 34%),
              radial-gradient(circle at 92% 80%, rgba(254, 202, 202, 0.18), transparent 34%);
          }

          .status-indicator-glass--warning {
            border: 1px solid rgba(253, 186, 116, 0.3);
            background:
              linear-gradient(
                135deg,
                rgba(255, 251, 235, 0.46),
                rgba(254, 243, 199, 0.26),
                color-mix(in srgb, var(--theme-surface, #ffffff) 76%, transparent)
              );
          }

          .status-indicator-glass--warning::before {
            background:
              radial-gradient(circle at 12% 18%, rgba(253, 186, 116, 0.28), transparent 34%),
              radial-gradient(circle at 92% 80%, rgba(254, 215, 170, 0.18), transparent 34%);
          }

          .status-indicator-glass:hover {
            transform: translateY(-1px);
            box-shadow:
              0 14px 34px rgba(15, 23, 42, 0.12),
              inset 0 1px 0 rgba(255, 255, 255, 0.2);
          }

          html[data-theme='dark'] .status-indicator-glass {
            box-shadow:
              0 10px 28px rgba(0, 0, 0, 0.3),
              inset 0 1px 0 rgba(255, 255, 255, 0.05);
          }

          html[data-theme='dark'] .status-indicator-glass--loading {
            border: 1px solid rgba(255, 255, 255, 0.08);
            background: linear-gradient(135deg, rgba(10, 10, 10, 0.98), rgba(18, 18, 18, 0.98));
          }

          html[data-theme='dark'] .status-indicator-glass--loading::before {
            background: none;
          }

          html[data-theme='dark'] .status-indicator-glass--success {
            border: 1px solid rgba(255, 255, 255, 0.08);
            background: linear-gradient(135deg, rgba(10, 10, 10, 0.98), rgba(18, 18, 18, 0.98));
          }

          html[data-theme='dark'] .status-indicator-glass--success::before {
            background: none;
          }

          html[data-theme='dark'] .status-indicator-glass--error {
            border: 1px solid rgba(255, 255, 255, 0.08);
            background: linear-gradient(135deg, rgba(10, 10, 10, 0.98), rgba(18, 18, 18, 0.98));
          }

          html[data-theme='dark'] .status-indicator-glass--error::before {
            background: none;
          }

          html[data-theme='dark'] .status-indicator-glass--warning {
            border: 1px solid rgba(255, 255, 255, 0.08);
            background: linear-gradient(135deg, rgba(10, 10, 10, 0.98), rgba(18, 18, 18, 0.98));
          }

          html[data-theme='dark'] .status-indicator-glass--warning::before {
            background: none;
          }

          html[data-theme='dark'] .status-indicator-glass:hover {
            box-shadow:
              0 14px 34px rgba(0, 0, 0, 0.28),
              inset 0 1px 0 rgba(255, 255, 255, 0.08);
          }

          .status-indicator-glass--loading:hover {
            border-color: rgba(96, 165, 250, 0.42);
          }

          .status-indicator-glass--success:hover {
            border-color: rgba(134, 239, 172, 0.42);
          }

          .status-indicator-glass--error:hover {
            border-color: rgba(252, 165, 165, 0.44);
          }

          .status-indicator-glass--warning:hover {
            border-color: rgba(253, 186, 116, 0.44);
          }

          .status-indicator__inner-clean {
            position: relative;
            z-index: 1;
          }

          .status-indicator__icon-clean {
            border-radius: 999px !important;
            color: var(--theme-text-secondary, #64748b);
            background: color-mix(in srgb, var(--theme-surface-muted, #f8fafc) 78%, transparent);
            border: 1px solid var(--theme-border-soft, rgba(226, 232, 240, 0.68));
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            transition:
              transform 150ms ease,
              background 150ms ease,
              border-color 150ms ease,
              color 150ms ease;
          }

          .status-indicator__icon-clean:hover {
            transform: scale(1.04);
            color: var(--theme-text-primary, #0f172a);
            background: color-mix(in srgb, var(--theme-surface-elevated, #ffffff) 86%, transparent);
          }

          html[data-theme='dark'] .status-indicator__icon-clean {
            color: rgba(255, 255, 255, 0.78);
            background: rgba(255, 255, 255, 0.03);
            border-color: rgba(255, 255, 255, 0.08);
          }

          html[data-theme='dark'] .status-indicator__icon-clean:hover {
            color: rgba(255, 255, 255, 0.92);
            background: rgba(255, 255, 255, 0.05);
          }

          .status-indicator__badge-clean {
            border-radius: 999px !important;
            color: var(--theme-text-secondary, #64748b);
            background: color-mix(in srgb, var(--theme-surface-muted, #f8fafc) 74%, transparent);
            border: 1px solid var(--theme-border-soft, rgba(226, 232, 240, 0.68));
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            font-weight: 700;
          }

          html[data-theme='dark'] .status-indicator__badge-clean {
            background: rgba(255, 255, 255, 0.04);
            border-color: rgba(255, 255, 255, 0.08);
            color: rgba(255, 255, 255, 0.86);
          }

          html[data-theme='dark'] .status-indicator__badge--loading {
            color: rgb(96, 165, 250);
            background: rgba(96, 165, 250, 0.12);
            border-color: rgba(96, 165, 250, 0.28);
          }

          html[data-theme='dark'] .status-indicator__badge--success {
            color: rgb(134, 239, 172);
            background: rgba(134, 239, 172, 0.12);
            border-color: rgba(134, 239, 172, 0.28);
          }

          html[data-theme='dark'] .status-indicator__badge--error {
            color: rgb(248, 113, 113);
            background: rgba(248, 113, 113, 0.12);
            border-color: rgba(248, 113, 113, 0.28);
          }

          html[data-theme='dark'] .status-indicator__badge--warning {
            color: rgb(251, 191, 36);
            background: rgba(251, 191, 36, 0.12);
            border-color: rgba(251, 191, 36, 0.28);
          }

          @keyframes statusIndicatorIn {
            from {
              opacity: 0;
              transform: translateY(5px) scale(0.985);
            }
            to {
              opacity: 1;
              transform: translateY(0) scale(1);
            }
          }

          @media (max-width: 520px) {
            .status-indicator-glass {
              border-radius: 18px;
            }

            .status-indicator__inner-clean {
              padding: 9px 10px !important;
              gap: 8px !important;
            }

            .status-indicator__icon-clean {
              width: 34px !important;
              height: 34px !important;
              border-radius: 999px !important;
            }

            .status-indicator__title-clean {
              font-size: 0.78rem !important;
            }

            .status-indicator__message-clean {
              font-size: 0.74rem !important;
            }

            .status-indicator__badge-clean {
              font-size: 0.58rem !important;
              padding: 2px 6px !important;
            }
          }

          @media (max-width: 360px) {
            .status-indicator__badge-clean {
              display: none !important;
            }
          }
        `}
      </style>

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
            <div className="flex flex-wrap items-center gap-1.5">
              <p
                className={`status-indicator__title-clean text-[0.82rem] font-semibold leading-tight ${theme.title}`}
              >
                {statusLabel}
              </p>

              <span
                className={`status-indicator__badge status-indicator__badge-clean ${theme.badge} px-1.5 py-0.5 text-[0.64rem]`}
              >
                {status.toUpperCase()}
              </span>
            </div>

            <p
              className={`status-indicator__message-clean mt-0.5 text-[0.78rem] leading-snug ${theme.subtitle} truncate`}
              title={message}
            >
              {message}
            </p>
          </div>
        </div>
      </div>
    </>
  );
};

export default StatusIndicator;
