import type { ICommandPalette } from '@jupyterlab/apputils';
import type { ILauncher } from '@jupyterlab/launcher';

import { KFP_SECTIONS } from '../kfpSections';
import { HOME_COMMAND_ID } from './commandIds';

export function registerLauncherItems(
  launcher: ILauncher | null,
  commandIds: { importPipelineYaml: string }
): void {
  if (!launcher) return;

  launcher.add({
    command: HOME_COMMAND_ID,
    category: 'Kubeflow Pipelines',
    rank: 0,
    args: { origin: 'launcher' }
  });

  launcher.add({
    command: commandIds.importPipelineYaml,
    category: 'Kubeflow Pipelines',
    rank: 1,
    args: { origin: 'launcher' }
  });

  KFP_SECTIONS.forEach((section, index) => {
    launcher.add({
      command: `kfp:open-${section.id}`,
      category: 'Kubeflow Pipelines',
      rank: 10 + index,
      args: { origin: 'launcher' }
    });
  });
}

export function registerPaletteItems(
  palette: ICommandPalette | null,
  commandIds: { importPipelineYaml: string }
): void {
  if (!palette) return;

  palette.addItem({ command: HOME_COMMAND_ID, category: 'Kubeflow Pipelines' });
  palette.addItem({
    command: commandIds.importPipelineYaml,
    category: 'Kubeflow Pipelines'
  });

  KFP_SECTIONS.forEach((section) => {
    palette.addItem({
      command: `kfp:open-${section.id}`,
      category: 'Kubeflow Pipelines'
    });
  });
}
