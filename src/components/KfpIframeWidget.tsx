import React, { useState, useEffect } from 'react';
import { ReactWidget } from '@jupyterlab/apputils';
import { KfpConfig, getConfig, getConnectionOk, kfpUiProxyUrl } from '../api';
import { KfpConfigForm } from './KfpConfigForm';

interface KfpIframeProps {
  path: string;
}

/**
 * A React component that renders the KFP UI in an iframe.
 * If not configured, it shows the configuration form.
 */
const KfpIframe: React.FC<KfpIframeProps> = ({ path }) => {
  const [config, setConfig] = useState<KfpConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isConnected, setIsConnected] = useState<boolean>(getConnectionOk());

  const refreshConfig = async () => {
    try {
      const current = await getConfig();
      setIsConnected(getConnectionOk());
      setConfig(
        current && current.endpoint && current.endpoint.trim() ? current : null
      );
    } catch (e) {
      console.error('Failed to load config', e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshConfig();

    // Listen for config changes from other components (e.g. login from sidebar)
    window.addEventListener('kfp-config-changed', refreshConfig);
    window.addEventListener('kfp-connection-ok', refreshConfig);
    return () => {
      window.removeEventListener('kfp-config-changed', refreshConfig);
      window.removeEventListener('kfp-connection-ok', refreshConfig);
    };
  }, []);

  if (isLoading) {
    return <div className="jp-KfpMessage">Loading configuration...</div>;
  }

  if (!config || !config.endpoint || !isConnected) {
    return (
      <div className="jp-KfpConnectContainer">
        <KfpConfigForm
          onConfigSave={(newConfig) => {
            setConfig(newConfig);
            setIsConnected(true);
          }}
        />
      </div>
    );
  }

  // We proxy through /kfp-ui/ which is handled by KfpUIProxyHandler
  const cleanPath = path.startsWith('/') ? path.slice(1) : path;
  const proxyBase = kfpUiProxyUrl.endsWith('/') ? kfpUiProxyUrl : `${kfpUiProxyUrl}/`;
  const iframeUrl = `${proxyBase}${cleanPath}`;

  return (
    <div
      className="jp-KfpIframeContainer"
      style={{ width: '100%', height: '100%', overflow: 'hidden' }}
    >
      <iframe
        src={iframeUrl}
        title="Kubeflow Pipelines UI"
        style={{ width: '100%', height: '100%', border: 'none' }}
        sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox"
      />
    </div>
  );
};

/**
 * A JupyterLab widget that hosts the KFP UI iframe.
 */
export class KfpIframeWidget extends ReactWidget {
  static widgetIdForPath(path: string): string {
    const normalized = path || 'root';
    const safe = normalized.replace(/[^a-zA-Z0-9_-]+/g, '-').replace(/^-+|-+$/g, '');
    return `kfp-ui-${safe || 'root'}`;
  }

  constructor(
    private path: string,
    label: string
  ) {
    super();
    this.id = KfpIframeWidget.widgetIdForPath(path);
    this.title.label = label;
    this.title.closable = true;
    this.title.iconClass = 'jp-KfpIcon';
    this.addClass('jp-KfpIframeWidget');
  }

  protected render(): React.JSX.Element {
    return <KfpIframe path={this.path} />;
  }
}
