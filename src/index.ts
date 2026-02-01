import { ILayoutRestorer, JupyterFrontEndPlugin } from '@jupyterlab/application';
import { ICommandPalette } from '@jupyterlab/apputils';
import { ILauncher } from '@jupyterlab/launcher';
import { INotebookTracker } from '@jupyterlab/notebook';
import { ISettingRegistry } from '@jupyterlab/settingregistry';

import mermaidMimeRendererPlugin from './mermaidMimeRenderer';
import { activateKfpPlugin } from './plugin/activate';
import { initializeSettings, syncBackendConfigFromSettings } from './api';

/**
 * Initialization data for the jupyterlab-kubeflow-pipelines extension.
 */
const plugin: JupyterFrontEndPlugin<void> = {
  id: 'jupyterlab-kubeflow-pipelines:plugin',
  description: 'JupyterLab extension to visualize Kubeflow Pipelines',
  autoStart: true,
  requires: [ISettingRegistry],
  optional: [ILauncher, ICommandPalette, ILayoutRestorer, INotebookTracker],
  activate: async (app, settingRegistry, launcher, palette, restorer, notebookTracker) => {
    void restorer;
    const settings = await settingRegistry.load(plugin.id);
    initializeSettings(settings);
    settings.changed.connect(() => {
      void syncBackendConfigFromSettings();
    });
    void syncBackendConfigFromSettings();
    activateKfpPlugin(app, launcher, palette, notebookTracker);
  }
};

export default [plugin, mermaidMimeRendererPlugin];
