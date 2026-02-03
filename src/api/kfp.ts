import type { KfpConfig } from './config';
import { requestAPI } from '../request';

type ExperimentListResponse = {
  experiments?: Array<{ id: string; name?: string }>;
  next_page_token?: string;
};

type PipelineArg = {
  name: string;
  default: string | null;
  type: string;
};

type PipelineDescriptor = {
  name: string;
  display_name?: string;
  description?: string | null;
  args: PipelineArg[];
};

type CompileResult = {
  pipelines?: PipelineDescriptor[];
  status?: 'compiled';
  pipeline_name?: string;
  package_path?: string;
  yaml?: string;
  error?: string;
};

type SubmitResult = {
  run_id: string;
  run_name?: string;
  url?: string;
};

type ImportPipelineResult = {
  pipeline_id?: string;
  pipeline_name?: string;
  url?: string;
  error?: string;
};

const JSON_HEADERS = { 'Content-Type': 'application/json' };

export const getExperiments = async (config: KfpConfig) => {
  const query = new URLSearchParams({ namespace: config.namespace });
  return requestAPI<ExperimentListResponse>(
    `proxy/experiments?${query.toString()}`
  );
};

export const compilePipeline = async (
  _config: KfpConfig,
  sourceCode: string,
  action: 'inspect' | 'compile' = 'inspect',
  pipelineName?: string
) => {
  return requestAPI<CompileResult>('kfp/compile', {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({
      source_code: sourceCode,
      action,
      pipeline_name: pipelineName
    })
  });
};

export const submitPipeline = async (
  _config: KfpConfig,
  packagePath: string | undefined,
  pipelineYaml: string | undefined,
  params: Record<string, unknown>,
  runName?: string,
  experimentId?: string
) => {
  return requestAPI<SubmitResult>('kfp/submit', {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({
      package_path: packagePath,
      pipeline_yaml: pipelineYaml,
      params,
      run_name: runName,
      experiment_id: experimentId
    })
  });
};

export const terminateRun = async (runId: string) => {
  return requestAPI<Record<string, unknown>>(
    'runs/' + encodeURIComponent(runId) + ':terminate',
    {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify({})
    }
  );
};

export const importPipelineFromYaml = async (
  pipelineName: string,
  pipelineYaml: string,
  description?: string
) => {
  return requestAPI<ImportPipelineResult>('kfp/pipelines/import', {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({
      pipeline_name: pipelineName,
      pipeline_yaml: pipelineYaml,
      description: description ?? null
    })
  });
};
