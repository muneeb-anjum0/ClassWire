import React, { useMemo, useState } from 'react';
import { Plus, Save, X } from 'lucide-react';
import { createSemesterManagerStyles, semesterManagerInlineCss } from './semesterManagerStyles';
import { useBodyScrollLock } from './useBodyScrollLock';

interface SemesterManagerProps {
  isOpen: boolean;
  onClose: () => void;
  currentSemesters: string[];
  onSave: (semesters: string[]) => void;
  filterMode?: 'semesters' | 'subjects' | 'faculty';
  currentSubjects?: string[];
  currentFaculty?: string[];
  onSaveDiscovery?: (mode: 'semesters' | 'subjects' | 'faculty', values: string[]) => void;
}

const SemesterManager: React.FC<SemesterManagerProps> = ({
  isOpen,
  onClose,
  currentSemesters = [],
  onSave,
  filterMode = 'semesters',
  currentSubjects = [],
  currentFaculty = [],
  onSaveDiscovery,
}) => {
  const [semesters, setSemesters] = useState<string[]>(currentSemesters);
  const [subjects, setSubjects] = useState<string[]>(currentSubjects);
  const [faculty, setFaculty] = useState<string[]>(currentFaculty);
  const [mode, setMode] = useState<'semesters' | 'subjects' | 'faculty'>(filterMode);
  const [newSemester, setNewSemester] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  React.useEffect(() => {
    setSemesters(currentSemesters);
    setSubjects(currentSubjects);
    setFaculty(currentFaculty);
    setMode(filterMode);
  }, [currentSemesters, currentSubjects, currentFaculty, filterMode]);

  useBodyScrollLock(isOpen);

  const trimmedSemester = newSemester.trim();
  const activeValues = mode === 'subjects' ? subjects : mode === 'faculty' ? faculty : semesters;
  const alreadyExists = useMemo(
    () => activeValues.some((value) => value.toLowerCase() === trimmedSemester.toLowerCase()),
    [activeValues, trimmedSemester],
  );
  const canAdd = trimmedSemester.length > 0 && !alreadyExists;
  const styles = createSemesterManagerStyles({
    alreadyExists,
    canAdd,
    hasSemesters: activeValues.length > 0,
    isSaving,
  });

  const addSemester = () => {
    if (!canAdd) {
      return;
    }

    if (mode === 'subjects') setSubjects((previous) => [...previous, trimmedSemester]);
    else if (mode === 'faculty') setFaculty((previous) => [...previous, trimmedSemester]);
    else setSemesters((previous) => [...previous, trimmedSemester]);
    setNewSemester('');
  };

  const removeSemester = (index: number) => {
    if (mode === 'subjects') setSubjects((previous) => previous.filter((_, currentIndex) => currentIndex !== index));
    else if (mode === 'faculty') setFaculty((previous) => previous.filter((_, currentIndex) => currentIndex !== index));
    else setSemesters((previous) => previous.filter((_, currentIndex) => currentIndex !== index));
  };

  const handleSave = async () => {
    try {
      setIsSaving(true);
      if (onSaveDiscovery) await onSaveDiscovery(mode, activeValues);
      else await onSave(semesters);
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
            <p style={styles.eyebrow}>Discovery setup</p>
            <h3 style={styles.title} className="semester-title">
              Choose what to find
            </h3>
            <p style={styles.subtitle} className="semester-subtitle">
              Search by semester, or find every section of specific subjects.
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
          <div className="discovery-mode" role="tablist" aria-label="Timetable discovery mode">
            <button type="button" role="tab" aria-selected={mode === 'semesters'} className={mode === 'semesters' ? 'is-active' : ''} onClick={() => { setMode('semesters'); setNewSemester(''); }}>By semester</button>
            <button type="button" role="tab" aria-selected={mode === 'subjects'} className={mode === 'subjects' ? 'is-active' : ''} onClick={() => { setMode('subjects'); setNewSemester(''); }}>By subject</button>
            <button type="button" role="tab" aria-selected={mode === 'faculty'} className={mode === 'faculty' ? 'is-active' : ''} onClick={() => { setMode('faculty'); setNewSemester(''); }}>By faculty</button>
          </div>
          <div style={styles.section}>
            <div style={styles.labelRow}>
              <label htmlFor="semester-input" style={styles.label}>
                {mode === 'subjects' ? 'Add subject search' : mode === 'faculty' ? 'Add faculty search' : 'Add semester'}
              </label>
            </div>

            <div style={styles.inputWrap} className="semester-input-wrap">
              <input
                id="semester-input"
                type="text"
                value={newSemester}
                onChange={(event) => setNewSemester(event.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={mode === 'subjects' ? 'Example: SEC 3603 or Software Engineering' : mode === 'faculty' ? 'Example: Muhammad Qasim or Qasim' : 'Example: BS (SE) - 5C'}
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
              {alreadyExists ? 'Already added.' : mode === 'subjects' ? 'Partial names and codes work. Spaces, punctuation, and letter case are ignored.' : mode === 'faculty' ? 'Name fragments work. Spaces, punctuation, and letter case are ignored.' : 'Examples: BS (SE) - 5C, MS (CS) - 1A, 7A'}
            </p>
          </div>

          <div style={{ ...styles.section, marginBottom: 0 }}>
            <div style={styles.labelRow}>
              <label style={styles.label}>{mode === 'subjects' ? 'Subject filters' : mode === 'faculty' ? 'Faculty filters' : 'Current semesters'}</label>
              <span style={styles.countBadge}>{activeValues.length}</span>
            </div>

            <div style={styles.listBox}>
              <div style={styles.listScroll} className="semester-list-scroll">
                {activeValues.length === 0 ? (
                  <div style={styles.emptyState}>
                    <p style={styles.emptyTitle}>No {mode === 'subjects' ? 'subjects' : mode === 'faculty' ? 'faculty' : 'semesters'} added</p>
                    <p style={styles.emptyText}>Add one above to start.</p>
                  </div>
                ) : (
                  activeValues.map((semester, index) => (
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
