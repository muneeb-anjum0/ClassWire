import React, { useMemo, useState } from 'react';
import { Plus, Save, X } from 'lucide-react';
import { createSemesterManagerStyles, semesterManagerInlineCss } from './semesterManagerStyles';
import { useBodyScrollLock } from './useBodyScrollLock';

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

  React.useEffect(() => {
    setSemesters(currentSemesters);
  }, [currentSemesters]);

  useBodyScrollLock(isOpen);

  const trimmedSemester = newSemester.trim();
  const alreadyExists = useMemo(
    () => semesters.some((semester) => semester.toLowerCase() === trimmedSemester.toLowerCase()),
    [semesters, trimmedSemester],
  );
  const canAdd = trimmedSemester.length > 0 && !alreadyExists;
  const styles = createSemesterManagerStyles({
    alreadyExists,
    canAdd,
    hasSemesters: semesters.length > 0,
    isSaving,
  });

  const addSemester = () => {
    if (!canAdd) {
      return;
    }

    setSemesters((previous) => [...previous, trimmedSemester]);
    setNewSemester('');
  };

  const removeSemester = (index: number) => {
    setSemesters((previous) => previous.filter((_, currentIndex) => currentIndex !== index));
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

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      addSemester();
    }

    if (event.key === 'Escape') {
      onClose();
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div style={styles.overlay} className="semester-overlay">
      <style>{semesterManagerInlineCss}</style>

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
                onChange={(event) => setNewSemester(event.target.value)}
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
              {alreadyExists ? 'Already added.' : 'Examples: BS (SE) - 5C, MS (CS) - 1A, 7A'}
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
