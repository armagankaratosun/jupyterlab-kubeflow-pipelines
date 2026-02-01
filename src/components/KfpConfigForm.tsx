import React, { useState, useEffect } from 'react';
import {
  KfpConfig,
  getConfig,
  saveConfig,
  setConnectionOk,
  testConnection
} from '../api';

interface KfpConfigFormProps {
  onConfigSave?: (config: KfpConfig) => void;
  onCancel?: () => void;
  title?: string;
  description?: string;
}

/**
 * A shared form for configuring Kubeflow Pipelines settings.
 * Used in both the Sidebar and the main Dashboard tabs.
 */
export const KfpConfigForm: React.FC<KfpConfigFormProps> = ({
  onConfigSave,
  onCancel,
  title = 'Connect to Kubeflow Pipelines',
  description = 'Enter your KFP endpoint, namespace, and (optional) token to start proxying.'
}) => {
  const [endpoint, setEndpoint] = useState('');
  const [namespace, setNamespace] = useState('kubeflow');
  const [token, setToken] = useState('');
  const [hasStoredToken, setHasStoredToken] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{
    text: string;
    type: 'error' | 'success' | 'info' | null;
  }>({ text: '', type: null });
  const [connectivity, setConnectivity] = useState<{
    ok: boolean;
    detail?: string;
  } | null>(null);
  const [endpointWarning, setEndpointWarning] = useState<string | null>(null);

  const validateInputs = (): string | null => {
    const e = (endpoint || '').trim();
    const ns = (namespace || '').trim();

    if (!e) {
      return 'Endpoint URL is required.';
    }
    if (/\s/.test(e)) {
      return 'Endpoint URL must not contain spaces.';
    }

    // Basic URL validation; backend will normalize/validate too.
    let toParse = e;
    if (!toParse.includes('://')) {
      toParse = `http://${toParse}`;
    }
    try {
      const u = new URL(toParse);
      if (!u.hostname) {
        return 'Endpoint URL must include a host.';
      }
      if ((u.hostname === 'localhost' || u.hostname === '127.0.0.1') && !u.port) {
        return 'For localhost, include a port (e.g. http://localhost:8080).';
      }
    } catch {
      return 'Endpoint URL is not a valid URL.';
    }

    if (!ns) {
      return 'Namespace is required.';
    }
    if (/\s/.test(ns)) {
      return 'Namespace must not contain spaces.';
    }

    return null;
  };

  const computeEndpointWarning = (): string | null => {
    const e = (endpoint || '').trim();
    if (!e || /\s/.test(e)) {
      return null;
    }

    let toParse = e;
    if (!toParse.includes('://')) {
      toParse = `http://${toParse}`;
    }

    try {
      const u = new URL(toParse);
      const hostname = (u.hostname || '').trim();
      if (!hostname) {
        return null;
      }

      const isIp = /^\d{1,3}(\.\d{1,3}){3}$/.test(hostname) || hostname.includes(':'); // very rough IPv6 heuristic
      const isLocalhost =
        hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1';
      const hasDot = hostname.includes('.');

      if (!hasDot && !isIp && !isLocalhost) {
        return (
          `Hostname "${hostname}" looks like a bare name. ` +
          'If this is an in-cluster service name, it might be OK; otherwise use a fully qualified host (e.g. https://kfp.example.com) or an IP.'
        );
      }
    } catch {
      return null;
    }

    return null;
  };

  useEffect(() => {
    const load = async () => {
      try {
        const config = await getConfig();
        setEndpoint((config.endpoint || '').toString());
        setNamespace((config.namespace || 'kubeflow').toString() || 'kubeflow');
        setHasStoredToken(Boolean((config as any).has_token));
      } catch (e) {
        console.error('Failed to load config', e);
      }
    };
    load();

    const onChanged = () => {
      void load();
    };
    window.addEventListener('kfp-config-changed', onChanged);
    return () => {
      window.removeEventListener('kfp-config-changed', onChanged);
    };
  }, []);

  useEffect(() => {
    setEndpointWarning(computeEndpointWarning());
  }, [endpoint]);

  const handleSave = async () => {
    const validationError = validateInputs();
    if (validationError) {
      setMessage({ text: validationError, type: 'error' });
      return;
    }

    setIsSaving(true);
    setMessage({ text: 'Saving configuration...', type: 'info' });
    setConnectivity(null);
    setConnectionOk(false);

    const newConfig = { endpoint, namespace, token };
    try {
      // Save first, but don't notify the rest of the UI until we know the connection works.
      await saveConfig(newConfig, { dispatchConfigChanged: false });
      setMessage({ text: 'Saved. Testing connection...', type: 'info' });

      try {
        const res = await testConnection();
        if (res.connectivity === 'SUCCESS') {
          setConnectivity({ ok: true });
          setMessage({ text: 'Connected successfully!', type: 'success' });
          setConnectionOk(true);
          window.dispatchEvent(new CustomEvent('kfp-config-changed'));
          window.dispatchEvent(new CustomEvent('kfp-connection-ok'));
          if (onConfigSave) {
            onConfigSave({ ...newConfig, token: '' });
          }
        } else {
          const detail = res.error || 'Connection test failed.';
          setConnectivity({ ok: false, detail });
          setConnectionOk(false);
          setMessage({
            text: `Saved, but connection failed: ${detail}`,
            type: 'error'
          });
        }
      } catch (e: any) {
        const detail =
          e?.response?.data?.error || e?.message || 'Connection test failed.';
        setConnectivity({ ok: false, detail });
        setConnectionOk(false);
        setMessage({ text: `Saved, but connection failed: ${detail}`, type: 'error' });
      }
    } catch (e) {
      setMessage({
        text: 'Failed to save configuration. Check console logs.',
        type: 'error'
      });
      console.error(e);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="jp-KfpWelcomeForm">
      <div className="jp-KfpHeader">
        <span className="jp-KfpIcon"></span>
        <span>{title}</span>
      </div>

      <p className="jp-KfpMessage">{description}</p>

      <div className="jp-KfpFormGroup">
        <label>Endpoint URL</label>
        <input
          type="text"
          value={endpoint}
          onChange={(e) => {
            e.stopPropagation();
            setEndpoint(e.target.value);
          }}
          placeholder="e.g. http://localhost:8080"
          disabled={isSaving}
        />
      </div>

      {endpointWarning && (
        <div
          style={{
            fontSize: '12px',
            padding: '10px',
            borderRadius: '6px',
            lineHeight: '1.4',
            background: 'rgba(250, 173, 20, 0.12)',
            color: 'var(--jp-ui-font-color1)',
            border: '1px solid rgba(250, 173, 20, 0.35)',
            wordBreak: 'break-word'
          }}
        >
          {endpointWarning}
        </div>
      )}

      <div className="jp-KfpFormGroup">
        <label>Namespace</label>
        <input
          type="text"
          value={namespace}
          onChange={(e) => {
            e.stopPropagation();
            setNamespace(e.target.value);
          }}
          placeholder="e.g. kubeflow"
          disabled={isSaving}
        />
      </div>

      <div className="jp-KfpFormGroup">
        <label>Auth Token (optional)</label>
        <input
          type="password"
          value={token}
          onChange={(e) => {
            e.stopPropagation();
            setToken(e.target.value);
          }}
          placeholder={
            hasStoredToken
              ? '(token stored) — paste a new token to replace'
              : 'Bearer...'
          }
          disabled={isSaving}
        />
      </div>

      {connectivity && !connectivity.ok && (
        <div
          style={{
            fontSize: '12px',
            padding: '10px',
            borderRadius: '6px',
            lineHeight: '1.4',
            background: 'rgba(217, 48, 37, 0.08)',
            color: '#d93025',
            border: '1px solid rgba(217, 48, 37, 0.2)'
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: '4px' }}>
            Connection test failed
          </div>
          <div style={{ wordBreak: 'break-word' }}>{connectivity.detail}</div>
        </div>
      )}

      {message.text && (
        <div
          style={{
            fontSize: '12px',
            padding: '10px',
            borderRadius: '6px',
            lineHeight: '1.4',
            background:
              message.type === 'error'
                ? 'rgba(217, 48, 37, 0.08)'
                : message.type === 'success'
                  ? 'rgba(30, 142, 62, 0.08)'
                  : 'rgba(66, 133, 244, 0.08)',
            color:
              message.type === 'error'
                ? '#d93025'
                : message.type === 'success'
                  ? '#1e8e3e'
                  : '#1a73e8',
            border: `1px solid ${message.type === 'error' ? 'rgba(217, 48, 37, 0.2)' : message.type === 'success' ? 'rgba(30, 142, 62, 0.2)' : 'rgba(66, 133, 244, 0.2)'}`
          }}
        >
          {message.text}
        </div>
      )}

      <div className="jp-KfpButtonGroup">
        <button className="jp-KfpSaveButton" onClick={handleSave} disabled={isSaving}>
          {isSaving ? 'Connecting...' : 'Connect'}
        </button>
        {onCancel && (
          <button className="jp-KfpCancelButton" onClick={onCancel} disabled={isSaving}>
            Cancel
          </button>
        )}
      </div>
    </div>
  );
};
