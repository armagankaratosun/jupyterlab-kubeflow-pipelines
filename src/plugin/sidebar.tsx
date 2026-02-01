import React from 'react';
import type { JupyterFrontEnd } from '@jupyterlab/application';
import { ReactWidget } from '@jupyterlab/apputils';

import { KfpSidebarLauncher } from '../components/KfpSidebarLauncher';
import { OPEN_TAB_COMMAND_ID } from './commandIds';

export function addSidebar(app: JupyterFrontEnd): void {
  const { commands, shell } = app;

  const sidebarWidget = ReactWidget.create(
    <KfpSidebarLauncher
      onOpenPath={(path, label) => {
        commands.execute(OPEN_TAB_COMMAND_ID, { path, label });
      }}
    />
  );
  sidebarWidget.id = 'kfp-v2-sidebar';
  sidebarWidget.title.iconClass = 'jp-KfpIcon';
  sidebarWidget.title.caption = 'Kubeflow Pipelines';
  sidebarWidget.addClass('jp-KfpSidebarWidget');
  shell.add(sidebarWidget, 'left', { rank: 1000 });
}
