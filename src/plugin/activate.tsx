import type { JupyterFrontEnd } from '@jupyterlab/application';
import type { ICommandPalette } from '@jupyterlab/apputils';
import type { ILauncher } from '@jupyterlab/launcher';
import type { INotebookTracker } from '@jupyterlab/notebook';

import { IMPORT_PIPELINE_YAML_COMMAND_ID } from './commandIds';
import {
  registerImportPipelineAction,
  registerSubmitPipelineAction
} from './actions';
import { registerLauncherItems, registerPaletteItems } from './launcherPalette';
import { addNotebookMessageListener } from './messages';
import { registerNavigationCommands } from './navigation';
import { addNotebookToolbarButton } from './notebook';
import { addSidebar } from './sidebar';

export function activateKfpPlugin(
  app: JupyterFrontEnd,
  launcher: ILauncher | null,
  palette: ICommandPalette | null,
  notebookTracker: INotebookTracker | null
): void {
  console.log(
    'JupyterLab extension jupyterlab-kubeflow-pipelines is activated! Version: 0.1.2'
  );

  registerNavigationCommands(app);
  registerImportPipelineAction(app);
  registerSubmitPipelineAction(app, notebookTracker);

  registerLauncherItems(launcher, {
    importPipelineYaml: IMPORT_PIPELINE_YAML_COMMAND_ID
  });
  registerPaletteItems(palette, {
    importPipelineYaml: IMPORT_PIPELINE_YAML_COMMAND_ID
  });

  addSidebar(app);
  addNotebookToolbarButton(app, notebookTracker);
  addNotebookMessageListener(app);
}
