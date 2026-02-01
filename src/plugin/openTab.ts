import type { JupyterFrontEnd } from '@jupyterlab/application';

import { KfpIframeWidget } from '../components/KfpIframeWidget';

export function openOrActivateKfpTab(
  app: JupyterFrontEnd,
  path: string,
  label: string
): void {
  const { shell } = app;
  const id = KfpIframeWidget.widgetIdForPath(path);
  for (const w of shell.widgets('main')) {
    if (w.id === id) {
      shell.activateById(id);
      return;
    }
  }
  const widget = new KfpIframeWidget(path, label);
  shell.add(widget, 'main');
  shell.activateById(widget.id);
}
