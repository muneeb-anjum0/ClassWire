import React from 'react';
import '../../styles/dashboard-quick-actions.css';
import '../../styles/dashboard-controls.css';
import '../../styles/dashboard-quick-actions-mobile.css';
import DesktopQuickActions from './quick-actions/DesktopQuickActions';
import MobileQuickActions from './quick-actions/MobileQuickActions';
import { QuickActionsPanelProps } from './quick-actions/types';

export default function QuickActionsPanel(props: QuickActionsPanelProps) {
  if (props.isMobile) {
    return <MobileQuickActions {...props} />;
  }

  return <DesktopQuickActions {...props} />;
}
