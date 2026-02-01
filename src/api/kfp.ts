import axios from 'axios';

import type { KfpConfig } from './config';
import { baseUrl, getCookie, kfpProxyUrl } from './base';

export const getExperiments = async (config: KfpConfig) => {
  const response = await axios.get(`${kfpProxyUrl}/experiments`, {
    params: { namespace: config.namespace }
  });
  return response.data;
};

export const compilePipeline = async (
  config: KfpConfig,
  sourceCode: string,
  action: 'inspect' | 'compile' = 'inspect',
  pipelineName?: string
) => {
  void config;
  const url = `${baseUrl}jupyterlab-kubeflow-pipelines/kfp/compile`;
  const xsrfToken = getCookie('_xsrf');
  const headers = {
    ...(xsrfToken ? { 'X-XSRFToken': xsrfToken } : {})
  };

  const response = await axios.post(
    url,
    {
      source_code: sourceCode,
      action,
      pipeline_name: pipelineName
    },
    { headers }
  );
  return response.data;
};

export const submitPipeline = async (
  config: KfpConfig,
  packagePath: string | undefined,
  pipelineYaml: string | undefined,
  params: any,
  runName?: string,
  experimentId?: string
) => {
  void config;
  const url = `${baseUrl}jupyterlab-kubeflow-pipelines/kfp/submit`;
  const xsrfToken = getCookie('_xsrf');
  const headers = {
    ...(xsrfToken ? { 'X-XSRFToken': xsrfToken } : {})
  };

  const response = await axios.post(
    url,
    {
      package_path: packagePath,
      pipeline_yaml: pipelineYaml,
      params,
      run_name: runName,
      experiment_id: experimentId
    },
    { headers }
  );
  return response.data;
};

export const terminateRun = async (runId: string) => {
  const url = `${baseUrl}jupyterlab-kubeflow-pipelines/runs/${runId}:terminate`;
  const xsrfToken = getCookie('_xsrf');
  const headers = {
    ...(xsrfToken ? { 'X-XSRFToken': xsrfToken } : {})
  };
  const response = await axios.post(url, {}, { headers });
  return response.data;
};

export const importPipelineFromYaml = async (
  pipelineName: string,
  pipelineYaml: string,
  description?: string
) => {
  const url = `${baseUrl}jupyterlab-kubeflow-pipelines/kfp/pipelines/import`;
  const xsrfToken = getCookie('_xsrf');
  const headers = {
    ...(xsrfToken ? { 'X-XSRFToken': xsrfToken } : {})
  };

  const response = await axios.post(
    url,
    {
      pipeline_name: pipelineName,
      pipeline_yaml: pipelineYaml,
      description: description ?? null
    },
    { headers }
  );
  return response.data;
};
