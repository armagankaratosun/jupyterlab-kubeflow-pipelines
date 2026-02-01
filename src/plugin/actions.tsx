import React from 'react';
import type { JupyterFrontEnd } from '@jupyterlab/application';
import { Dialog, ReactWidget, showDialog } from '@jupyterlab/apputils';
import type { INotebookTracker } from '@jupyterlab/notebook';

import { ImportPipelineDialog } from '../components/ImportPipelineDialog';
import { PipelineSubmitDialog } from '../components/PipelineSubmitDialog';
import { compilePipeline, getConfig } from '../api';
import { kfpPipelinesIcon } from '../kfpIcons';
import {
  IMPORT_PIPELINE_YAML_COMMAND_ID,
  OPEN_TAB_COMMAND_ID,
  SUBMIT_PIPELINE_COMMAND_ID
} from './commandIds';

export function registerImportPipelineAction(app: JupyterFrontEnd): void {
  const { commands } = app;

  commands.addCommand(IMPORT_PIPELINE_YAML_COMMAND_ID, {
    label: 'Import Pipeline (YAML)',
    caption: 'Register a pipeline from YAML (no run)',
    icon: kfpPipelinesIcon,
    execute: async () => {
      const dialogRef: { current: Dialog<any> | null } = { current: null };
      const body = ReactWidget.create(
        <ImportPipelineDialog
          onClose={() => {
            if (dialogRef.current) {
              dialogRef.current.resolve(0);
            }
          }}
          onOpenPipelineDetails={(pipelineId: string) => {
            commands.execute(OPEN_TAB_COMMAND_ID, {
              path: `#/pipelines/details/${pipelineId}`,
              label: 'Pipeline Details'
            });
          }}
        />
      );

      const dialog = new Dialog({
        title: 'Import Pipeline',
        body,
        buttons: [Dialog.okButton({ label: 'OK' })]
      });
      dialog.addClass('jp-KfpDialogContainer');
      dialogRef.current = dialog;
      await dialog.launch();
    }
  });
}

export function registerSubmitPipelineAction(
  app: JupyterFrontEnd,
  notebookTracker: INotebookTracker | null
): void {
  const { commands } = app;

  commands.addCommand(SUBMIT_PIPELINE_COMMAND_ID, {
    label: 'Submit Pipeline to KFP',
    caption: 'Compile and submit the current notebook as a pipeline',
    icon: kfpPipelinesIcon,
    execute: async () => {
      if (!notebookTracker || !notebookTracker.currentWidget) {
        return;
      }
      const notebookPanel = notebookTracker.currentWidget;
      const notebook = notebookPanel.content;

      let sourceCode = '';
      if (notebook.model) {
        for (let i = 0; i < notebook.model.cells.length; i++) {
          const cell = notebook.model.cells.get(i);
          if (cell.type !== 'code') {
            continue;
          }

          let text = '';
          if ((cell as any).sharedModel) {
            text = (cell as any).sharedModel.source;
          } else if ((cell as any).value && (cell as any).value.text) {
            text = (cell as any).value.text;
          } else {
            const source = cell.toJSON().source;
            text = Array.isArray(source) ? source.join('') : (source as string);
          }
          sourceCode += `${text}\n\n`;
        }
      }

      if (!sourceCode.trim()) {
        await showDialog({
          title: 'Empty Notebook',
          body: 'Please add some code to your notebook before submitting.',
          buttons: [Dialog.okButton()]
        });
        return;
      }

      try {
        const config = await getConfig();
        const inspection = await compilePipeline(config, sourceCode, 'inspect');

        if (!inspection.pipelines || inspection.pipelines.length === 0) {
          await showDialog({
            title: 'No Pipelines Found',
            body: 'No functions decorated with @dsl.pipeline were found in this notebook.',
            buttons: [Dialog.okButton()]
          });
          return;
        }

        const dialogRef: { current: Dialog<any> | null } = { current: null };

        const body = ReactWidget.create(
          <PipelineSubmitDialog
            config={config}
            sourceCode={sourceCode}
            inspectedPipelines={inspection.pipelines}
            onClose={() => {
              if (dialogRef.current) {
                dialogRef.current.resolve(0);
              }
            }}
            onOpenRunDetails={(runId: string) => {
              commands.execute(OPEN_TAB_COMMAND_ID, {
                path: `#/runs/details/${runId}`,
                label: 'Run Details'
              });
            }}
          />
        );

        const dialog = new Dialog({
          title: 'Submit Pipeline Run',
          body,
          buttons: [Dialog.okButton({ label: 'OK' })]
        });
        dialog.addClass('jp-KfpDialogContainer');
        dialogRef.current = dialog;
        await dialog.launch();
      } catch (err: any) {
        console.error(err);
        await showDialog({
          title: 'Inspection Failed',
          body: `Error analyzing notebook: ${err.message || String(err)}`,
          buttons: [Dialog.okButton()]
        });
      }
    }
  });
}
