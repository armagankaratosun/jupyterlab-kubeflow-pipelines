import React, { useState, useEffect } from 'react';
import { KfpConfig, getConfig, getConnectionOk, logout } from '../api';
import { KfpConfigForm } from './KfpConfigForm';

interface KfpSidebarLauncherProps {
  onOpenPath: (path: string, label: string) => void;
}

export const KfpSidebarLauncher: React.FC<KfpSidebarLauncherProps> = ({
  onOpenPath
}) => {
  const [config, setConfig] = useState<KfpConfig | null>(null);
  const [isConfiguring, setIsConfiguring] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isConnected, setIsConnected] = useState<boolean>(getConnectionOk());

  const refreshConfig = async () => {
    try {
      const current = await getConfig();
      const connected = getConnectionOk();
      setIsConnected(connected);
      if (current && current.endpoint && current.endpoint.trim()) {
        setConfig(current);
        setIsConfiguring(!connected);
      } else {
        setConfig(null);
        setIsConfiguring(true);
      }
    } catch (e) {
      console.error('Failed to load config', e);
      setIsConfiguring(true);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshConfig();

    // Listen for config changes from other components (e.g. login from a tab)
    window.addEventListener('kfp-config-changed', refreshConfig);
    window.addEventListener('kfp-connection-ok', refreshConfig);
    return () => {
      window.removeEventListener('kfp-config-changed', refreshConfig);
      window.removeEventListener('kfp-connection-ok', refreshConfig);
    };
  }, []);

  const handleLogout = async () => {
    if (
      window.confirm('Are you sure you want to disconnect from Kubeflow Pipelines?')
    ) {
      await logout();
    }
  };

  if (isLoading) {
    return <div className="jp-KfpMessage">Loading configuration...</div>;
  }

  if (isConfiguring || !config) {
    return (
      <div className="jp-KfpSidebarContent">
        <KfpConfigForm
          onConfigSave={(newConfig) => {
            setConfig(newConfig);
            setIsConnected(true);
            setIsConfiguring(false);
          }}
          onCancel={config && isConnected ? () => setIsConfiguring(false) : undefined}
        />
      </div>
    );
  }

  const items = [
    {
      id: 'pipelines',
      label: 'Pipelines',
      path: '#/pipelines',
      icon: 'jp-PipelineIcon'
    },
    {
      id: 'experiments',
      label: 'Experiments',
      path: '#/experiments',
      icon: 'jp-ExperimentIcon'
    },
    { id: 'runs', label: 'Runs', path: '#/runs', icon: 'jp-RunIcon' },
    {
      id: 'recurringruns',
      label: 'Recurring Runs',
      path: '#/recurringruns',
      icon: 'jp-RecurringIcon'
    },
    {
      id: 'artifacts',
      label: 'Artifacts',
      path: '#/artifacts',
      icon: 'jp-ArtifactIcon'
    },
    {
      id: 'executions',
      label: 'Executions',
      path: '#/executions',
      icon: 'jp-ExecutionIcon'
    }
  ];

  return (
    <div className="jp-KfpSidebarContent">
      <div className="jp-KfpHeader">
        <span className="jp-KfpIcon"></span>
        <span>Kubeflow Pipelines</span>
      </div>
      <div className="jp-KfpLauncherList">
        {items.map((item) => (
          <div
            key={item.id}
            className="jp-KfpLauncherItem"
            onClick={() => onOpenPath(item.path, item.label)}
          >
            <span className={`jp-KfpLauncherIcon ${item.icon}`}></span>
            <span className="jp-KfpLauncherLabel">{item.label}</span>
          </div>
        ))}
      </div>

      <div className="jp-KfpSidebarFooter">
        <button className="jp-mod-styled" onClick={() => setIsConfiguring(true)}>
          Settings
        </button>
        <button className="jp-mod-styled" onClick={handleLogout}>
          Logout
        </button>
      </div>
    </div>
  );
};
