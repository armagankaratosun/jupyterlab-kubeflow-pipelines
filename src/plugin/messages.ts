import type { JupyterFrontEnd } from '@jupyterlab/application';
import { Dialog, showDialog } from '@jupyterlab/apputils';

import { saveConfig, terminateRun } from '../api';
import { OPEN_TAB_COMMAND_ID, SUBMIT_PIPELINE_COMMAND_ID } from './commandIds';

export function addNotebookMessageListener(app: JupyterFrontEnd): void {
  const { commands } = app;

  window.addEventListener('message', (event: MessageEvent) => {
    if (!event.data) return;

    if (event.data.type === 'kfp-open-run' && event.data.runId) {
      const path = `#/runs/details/${event.data.runId}`;
      const label = (event.data.label as string) || 'Run Details';
      commands.execute(OPEN_TAB_COMMAND_ID, { path, label });
      return;
    }

    if (event.data.type === 'kfp-open-pipeline' && event.data.pipelineId) {
      const path = `#/pipelines/details/${event.data.pipelineId}`;
      const label = (event.data.label as string) || 'Pipeline Details';
      commands.execute(OPEN_TAB_COMMAND_ID, { path, label });
      return;
    }

    if (
      event.data.type === 'kfp-set-config' &&
      event.data.endpoint &&
      event.data.namespace
    ) {
      const endpoint = event.data.endpoint as string;
      const namespace = event.data.namespace as string;

      (async () => {
        try {
          await saveConfig({ endpoint, namespace });
          await showDialog({
            title: 'KFP Settings Updated',
            body: `Updated Kubeflow Pipelines settings to endpoint=${endpoint}, namespace=${namespace}.`,
            buttons: [Dialog.okButton()]
          });
        } catch (err: any) {
          console.error(err);
          await showDialog({
            title: 'KFP Settings Update Failed',
            body: `Failed to update settings: ${err.message || String(err)}`,
            buttons: [Dialog.okButton()]
          });
        }
      })();
      return;
    }

    if (event.data.type === 'kfp-open-dialog') {
      commands.execute(SUBMIT_PIPELINE_COMMAND_ID);
      return;
    }

    if (event.data.type === 'kfp-terminate-run' && event.data.runId) {
      const runId = event.data.runId as string;
      (async () => {
        try {
          await terminateRun(runId);
          await showDialog({
            title: 'Run Terminated',
            body: `Termination requested for run ${runId}.`,
            buttons: [Dialog.okButton()]
          });
        } catch (err: any) {
          console.error(err);
          await showDialog({
            title: 'Terminate Failed',
            body: `Failed to terminate run ${runId}: ${err.message || String(err)}`,
            buttons: [Dialog.okButton()]
          });
        }
      })();
    }
  });
}
