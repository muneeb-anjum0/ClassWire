import React, { useEffect, useMemo, useState } from 'react';
import { Plus, X, Save } from 'lucide-react';

interface SemesterManagerProps {
  isOpen: boolean;
  onClose: () => void;
  currentSemesters: string[];
  onSave: (semesters: string[]) => void;
}

const SemesterManager: React.FC<SemesterManagerProps> = ({
  isOpen,
  onClose,
  currentSemesters = [],
  onSave,
}) => {
  const [semesters, setSemesters] = useState<string[]>(currentSemesters);
  const [newSemester, setNewSemester] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    setSemesters(currentSemesters);
  }, [currentSemesters]);

  useEffect(() => {
    if (!isOpen) return;

    const scrollY = window.scrollY;

    const originalBodyStyle = {
      position: document.body.style.position,
      top: document.body.style.top,
      left: document.body.style.left,
      right: document.body.style.right,
      width: document.body.style.width,
      overflow: document.body.style.overflow,
    };

    document.body.style.position = 'fixed';
    document.body.style.top = `-${scrollY}px`;
    document.body.style.left = '0';
    document.body.style.right = '0';
    document.body.style.width = '100%';
    document.body.style.overflow = 'hidden';

    return () => {
      document.body.style.position = originalBodyStyle.position;
      document.body.style.top = originalBodyStyle.top;
      document.body.style.left = originalBodyStyle.left;
      document.body.style.right = originalBodyStyle.right;
      document.body.style.width = originalBodyStyle.width;
      document.body.style.overflow = originalBodyStyle.overflow;

      window.scrollTo(0, scrollY);
    };
  }, [isOpen]);

  const trimmedSemester = newSemester.trim();

  const alreadyExists = useMemo(() => {
    return semesters.some(
      (semester) => semester.toLowerCase() === trimmedSemester.toLowerCase()
    );
  }, [semesters, trimmedSemester]);

  const canAdd = trimmedSemester.length > 0 && !alreadyExists;

  const addSemester = () => {
    if (!canAdd) return;

    setSemesters((prev) => [...prev, trimmedSemester]);
    setNewSemester('');
  };

  const removeSemester = (index: number) => {
    setSemesters((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSave = async () => {
    try {
      setIsSaving(true);
      await onSave(semesters);
      onClose();
    } finally {
      setIsSaving(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addSemester();
    }

    if (e.key === 'Escape') {
      onClose();
    }
  };

  if (!isOpen) return null;

  const styles: Record<string, React.CSSProperties> = {
    overlay: {
      position: 'fixed',
      inset: 0,
      zIndex: 50,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '14px',
      background: 'rgba(0, 0, 0, 0.48)',
      backdropFilter: 'blur(8px)',
      WebkitBackdropFilter: 'blur(8px)',
      overscrollBehavior: 'contain',
      touchAction: 'none',
      animation: 'semesterOverlayIn 150ms ease-out',
    },

    modal: {
      width: '100%',
      maxWidth: '390px',
      maxHeight: 'calc(100svh - 28px)',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      borderRadius: '18px',
      border: '1px solid var(--theme-border-soft, rgba(148, 163, 184, 0.25))',
      background: 'var(--theme-surface, #ffffff)',
      color: 'var(--theme-text-primary, #0f172a)',
      boxShadow: '0 18px 55px rgba(15, 23, 42, 0.22)',
      animation: 'semesterModalIn 180ms cubic-bezier(.2,.8,.2,1)',
      touchAction: 'auto',
    },

    header: {
      display: 'flex',
      alignItems: 'flex-start',
      justifyContent: 'space-between',
      gap: '12px',
      padding: '18px 18px 12px',
      borderBottom: '1px solid var(--theme-border-soft, rgba(226, 232, 240, 0.9))',
    },

    titleBlock: {
      minWidth: 0,
    },

    eyebrow: {
      margin: '0 0 4px',
      color: 'var(--theme-accent, #2563eb)',
      fontSize: '10.5px',
      fontWeight: 800,
      letterSpacing: '0.1em',
      textTransform: 'uppercase',
    },

    title: {
      margin: 0,
      color: 'var(--theme-text-primary, #0f172a)',
      fontSize: '18px',
      lineHeight: 1.15,
      fontWeight: 850,
      letterSpacing: '-0.03em',
    },

    subtitle: {
      margin: '6px 0 0',
      color: 'var(--theme-text-muted, #64748b)',
      fontSize: '12.5px',
      lineHeight: 1.45,
    },

    closeButton: {
      width: '32px',
      height: '32px',
      flex: '0 0 auto',
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      border: '1px solid var(--theme-border-soft, rgba(226, 232, 240, 0.95))',
      borderRadius: '999px',
      background: 'var(--theme-surface-muted, #f8fafc)',
      color: 'var(--theme-text-muted, #64748b)',
      cursor: 'pointer',
      transition: 'transform 140ms ease, background 140ms ease, color 140ms ease',
    },

    body: {
      flex: 1,
      overflowY: 'auto',
      padding: '14px 18px',
      background: 'var(--theme-surface, #ffffff)',
      WebkitOverflowScrolling: 'touch',
      overscrollBehavior: 'contain',
    },

    section: {
      marginBottom: '14px',
    },

    labelRow: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '10px',
      marginBottom: '7px',
    },

    label: {
      color: 'var(--theme-text-secondary, #334155)',
      fontSize: '12.5px',
      fontWeight: 760,
    },

    countBadge: {
      minWidth: '24px',
      height: '22px',
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '0 8px',
      borderRadius: '999px',
      background: 'color-mix(in srgb, var(--theme-accent, #2563eb) 12%, transparent)',
      color: 'var(--theme-accent, #2563eb)',
      fontSize: '11.5px',
      fontWeight: 850,
    },

    inputWrap: {
      display: 'flex',
      alignItems: 'center',
      width: '100%',
      overflow: 'hidden',
      border: '1px solid var(--theme-border-soft, rgba(203, 213, 225, 0.95))',
      borderRadius: '999px',
      background: 'var(--theme-surface-muted, #f8fafc)',
      transition: 'border-color 140ms ease, box-shadow 140ms ease',
    },

    input: {
      width: '100%',
      height: '40px',
      minWidth: 0,
      outline: 'none',
      border: 'none',
      background: 'transparent',
      color: 'var(--theme-text-primary, #0f172a)',
      fontSize: '16px',
      padding: '0 12px 0 14px',
    },

    addButton: {
      width: '34px',
      height: '34px',
      flex: '0 0 34px',
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      border: 'none',
      borderRadius: '999px',
      margin: '0 4px 0 0',
      background: canAdd
        ? 'var(--theme-accent, #2563eb)'
        : 'var(--theme-surface-elevated, #e2e8f0)',
      color: canAdd ? '#ffffff' : 'var(--theme-text-muted, #94a3b8)',
      cursor: canAdd ? 'pointer' : 'not-allowed',
      transition: 'transform 140ms ease, filter 140ms ease, background 140ms ease',
    },

    hint: {
      margin: '7px 0 0',
      color: alreadyExists ? '#ef4444' : 'var(--theme-text-muted, #94a3b8)',
      fontSize: '11.5px',
      lineHeight: 1.4,
    },

    listBox: {
      overflow: 'hidden',
      border: '1px solid var(--theme-border-soft, rgba(226, 232, 240, 0.95))',
      borderRadius: '20px',
      background: 'var(--theme-surface-muted, #f8fafc)',
      padding: semesters.length > 0 ? '6px' : 0,
    },

    listScroll: {
      maxHeight: '178px',
      overflowY: 'auto',
      padding: 0,
      display: 'flex',
      flexDirection: 'column',
      gap: '6px',
      WebkitOverflowScrolling: 'touch',
      overscrollBehavior: 'contain',
    },

    emptyState: {
      padding: '22px 16px',
      textAlign: 'center',
    },

    emptyTitle: {
      margin: 0,
      color: 'var(--theme-text-primary, #334155)',
      fontSize: '13px',
      fontWeight: 850,
    },

    emptyText: {
      margin: '5px 0 0',
      color: 'var(--theme-text-muted, #94a3b8)',
      fontSize: '11.5px',
      lineHeight: 1.4,
    },

    semesterItem: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '8px',
      minHeight: '38px',
      padding: '7px 7px 7px 13px',
      borderRadius: '999px',
      border: '1px solid var(--theme-border-soft, rgba(226, 232, 240, 0.82))',
      color: 'var(--theme-text-primary, #0f172a)',
      background: 'var(--theme-surface, #ffffff)',
      boxShadow: '0 4px 12px rgba(15, 23, 42, 0.045)',
      transition: 'background 130ms ease, transform 130ms ease, box-shadow 130ms ease',
    },

    semesterText: {
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap',
      fontSize: '12.8px',
      fontWeight: 650,
    },

    removeButton: {
      width: '27px',
      height: '27px',
      flex: '0 0 auto',
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      border: 'none',
      borderRadius: '999px',
      background: 'var(--theme-surface-muted, #f8fafc)',
      color: 'var(--theme-text-muted, #64748b)',
      cursor: 'pointer',
      transition: 'background 130ms ease, color 130ms ease, transform 130ms ease',
    },

    footer: {
      display: 'flex',
      justifyContent: 'flex-end',
      padding: '12px 18px 16px',
      borderTop: '1px solid var(--theme-border-soft, rgba(226, 232, 240, 0.9))',
      background: 'var(--theme-surface-muted, #f8fafc)',
    },

    joinedButtons: {
      display: 'inline-flex',
      gap: '7px',
      padding: '4px',
      borderRadius: '999px',
      background: 'var(--theme-surface-elevated, #ffffff)',
      border: '1px solid var(--theme-border-soft, rgba(203, 213, 225, 0.95))',
      boxShadow: '0 10px 24px rgba(15, 23, 42, 0.10)',
    },

    cancelButton: {
      height: '34px',
      padding: '0 17px',
      border: 'none',
      borderRadius: '999px',
      background: 'transparent',
      color: 'var(--theme-text-secondary, #475569)',
      fontSize: '12.5px',
      fontWeight: 850,
      cursor: 'pointer',
      transition: 'background 150ms ease, color 150ms ease, transform 150ms ease',
    },

    saveButton: {
      height: '34px',
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '6px',
      padding: '0 17px',
      border: 'none',
      borderRadius: '999px',
      background: '#000000',
      color: '#ffffff',
      fontSize: '12.5px',
      fontWeight: 900,
      cursor: isSaving ? 'not-allowed' : 'pointer',
      opacity: isSaving ? 0.7 : 1,
      boxShadow: '0 8px 18px rgba(0, 0, 0, 0.24)',
      transition: 'filter 150ms ease, transform 150ms ease, box-shadow 150ms ease',
    },
  };

  return (
    <div style={styles.overlay} className="semester-overlay">
      <style>
        {`
          @keyframes semesterOverlayIn {
            from {
              opacity: 0;
            }
            to {
              opacity: 1;
            }
          }

          @keyframes semesterModalIn {
            from {
              opacity: 0;
              transform: translateY(8px) scale(0.98);
            }
            to {
              opacity: 1;
              transform: translateY(0) scale(1);
            }
          }

          .semester-input::placeholder {
            color: var(--theme-text-muted, #94a3b8);
            font-size: 13px;
          }

          .semester-input-wrap:focus-within {
            border-color: var(--theme-accent, #2563eb) !important;
            box-shadow: 0 0 0 3px color-mix(in srgb, var(--theme-accent, #2563eb) 14%, transparent) !important;
          }

          .semester-close-btn:hover {
            color: var(--theme-text-primary, #0f172a) !important;
            background: var(--theme-surface-elevated, #ffffff) !important;
            transform: translateY(-1px);
          }

          .semester-add-btn:hover:not(:disabled) {
            filter: brightness(0.94);
            transform: scale(1.04);
          }

          .semester-add-btn:active:not(:disabled) {
            transform: scale(0.94);
          }

          .semester-item:hover {
            background: var(--theme-surface-elevated, #ffffff) !important;
            transform: translateY(-1px);
            box-shadow: 0 8px 18px rgba(15, 23, 42, 0.075) !important;
          }

          .semester-remove-btn:hover {
            color: #ef4444 !important;
            background: color-mix(in srgb, #ef4444 12%, transparent) !important;
            transform: scale(1.06);
          }

          .semester-cancel-btn:hover {
            color: var(--theme-text-primary, #0f172a) !important;
            background: var(--theme-surface-muted, #f8fafc) !important;
            transform: translateY(-1px);
          }

          .semester-save-btn:hover:not(:disabled) {
            filter: brightness(1.03);
            transform: translateY(-1px);
            box-shadow:
              0 12px 24px color-mix(in srgb, var(--theme-accent, #2563eb) 32%, transparent) !important;
          }

          .semester-save-btn:active:not(:disabled),
          .semester-cancel-btn:active {
            transform: scale(0.97);
          }

          @media (max-width: 520px) {
            .semester-overlay {
              align-items: center !important;
              justify-content: center !important;
              padding: 12px !important;
            }

            .semester-modal {
              max-width: 100% !important;
              max-height: calc(100svh - 24px) !important;
              border-radius: 18px !important;
            }

            .semester-header {
              padding: 16px 16px 10px !important;
            }

            .semester-title {
              font-size: 17px !important;
            }

            .semester-subtitle {
              font-size: 12px !important;
            }

            .semester-body {
              padding: 12px 16px !important;
            }

            .semester-input {
              font-size: 16px !important;
            }

            .semester-list-scroll {
              max-height: 155px !important;
            }

            .semester-footer {
              justify-content: center !important;
              padding: 10px 16px 14px !important;
            }

            .semester-joined-buttons {
              width: auto !important;
              max-width: max-content !important;
            }

            .semester-cancel-btn,
            .semester-save-btn {
              flex: 0 0 auto !important;
              height: 34px !important;
              padding-left: 17px !important;
              padding-right: 17px !important;
              font-size: 12.5px !important;
            }
          }

          @media (max-width: 360px) {
            .semester-cancel-btn,
            .semester-save-btn {
              padding-left: 15px !important;
              padding-right: 15px !important;
            }
          }

          @media (max-height: 620px) and (max-width: 520px) {
            .semester-subtitle {
              display: none !important;
            }

            .semester-header {
              padding-bottom: 9px !important;
            }

            .semester-list-scroll {
              max-height: 120px !important;
            }
          }

          html[data-theme='dark'] .semester-save-btn {
            background: #1a1a1a !important;
            color: #ffffff !important;
            border: 1px solid #2a2a2a !important;
            box-shadow: 0 8px 18px rgba(0, 0, 0, 0.3) !important;
          }

          html[data-theme='dark'] .semester-save-btn:hover:not(:disabled) {
            background: #242424 !important;
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.4) !important;
          }
        `}
      </style>

      <div style={styles.modal} className="semester-modal">
        <div style={styles.header} className="semester-header">
          <div style={styles.titleBlock}>
            <p style={styles.eyebrow}>Semester setup</p>

            <h3 style={styles.title} className="semester-title">
              Manage semesters
            </h3>

            <p style={styles.subtitle} className="semester-subtitle">
              Choose which semesters appear in timetable filters.
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            style={styles.closeButton}
            className="semester-close-btn"
            title="Close"
            aria-label="Close semester manager"
          >
            <X size={16} />
          </button>
        </div>

        <div style={styles.body} className="semester-body">
          <div style={styles.section}>
            <div style={styles.labelRow}>
              <label htmlFor="semester-input" style={styles.label}>
                Add semester
              </label>
            </div>

            <div style={styles.inputWrap} className="semester-input-wrap">
              <input
                id="semester-input"
                type="text"
                value={newSemester}
                onChange={(e) => setNewSemester(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Example: BS (SE) - 5C"
                style={styles.input}
                className="semester-input"
              />

              <button
                type="button"
                onClick={addSemester}
                disabled={!canAdd}
                style={styles.addButton}
                className="semester-add-btn"
                title="Add semester"
                aria-label="Add semester"
              >
                <Plus size={16} />
              </button>
            </div>

            <p style={styles.hint}>
              {alreadyExists
                ? 'Already added.'
                : 'Examples: BS (SE) - 5C, MS (CS) - 1A, 7A'}
            </p>
          </div>

          <div style={{ ...styles.section, marginBottom: 0 }}>
            <div style={styles.labelRow}>
              <label style={styles.label}>Current semesters</label>
              <span style={styles.countBadge}>{semesters.length}</span>
            </div>

            <div style={styles.listBox}>
              <div style={styles.listScroll} className="semester-list-scroll">
                {semesters.length === 0 ? (
                  <div style={styles.emptyState}>
                    <p style={styles.emptyTitle}>No semesters added</p>
                    <p style={styles.emptyText}>Add one semester above to start.</p>
                  </div>
                ) : (
                  semesters.map((semester, index) => (
                    <div
                      key={`${semester}-${index}`}
                      style={styles.semesterItem}
                      className="semester-item"
                    >
                      <span style={styles.semesterText} title={semester}>
                        {semester}
                      </span>

                      <button
                        type="button"
                        onClick={() => removeSemester(index)}
                        style={styles.removeButton}
                        className="semester-remove-btn"
                        title="Remove semester"
                        aria-label={`Remove ${semester}`}
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>

        <div style={styles.footer} className="semester-footer">
          <div style={styles.joinedButtons} className="semester-joined-buttons">
            <button
              type="button"
              onClick={onClose}
              style={styles.cancelButton}
              className="semester-cancel-btn"
            >
              Cancel
            </button>

            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving}
              style={styles.saveButton}
              className="semester-save-btn"
            >
              <Save size={13} />
              {isSaving ? 'Saving' : 'Save'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SemesterManager;