import type { JupyterFrontEnd } from '@jupyterlab/application';
import { ToolbarButton } from '@jupyterlab/apputils';
import type { INotebookTracker } from '@jupyterlab/notebook';

import { kfpPipelinesIcon } from '../kfpIcons';
import { SUBMIT_PIPELINE_COMMAND_ID } from './commandIds';

export function addNotebookToolbarButton(
  app: JupyterFrontEnd,
  notebookTracker: INotebookTracker | null
): void {
  if (!notebookTracker) {
    return;
  }

  const { commands } = app;
  notebookTracker.widgetAdded.connect((sender: any, panel: any) => {
    void sender;
    const button = new ToolbarButton({
      className: 'kfp-submit-button',
      label: 'Submit Pipeline',
      onClick: () => {
        commands.execute(SUBMIT_PIPELINE_COMMAND_ID);
      },
      tooltip: 'Submit current notebook as KFP pipeline',
      icon: kfpPipelinesIcon
    });

    panel.toolbar.insertItem(10, 'kfp-submit', button);
  });
}
