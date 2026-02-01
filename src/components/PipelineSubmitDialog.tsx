import React, { useEffect } from 'react';
import PipelinePreview from './PipelinePreview';
import {
  compilePipeline,
  getExperiments,
  kfpUiProxyUrl,
  submitPipeline,
  terminateRun
} from '../api';

export const PipelineSubmitDialog = ({
  config,
  sourceCode,
  inspectedPipelines,
  onClose,
  onOpenRunDetails
}: any) => {
  const [selectedPipeline, setSelectedPipeline] = React.useState<any>(
    inspectedPipelines[0] || {}
  );
  const [experiments, setExperiments] = React.useState<any[]>([]);
  const [selectedExperimentId, setSelectedExperimentId] = React.useState<string>('');
  const [params, setParams] = React.useState<any>({});
  const [runName, setRunName] = React.useState<string>('');
  const [submitting, setSubmitting] = React.useState(false);
  const [submittedRunId, setSubmittedRunId] = React.useState<string | null>(null);
  const [terminating, setTerminating] = React.useState(false);
  const [status, setStatus] = React.useState<string>('');
  const [error, setError] = React.useState<string>('');

  useEffect(() => {
    // Initialize default params and run name when selectedPipeline changes
    if (selectedPipeline.name) {
      const display = selectedPipeline.display_name || selectedPipeline.name;
      setRunName(`Run of ${display} - ${new Date().toLocaleString()}`);

      const defaultParams: any = {};
      if (selectedPipeline.args) {
        selectedPipeline.args.forEach((arg: any) => {
          // Use arg.default if it exists, otherwise empty string
          defaultParams[arg.name] =
            arg.default !== undefined && arg.default !== null && arg.default !== 'None'
              ? arg.default
              : '';
        });
      }
      setParams(defaultParams);
    }

    // Fetch experiments (only when config changes or on initial load)
    getExperiments(config)
      .then((data) => {
        setExperiments(data.experiments || []);
        if (data.experiments && data.experiments.length > 0) {
          setSelectedExperimentId(data.experiments[0].id);
        }
      })
      .catch(console.error);
  }, [selectedPipeline, config]); // Dependencies for this combined effect

  const handleSubmit = async () => {
    setSubmitting(true);
    setStatus('Processing...');
    setError('');
    setSubmittedRunId(null);

    try {
      setStatus('Compiling pipeline...');
      const compileRes = await compilePipeline(
        config,
        sourceCode,
        'compile',
        selectedPipeline.name
      );
      if (!compileRes.package_path) {
        throw new Error('Compilation did not return a package path.');
      }

      setStatus('Submitting run...');
      const result = await submitPipeline(
        config,
        compileRes.package_path,
        undefined,
        params,
        runName,
        selectedExperimentId
      );
      setSubmittedRunId(result.run_id);
      setStatus(`Run submitted successfully! Run ID: ${result.run_id}`);
      if (onOpenRunDetails) {
        onOpenRunDetails(result.run_id);
      }
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.message || err.message || 'Error occurred');
    } finally {
      setSubmitting(false);
    }
  };

  const handleTerminate = async () => {
    if (!submittedRunId) return;
    setError('');
    setTerminating(true);
    try {
      await terminateRun(submittedRunId);
      setStatus(`Termination requested for run ${submittedRunId}.`);
    } catch (err: any) {
      console.error(err);
      setError(
        err.response?.data?.message || err.message || 'Failed to terminate run.'
      );
    } finally {
      setTerminating(false);
    }
  };

  if (!selectedPipeline.name) {
    return <div className="jp-KfpMessage">No pipelines found in this notebook.</div>;
  }

  const openInBrowserUrl = submittedRunId
    ? `${kfpUiProxyUrl}/#/runs/details/${submittedRunId}`
    : null;

  return (
    <div className="jp-KfpSubmitDialog">
      {/* Preview Section - Always visible or dependent? Always visible is helpful */}
      <div className="jp-KfpFormGroup">
        <label>Pipeline Preview (DAG)</label>
        <PipelinePreview pipeline={selectedPipeline} />
      </div>

      <div className="jp-KfpFormGroup">
        <label>Select Pipeline</label>
        <select
          value={selectedPipeline.name}
          onChange={(e) => {
            const p = inspectedPipelines.find((p: any) => p.name === e.target.value);
            setSelectedPipeline(p);
          }}
          disabled={submitting}
        >
          {inspectedPipelines.map((p: any) => (
            <option key={p.name} value={p.name}>
              {p.display_name || p.name}
            </option>
          ))}
        </select>
      </div>

      <div className="jp-KfpFormGroup">
        <label>Run Name</label>
        <input
          type="text"
          value={runName}
          onChange={(e) => setRunName(e.target.value)}
          disabled={submitting}
        />
      </div>
      <div className="jp-KfpFormGroup">
        <label>Experiment</label>
        <select
          value={selectedExperimentId}
          onChange={(e) => setSelectedExperimentId(e.target.value)}
          disabled={submitting}
        >
          <option value="">(Default Experiment)</option>
          {experiments.map((e: any) => (
            <option key={e.experiment_id || e.id} value={e.experiment_id || e.id}>
              {e.display_name || e.name}
            </option>
          ))}
        </select>
      </div>
      <div className="jp-KfpFormGroup">
        <label>Pipeline Parameters</label>
      </div>
      {selectedPipeline.args &&
        selectedPipeline.args.map((arg: any) => (
          <div key={arg.name} style={{ marginBottom: '8px' }}>
            <label style={{ display: 'block', fontSize: '12px', marginBottom: '4px' }}>
              {arg.name} {arg.default ? `(default: ${arg.default})` : ''}
            </label>
            <input
              type="text"
              style={{
                width: '100%',
                padding: '6px',
                border: '1px solid var(--jp-border-color2)',
                borderRadius: '4px'
              }}
              value={params[arg.name] || ''}
              onChange={(e) => setParams({ ...params, [arg.name]: e.target.value })}
              disabled={submitting}
            />
          </div>
        ))}

      {error && (
        <div className="jp-KfpMessage" style={{ color: 'var(--jp-error-color1)' }}>
          {error}
        </div>
      )}
      {status && (
        <div className="jp-KfpMessage" style={{ color: 'var(--jp-success-color1)' }}>
          {status}
        </div>
      )}

      {submittedRunId && (
        <div
          className="jp-KfpButtonGroup"
          style={{ flexDirection: 'row', gap: '12px', marginTop: '16px' }}
        >
          <button
            type="button"
            className="jp-KfpCancelButton"
            onClick={() => onOpenRunDetails?.(submittedRunId)}
          >
            Open Run Details
          </button>
          {openInBrowserUrl && (
            <a
              href={openInBrowserUrl}
              target="_blank"
              rel="noreferrer"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '0 16px',
                height: '40px',
                borderRadius: '6px',
                fontWeight: 600,
                fontSize: '14px',
                textDecoration: 'none',
                color: '#1a73e8',
                border: '1px solid var(--jp-border-color2)',
                background: 'var(--jp-layout-color1)'
              }}
            >
              Open in KFP UI (New Tab)
            </a>
          )}
          <button
            type="button"
            className="jp-KfpCancelButton"
            onClick={handleTerminate}
            disabled={terminating}
            style={{ borderColor: 'rgba(217, 48, 37, 0.35)', color: '#d93025' }}
          >
            {terminating ? 'Terminating...' : 'Terminate Run'}
          </button>
        </div>
      )}

      <div
        className="jp-KfpButtonGroup"
        style={{ flexDirection: 'row', gap: '12px', marginTop: '16px' }}
      >
        <button
          type="button"
          className="jp-KfpCancelButton"
          onClick={onClose}
          disabled={submitting}
        >
          Cancel
        </button>
        <button
          className="jp-KfpSaveButton"
          onClick={handleSubmit}
          disabled={submitting}
        >
          {submitting ? 'Processing...' : 'Submit Run'}
        </button>
      </div>
    </div>
  );
};
