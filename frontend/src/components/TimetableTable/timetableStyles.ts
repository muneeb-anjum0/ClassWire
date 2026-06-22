export const timetableStyles = `
  @keyframes twEnter {
    from {
      opacity: 0;
      transform: translateY(8px) scale(0.99);
    }

    to {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }

  @keyframes twRowIn {
    from {
      opacity: 0;
      transform: translateY(6px);
    }

    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .tw-stage {
    width: 100%;
    color: var(--theme-text-primary, #0f172a);
    animation: twEnter 220ms cubic-bezier(.2,.8,.2,1);
  }

  .tw-mobile-view {
    display: block;
  }

  .tw-desktop-view {
    display: none;
  }

  .tw-mobile-semester {
    overflow: hidden;
    border-bottom: 2px solid var(--theme-border-soft, #171717);
    background: transparent;
  }

  .tw-mobile-semester:last-child {
    border-bottom: none;
  }

  .tw-mobile-semester-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 14px 14px 10px;
    background: var(--theme-surface-soft, #fffaf0);
  }

  .tw-section-kicker {
    margin: 0 0 4px;
    color: var(--theme-text-muted, #64748b);
    font-size: 10px;
    line-height: 1;
    font-weight: 900;
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }

  .tw-mobile-semester-head h3 {
    margin: 0;
    color: var(--theme-text-primary, #0f172a);
    font-size: 15px;
    line-height: 1.1;
    font-weight: 900;
    letter-spacing: -0.025em;
  }

  .tw-count-pill {
    min-height: 26px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 auto;
    padding: 0 10px;
    border-radius: 999px;
    border: 2px solid var(--theme-border-soft, #171717);
    background: var(--theme-surface, #ffffff);
    color: var(--theme-text-secondary, #475569);
    font-size: 11px;
    line-height: 1;
    font-weight: 850;
    white-space: nowrap;
    box-shadow: var(--theme-button-shadow, 0 4px 0 rgba(23, 23, 23, 0.18));
  }

  .tw-mobile-card-list {
    display: grid;
    grid-template-columns: 1fr;
    gap: 10px;
    padding: 10px 12px 14px;
  }

  .tw-class-card {
    position: relative;
    overflow: hidden;
    border-radius: 22px;
    border: 3px solid var(--theme-border-soft, #171717);
    background: var(--theme-surface, #ffffff);
    box-shadow: var(--theme-shadow-soft, 0 5px 0 rgba(23, 23, 23, 0.14));
    padding: 12px;
    animation: twRowIn 190ms cubic-bezier(.2,.8,.2,1) both;
    transition:
      transform 160ms ease,
      box-shadow 160ms ease,
      border-color 160ms ease,
      background 160ms ease;
  }

  .tw-class-card:hover {
    transform: translateY(-1px);
    border-color: var(--theme-border, #171717);
    box-shadow: 0 6px 0 rgba(23, 23, 23, 0.18);
  }

  .tw-class-card--cancelled {
    border-color: color-mix(in srgb, #ef4444 34%, var(--theme-border-soft, #e5e7eb));
    background: color-mix(in srgb, #ef4444 10%, var(--theme-surface, #ffffff));
  }

  .tw-card-top {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: flex-start;
    justify-content: space-between;
    gap: 10px;
    min-width: 0;
  }

  .tw-course-block {
    min-width: 0;
    flex: 1 1 auto;
    overflow: hidden;
  }

  .tw-course-code {
    display: block;
    width: fit-content;
    max-width: 100%;
    min-height: 22px;
    margin-bottom: 7px;
    padding: 5px 9px;
    border-radius: 999px;
    border: 2px solid var(--theme-border-soft, #171717);
    background: var(--theme-surface-muted, #ffe9bf);
    color: var(--theme-text-secondary, #475569);
    font-size: 10.5px;
    line-height: 1.1;
    font-weight: 850;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    box-shadow: var(--theme-button-shadow, 0 4px 0 rgba(23, 23, 23, 0.18));
  }

  .tw-course-block h4 {
    display: block;
    width: 100%;
    max-width: 100%;
    margin: 0;
    color: var(--theme-text-primary, #0f172a);
    font-size: 14px;
    line-height: 1.35;
    font-weight: 850;
    letter-spacing: -0.012em;
    white-space: normal;
    overflow: visible;
    text-overflow: unset;
    overflow-wrap: anywhere;
  }

  .tw-room-pill {
    min-height: 26px;
    max-width: 112px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 auto;
    padding: 0 10px;
    border-radius: 999px;
    border: 2px solid var(--theme-border-soft, #171717);
    background: var(--theme-surface-soft, #fffaf0);
    color: var(--theme-text-secondary, #475569);
    font-size: 11px;
    line-height: 1;
    font-weight: 850;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    box-shadow: var(--theme-button-shadow, 0 4px 0 rgba(23, 23, 23, 0.18));
  }

  .tw-room-pill--online {
    color: var(--theme-success, #16a34a);
    background: var(--theme-success-soft, rgba(22, 163, 74, 0.1));
    border-color: color-mix(in srgb, var(--theme-success, #16a34a) 30%, var(--theme-border-soft, #e5e7eb));
  }

  .tw-mobile-details {
    display: grid;
    grid-template-columns: 1fr;
    gap: 7px;
    margin-top: 12px;
  }

  .tw-detail-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    min-height: 32px;
    padding: 7px 9px;
    border-radius: 999px;
    border: 2px solid var(--theme-border-soft, #171717);
    background: var(--theme-surface-soft, #fffaf0);
  }

  .tw-detail-row--full {
    align-items: flex-start;
    border-radius: 17px;
  }

  .tw-detail-label {
    flex: 0 0 auto;
    color: var(--theme-text-muted, #64748b);
    font-size: 10px;
    line-height: 1.2;
    font-weight: 900;
    letter-spacing: 0.09em;
    text-transform: uppercase;
  }

  .tw-detail-value {
    min-width: 0;
    color: var(--theme-text-primary, #0f172a);
    font-size: 12px;
    line-height: 1.25;
    font-weight: 750;
    text-align: right;
    overflow-wrap: anywhere;
  }

  .tw-empty-state {
    display: grid;
    place-items: center;
    text-align: center;
    padding: 34px 18px;
    border-radius: 24px;
    border: 3px dashed var(--theme-border-soft, #171717);
    background: var(--theme-surface-soft, #fffaf0);
    box-shadow: var(--theme-shadow-soft, 0 5px 0 rgba(23, 23, 23, 0.14));
  }

  .tw-empty-icon {
    width: 58px;
    height: 58px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 14px;
    border-radius: 18px;
    border: 2px solid var(--theme-border-soft, #171717);
    background: var(--theme-surface-muted, #ffe9bf);
    color: var(--theme-text-muted, #64748b);
    box-shadow: var(--theme-button-shadow, 0 4px 0 rgba(23, 23, 23, 0.18));
  }

  .tw-empty-icon svg {
    width: 30px;
    height: 30px;
  }

  .tw-empty-state h3 {
    margin: 0 0 6px;
    color: var(--theme-text-primary, #0f172a);
    font-size: 16px;
    font-weight: 850;
    letter-spacing: -0.02em;
  }

  .tw-empty-state p {
    margin: 0;
    max-width: 420px;
    color: var(--theme-text-secondary, #475569);
    font-size: 13px;
    line-height: 1.5;
  }

  .timetable-cancelled-text {
    color: #ef4444;
    font-weight: 900;
  }

  @media (min-width: 768px) {
    .tw-mobile-view {
      display: none;
    }

    .tw-desktop-view {
      display: block;
      width: 100%;
      overflow-x: auto;
    }

    .tw-table-shell {
      min-width: 980px;
      overflow: hidden;
      background: transparent;
    }

    .tw-table {
      width: 100%;
      border-collapse: separate;
      border-spacing: 0;
    }

    .tw-table thead {
      position: sticky;
      top: 0;
      z-index: 2;
      background: var(--theme-surface-soft, #fffaf0);
    }

    .tw-table th {
      padding: 14px 16px;
      border-bottom: 3px solid var(--theme-border-soft, #171717);
      color: var(--theme-text-muted, #64748b);
      font-size: 11px;
      line-height: 1;
      font-weight: 900;
      letter-spacing: 0.12em;
      text-align: left;
      text-transform: uppercase;
      white-space: nowrap;
    }

    .tw-semester-row td {
      padding: 12px 16px;
      border-top: 2px solid var(--theme-border-soft, #171717);
      border-bottom: 2px solid var(--theme-border-soft, #171717);
      background: var(--theme-surface-soft, #fffaf0);
    }

    .tw-semester-title-row {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .tw-semester-name {
      color: var(--theme-text-primary, #0f172a);
      font-size: 13px;
      line-height: 1;
      font-weight: 900;
      letter-spacing: -0.01em;
    }

    .tw-table-row {
      animation: twRowIn 170ms cubic-bezier(.2,.8,.2,1) both;
      transition:
        background 140ms ease,
        box-shadow 140ms ease;
    }

    .tw-table-row td {
      padding: 13px 16px;
      border-bottom: 2px solid var(--theme-border-soft, #171717);
      background: var(--theme-surface, #ffffff);
      vertical-align: middle;
    }

    .tw-table-row:nth-child(even) td {
      background: var(--theme-surface-soft, #fffaf0);
    }

    .tw-table-row:hover td {
      background: var(--theme-surface-elevated, #fffef7);
    }

    .tw-table-row--cancelled td {
      background: color-mix(in srgb, #ef4444 7%, var(--theme-surface, #ffffff)) !important;
    }

    .tw-table-chip,
    .tw-campus-chip {
      min-height: 28px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      max-width: 240px;
      padding: 0 10px;
      border-radius: 999px;
      border: 2px solid var(--theme-border-soft, #171717);
      background: var(--theme-surface-soft, #fffaf0);
      color: var(--theme-text-secondary, #475569);
      font-size: 12px;
      line-height: 1;
      font-weight: 800;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      box-shadow: var(--theme-button-shadow, 0 4px 0 rgba(23, 23, 23, 0.18));
    }

    .tw-table-chip--online {
      color: var(--theme-success, #16a34a);
      background: var(--theme-success-soft, rgba(22, 163, 74, 0.1));
      border-color: color-mix(in srgb, var(--theme-success, #16a34a) 30%, var(--theme-border-soft, #e5e7eb));
    }

    .tw-table-chip--time {
      color: var(--theme-text-primary, #0f172a);
      background: var(--theme-surface-muted, #ffe9bf);
    }

    .tw-table-course {
      display: flex;
      flex-direction: column;
      gap: 4px;
      max-width: 480px;
    }

    .tw-table-course-title {
      display: block;
      max-width: 460px;
      color: var(--theme-text-primary, #0f172a);
      font-size: 13px;
      line-height: 1.35;
      font-weight: 850;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .tw-table-course-code {
      color: var(--theme-text-muted, #64748b);
      font-size: 11px;
      line-height: 1;
      font-weight: 800;
    }

    .tw-muted-text {
      color: var(--theme-text-secondary, #475569);
      font-size: 13px;
      line-height: 1.35;
      font-weight: 650;
      white-space: nowrap;
    }

    .tw-campus-chip {
      max-width: 280px;
      justify-content: flex-start;
    }
  }

  @media (max-width: 420px) {
    .tw-mobile-semester-head {
      padding: 13px 12px 9px;
    }

    .tw-mobile-semester-head h3 {
      font-size: 14px;
    }

    .tw-count-pill {
      min-height: 24px;
      padding: 0 8px;
      font-size: 10.5px;
    }

    .tw-mobile-card-list {
      padding: 9px 10px 12px;
      gap: 9px;
    }

    .tw-class-card {
      border-radius: 20px;
      padding: 11px;
    }

    .tw-card-top {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      align-items: start;
      gap: 8px;
    }

    .tw-course-block {
      min-width: 0;
      overflow: hidden;
    }

    .tw-course-code {
      display: block;
      width: fit-content;
      max-width: 100%;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .tw-course-block h4 {
      font-size: 13.5px;
      white-space: normal;
      overflow: visible;
      text-overflow: unset;
      overflow-wrap: anywhere;
    }

    .tw-room-pill {
      max-width: 92px;
    }

    .tw-detail-row {
      min-height: 30px;
      padding: 7px 8px;
    }

    .tw-detail-value {
      font-size: 11.5px;
    }
  }
`;
