import type { JupyterFrontEnd } from '@jupyterlab/application';

import { KFP_SECTIONS } from '../kfpSections';
import { HOME_COMMAND_ID, OPEN_TAB_COMMAND_ID } from './commandIds';
import { openOrActivateKfpTab } from './openTab';

export function registerNavigationCommands(app: JupyterFrontEnd): void {
  const { commands } = app;

  commands.addCommand(HOME_COMMAND_ID, {
    label: 'KFP Home',
    caption: 'Open Kubeflow Pipelines (home)',
    iconClass: 'jp-KfpIcon',
    execute: () => {
      openOrActivateKfpTab(app, '#/runs', 'KFP Runs');
    }
  });

  KFP_SECTIONS.forEach(section => {
    const commandId = `kfp:open-${section.id}`;
    commands.addCommand(commandId, {
      label: section.label,
      caption: `Open ${section.label} dashboard`,
      icon: section.icon,
      execute: () => {
        openOrActivateKfpTab(app, section.path, section.label);
      }
    });
  });

  // Backwards-compatible generic open-tab command
  commands.addCommand(OPEN_TAB_COMMAND_ID, {
    label: args => (args['label'] as string) || 'Kubeflow Pipelines',
    caption: 'Open a KFP UI dashboard tab',
    execute: args => {
      const path = (args['path'] as string) || '#/runs';
      const label = (args['label'] as string) || 'KFP Runs';
      openOrActivateKfpTab(app, path, label);
    }
  });
}
