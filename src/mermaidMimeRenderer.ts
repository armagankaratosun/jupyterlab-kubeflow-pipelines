import { JupyterFrontEndPlugin } from '@jupyterlab/application';
import { IRenderMimeRegistry } from '@jupyterlab/rendermime';
import { IRenderMime } from '@jupyterlab/rendermime-interfaces';
import { Widget } from '@lumino/widgets';
import mermaid from 'mermaid';

const MIME_TYPE = 'application/vnd.jupyterlab-kubeflow-pipelines.mermaid+json';

type MermaidPayload = {
  title?: string | null;
  mermaid: string;
};

let mermaidInitialized = false;

function ensureMermaidInitialized(): void {
  if (mermaidInitialized) return;
  mermaidInitialized = true;

  mermaid.initialize({
    startOnLoad: false,
    theme: 'default',
    securityLevel: 'loose',
    flowchart: {
      htmlLabels: true,
      curve: 'basis'
    }
  });
}

class MermaidMimeRenderer extends Widget implements IRenderMime.IRenderer {
  constructor() {
    super();
    this.addClass('jp-KfpMermaidPreview');
    this.node.style.overflow = 'auto';
    this.node.style.padding = '8px';
    this.node.style.border = '1px solid var(--jp-border-color2)';
    this.node.style.borderRadius = '4px';
    this.node.style.background = 'var(--jp-layout-color1)';
  }

  async renderModel(model: IRenderMime.IMimeModel): Promise<void> {
    ensureMermaidInitialized();

    const payload = model.data[MIME_TYPE] as unknown as MermaidPayload | undefined;
    const mermaidSource = payload?.mermaid;
    const title = payload?.title ?? null;

    this.node.textContent = '';

    if (!mermaidSource || typeof mermaidSource !== 'string') {
      const pre = document.createElement('pre');
      pre.textContent = String(model.data['text/plain'] ?? '');
      this.node.appendChild(pre);
      return;
    }

    if (title) {
      const heading = document.createElement('div');
      heading.textContent = title;
      heading.style.fontWeight = '600';
      heading.style.marginBottom = '8px';
      this.node.appendChild(heading);
    }

    const container = document.createElement('div');
    container.style.width = '100%';
    this.node.appendChild(container);

    try {
      const id = `kfp-mermaid-${Date.now()}-${Math.random().toString(16).slice(2)}`;
      const { svg } = await mermaid.render(id, mermaidSource);
      container.innerHTML = svg;
    } catch (err) {
      console.error('Failed to render Mermaid DAG preview', err);
      const pre = document.createElement('pre');
      pre.textContent = mermaidSource;
      this.node.appendChild(pre);
    }
  }
}

const rendererFactory: IRenderMime.IRendererFactory = {
  safe: true,
  mimeTypes: [MIME_TYPE],
  createRenderer: () => new MermaidMimeRenderer()
};

const mermaidMimeRendererPlugin: JupyterFrontEndPlugin<void> = {
  id: 'jupyterlab-kubeflow-pipelines:mermaid-mime-renderer',
  autoStart: true,
  requires: [IRenderMimeRegistry],
  activate: (app, registry) => {
    void app;
    registry.addFactory(rendererFactory, 0);
  }
};

export default mermaidMimeRendererPlugin;
