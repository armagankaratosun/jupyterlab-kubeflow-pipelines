import './base.css';
import './index.css';

// Ensure the KFP icon asset is bundled and addressable at runtime.
// JupyterLab's extension build may not rewrite CSS `url(...)` references, so we
// pass the resolved URL through a CSS variable.
import kubeflowIconUrl from './kubeflow-icon.png';

if (typeof document !== 'undefined') {
  document.documentElement.style.setProperty(
    '--jp-kfp-kubeflow-icon-url',
    `url("${kubeflowIconUrl}")`
  );
}
