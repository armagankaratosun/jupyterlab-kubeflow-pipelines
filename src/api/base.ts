import { PageConfig } from '@jupyterlab/coreutils';

export const baseUrl = PageConfig.getBaseUrl();
export const kfpProxyUrl = `${baseUrl}jupyterlab-kubeflow-pipelines/proxy`;
export const kfpUiProxyUrl = `${baseUrl}kfp-ui`;

export function getCookie(name: string): string | undefined {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop()?.split(';').shift();
  }
  return undefined;
}
