import type { LabIcon } from '@jupyterlab/ui-components';

import {
  kfpArtifactsIcon,
  kfpExecutionsIcon,
  kfpExperimentsIcon,
  kfpPipelinesIcon,
  kfpRecurringRunsIcon,
  kfpRunsIcon
} from './kfpIcons';

type KfpSection = {
  id:
    | 'pipelines'
    | 'experiments'
    | 'runs'
    | 'recurringruns'
    | 'artifacts'
    | 'executions';
  label: string;
  path: string;
  icon: LabIcon;
};

export const KFP_SECTIONS: KfpSection[] = [
  {
    id: 'pipelines',
    label: 'KFP Pipelines',
    path: '#/pipelines',
    icon: kfpPipelinesIcon
  },
  {
    id: 'experiments',
    label: 'KFP Experiments',
    path: '#/experiments',
    icon: kfpExperimentsIcon
  },
  { id: 'runs', label: 'KFP Runs', path: '#/runs', icon: kfpRunsIcon },
  {
    id: 'recurringruns',
    label: 'KFP Recurring Runs',
    path: '#/recurringruns',
    icon: kfpRecurringRunsIcon
  },
  {
    id: 'artifacts',
    label: 'KFP Artifacts',
    path: '#/artifacts',
    icon: kfpArtifactsIcon
  },
  {
    id: 'executions',
    label: 'KFP Executions',
    path: '#/executions',
    icon: kfpExecutionsIcon
  }
];
