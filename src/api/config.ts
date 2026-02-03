import type { ISettingRegistry } from '@jupyterlab/settingregistry';

import { requestAPI } from '../request';

const CONNECTION_OK_KEY = '__kfpConnectionOk';

let pluginSettings: ISettingRegistry.ISettings | null = null;
let lastBackendSynced: { endpoint: string; namespace: string } | null = null;

export const initializeSettings = (
  settings: ISettingRegistry.ISettings
): void => {
  pluginSettings = settings;
};

const getPersistedString = (key: string, fallback: string): string => {
  if (!pluginSettings) {
    return fallback;
  }
  const value = pluginSettings.get(key).composite;
  return typeof value === 'string' ? value : fallback;
};

export const getPersistedConfig = (): Pick<
  KfpConfig,
  'endpoint' | 'namespace'
> => {
  return {
    endpoint: getPersistedString('endpoint', ''),
    namespace: getPersistedString('namespace', 'kubeflow') || 'kubeflow'
  };
};

const setPersistedConfig = async (
  config: Pick<KfpConfig, 'endpoint' | 'namespace'>
): Promise<void> => {
  if (!pluginSettings) {
    return;
  }

  await Promise.all([
    pluginSettings.set('endpoint', config.endpoint ?? ''),
    pluginSettings.set('namespace', config.namespace ?? 'kubeflow')
  ]);
};

export const syncBackendConfigFromSettings = async (): Promise<void> => {
  const { endpoint, namespace } = getPersistedConfig();
  const normalized = {
    endpoint: endpoint ?? '',
    namespace: namespace ?? 'kubeflow'
  };

  if (
    lastBackendSynced &&
    lastBackendSynced.endpoint === normalized.endpoint &&
    lastBackendSynced.namespace === normalized.namespace
  ) {
    return;
  }

  try {
    await requestAPI('settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(normalized)
    });
    lastBackendSynced = normalized;
    window.dispatchEvent(new CustomEvent('kfp-config-changed'));
  } catch (e) {
    // Backend might not be reachable yet (e.g. extension not enabled); keep settings canonical.
    console.warn('Failed to sync KFP settings to backend', e);
  }
};

export const getConnectionOk = (): boolean => {
  return Boolean((window as any)[CONNECTION_OK_KEY]);
};

export const setConnectionOk = (ok: boolean): void => {
  (window as any)[CONNECTION_OK_KEY] = ok;
};

export type KfpConfig = {
  endpoint: string;
  namespace: string;
  token?: string;
  has_token?: boolean;
};

type BackendConfig = {
  endpoint?: string | null;
  namespace?: string | null;
  has_token?: boolean;
};

export const getConfig = async (): Promise<KfpConfig> => {
  const persisted = getPersistedConfig();
  let backend: BackendConfig = {};
  try {
    backend = await requestAPI<BackendConfig>('settings');
  } catch {
    backend = {};
  }

  return {
    endpoint: (persisted.endpoint || backend.endpoint || '') as string,
    namespace:
      (persisted.namespace || backend.namespace || 'kubeflow')?.toString() ??
      'kubeflow',
    has_token: Boolean(backend.has_token)
  };
};

type KfpConnectivityResult = {
  config?: { endpoint?: string; namespace?: string; has_token?: boolean };
  test_endpoint?: string;
  connectivity?: 'SUCCESS' | 'FAILED';
  latency_ms?: number;
  status_code?: number;
  body?: string;
  error?: string;
  error_type?: string;
};

export const testConnection = async (): Promise<KfpConnectivityResult> => {
  return requestAPI<KfpConnectivityResult>('debug');
};

type SaveConfigOptions = {
  dispatchConfigChanged?: boolean;
};

export const saveConfig = async (
  config: KfpConfig,
  options: SaveConfigOptions = {}
): Promise<void> => {
  const desired = {
    endpoint: (config.endpoint ?? '').toString(),
    namespace: (config.namespace ?? 'kubeflow').toString() || 'kubeflow'
  };
  const previousBackendSynced = lastBackendSynced;

  // Persist only non-sensitive values via JupyterLab user settings.
  // Token is intentionally not persisted.
  // Set this early to avoid a duplicate settings.changed → backend sync cycle.
  lastBackendSynced = desired;
  await setPersistedConfig(desired);

  const payload: { endpoint: string; namespace: string; token?: string } = {
    ...desired
  };
  if (config.token && config.token.trim()) {
    payload.token = config.token;
  }
  try {
    await requestAPI('settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
  } catch (e) {
    // Restore so a future settings.changed can retry syncing to backend.
    lastBackendSynced = previousBackendSynced;
    throw e;
  }

  setConnectionOk(false);

  if (options.dispatchConfigChanged ?? true) {
    window.dispatchEvent(new CustomEvent('kfp-config-changed'));
  }
};

export const logout = async (): Promise<void> => {
  // Clear token for this server session only (do not clear persisted endpoint/namespace).
  await requestAPI('settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token: '' })
  });

  setConnectionOk(false);
  window.dispatchEvent(new CustomEvent('kfp-config-changed'));
};
