import React, { useState } from 'react';
import { importPipelineFromYaml } from '../api';

type ImportPipelineDialogProps = {
  onClose: () => void;
  onOpenPipelineDetails: (pipelineId: string) => void;
};

export const ImportPipelineDialog: React.FC<ImportPipelineDialogProps> = ({
  onClose,
  onOpenPipelineDetails
}) => {
  const [pipelineName, setPipelineName] = useState('');
  const [description, setDescription] = useState('');
  const [pipelineYaml, setPipelineYaml] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<{
    pipelineId: string;
    pipelineName: string;
  } | null>(null);

  const validate = (): string | null => {
    const name = pipelineName.trim();
    if (!name) {
      return 'Pipeline name is required.';
    }
    const yaml = pipelineYaml.trim();
    if (!yaml) {
      return 'Pipeline YAML is required.';
    }
    return null;
  };

  const handleImport = async () => {
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setCreated(null);
    try {
      const res = await importPipelineFromYaml(
        pipelineName.trim(),
        pipelineYaml.trim(),
        description.trim() || undefined
      );

      const pipelineId = String(res?.pipeline_id || '');
      if (!pipelineId) {
        throw new Error(
          'Import succeeded but pipeline_id was missing in response.'
        );
      }
      setCreated({ pipelineId, pipelineName: pipelineName.trim() });
    } catch (e: any) {
      const status = e?.response?.status;
      const body = e?.response?.data;
      if (status === 409 && body?.pipeline_id) {
        setError(
          `A pipeline named "${pipelineName.trim()}" already exists. ` +
            'Use a unique name, or import as a new version (not implemented yet).'
        );
      } else {
        setError(
          body?.error ||
            body?.detail ||
            e?.message ||
            'Failed to import pipeline.'
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="jp-KfpSubmitDialog">
      <h3 style={{ margin: 0 }}>Import pipeline from YAML</h3>
      <p className="jp-KfpMessage" style={{ marginTop: 0 }}>
        Registers a pipeline (does not create a run).
      </p>

      <div className="jp-KfpFormGroup">
        <label>Pipeline name</label>
        <input
          type="text"
          value={pipelineName}
          onChange={e => {
            e.stopPropagation();
            setPipelineName(e.target.value);
          }}
          placeholder="e.g. my-pipeline"
          disabled={isSubmitting}
        />
      </div>

      <div className="jp-KfpFormGroup">
        <label>Description (optional)</label>
        <input
          type="text"
          value={description}
          onChange={e => {
            e.stopPropagation();
            setDescription(e.target.value);
          }}
          placeholder="What does this pipeline do?"
          disabled={isSubmitting}
        />
      </div>

      <div className="jp-KfpFormGroup">
        <label>Pipeline YAML</label>
        <textarea
          value={pipelineYaml}
          onChange={e => {
            e.stopPropagation();
            setPipelineYaml(e.target.value);
          }}
          placeholder="Paste your compiled KFP v2 pipeline YAML here…"
          disabled={isSubmitting}
          style={{
            minHeight: '220px',
            resize: 'vertical',
            padding: '10px 12px',
            border: '1px solid var(--jp-border-color2)',
            background: 'var(--jp-layout-color2)',
            color: 'var(--jp-ui-font-color1)',
            borderRadius: '6px',
            fontSize: '12px',
            fontFamily: 'var(--jp-code-font-family)'
          }}
        />
      </div>

      {error && (
        <div
          style={{
            fontSize: '12px',
            padding: '10px',
            borderRadius: '6px',
            lineHeight: '1.4',
            background: 'rgba(217, 48, 37, 0.08)',
            color: '#d93025',
            border: '1px solid rgba(217, 48, 37, 0.2)',
            wordBreak: 'break-word'
          }}
        >
          {error}
        </div>
      )}

      {created && (
        <div
          style={{
            fontSize: '12px',
            padding: '10px',
            borderRadius: '6px',
            lineHeight: '1.4',
            background: 'rgba(24, 128, 56, 0.08)',
            color: 'var(--jp-ui-font-color1)',
            border: '1px solid rgba(24, 128, 56, 0.2)',
            wordBreak: 'break-word'
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: '4px' }}>
            Pipeline imported
          </div>
          <div>
            Pipeline ID:{' '}
            <span style={{ fontFamily: 'var(--jp-code-font-family)' }}>
              {created.pipelineId}
            </span>
          </div>
          <div style={{ marginTop: '8px', display: 'flex', gap: '8px' }}>
            <button
              className="jp-mod-styled"
              onClick={() => onOpenPipelineDetails(created.pipelineId)}
            >
              Open details in JupyterLab tab
            </button>
          </div>
        </div>
      )}

      <div className="jp-KfpButtonGroup">
        <button
          className="jp-mod-styled jp-KfpSaveButton"
          onClick={() => void handleImport()}
          disabled={isSubmitting}
        >
          {isSubmitting ? 'Importing…' : 'Import'}
        </button>
        <button
          className="jp-mod-styled jp-KfpCancelButton"
          onClick={onClose}
          disabled={isSubmitting}
        >
          Close
        </button>
      </div>
    </div>
  );
};
