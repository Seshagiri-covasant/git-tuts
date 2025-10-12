import React, { useState, useEffect } from 'react';
import { X, Key, Info, Copy } from 'lucide-react';
import Loader from '../components/Loader';

const API_BASE_URL = import.meta.env.DEV ? 'http://localhost:5000' : 'http://localhost:5000';

interface GlobalAISettingsModalProps {
  onClose: () => void;
}

interface APISettings {
  llm_name: string;
  api_key_source: 'env' | 'global' | 'local';
  has_env_key: boolean;
}

const GlobalAISettingsModal: React.FC<GlobalAISettingsModalProps> = ({ onClose }) => {
  const [settings, setSettings] = useState<APISettings>({
    llm_name: 'COHERE',
    api_key_source: 'env',
    has_env_key: true
  });
  
  // Removed eye toggle; always show masked preview in plain text
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [globalKeyMasked, setGlobalKeyMasked] = useState<string>("");
  const [globalKeyInput, setGlobalKeyInput] = useState<string>("");
  const [copying, setCopying] = useState<boolean>(false);

  // Available LLM models
  const llmModels = [
    { value: 'OPENAI', label: 'OpenAI GPT-4o' },
    { value: 'AZURE', label: 'Azure GPT-4o Mini' },
    { value: 'COHERE', label: 'Cohere Command R+' },
    { value: 'GEMINI', label: 'Google Gemini 1.5 Pro' },
    { value: 'CLAUDE', label: 'Claude 3 Opus' }
  ];

  useEffect(() => {
    // Load current settings when modal opens
    loadCurrentSettings();
  }, []);

  // Reload masked preview when LLM changes
  useEffect(() => {
    if (!loading) {
      loadCurrentSettings(settings.llm_name);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings.llm_name]);

  const loadCurrentSettings = async (llm?: string) => {
    setLoading(true);
    try {
      const query = llm ? `?llm=${encodeURIComponent(llm)}` : '';
      const response = await fetch(`${API_BASE_URL}/api/settings/ai${query}`);
      const data = await response.json();
      
      if (data.status === 'success') {
        setSettings({
          llm_name: data.settings.llm_name,
          api_key_source: data.settings.api_key_source,
          has_env_key: data.settings.has_env_key
        });
        const masked = data.settings.global_api_key_masked || '';
        setGlobalKeyMasked(masked);
        setGlobalKeyInput(masked || '');
      } else {
        console.error('Failed to load settings:', data.error);
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSettings = async () => {
    setSaving(true);
    try {
      // Build payload, sending global_api_key only when user entered a new value
      const payload: any = {
        llm_name: settings.llm_name,
        api_key_source: settings.api_key_source
      };
      if (settings.api_key_source === 'global') {
        const trimmed = (globalKeyInput || '').trim();
        if (trimmed && trimmed !== globalKeyMasked) {
          payload.global_api_key = trimmed;
        }
      }
      const response = await fetch(`${API_BASE_URL}/api/settings/ai`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      console.log('Response status:', response.status);
      console.log('Response headers:', response.headers);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response:', errorText);
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }
      
      const data = await response.json();
      console.log('API response:', data); // Debug log
      
      if (data.status === 'success') {
        onClose();
      } else {
        console.error('Failed to save settings:', data.error);
        // TODO: Show error message to user
      }
    } catch (error) {
      console.error('Failed to save settings:', error);
      // TODO: Show error message to user
    } finally {
      setSaving(false);
    }
  };

  const handleApiKeySourceChange = (source: 'env' | 'global') => {
    setSettings(prev => ({
      ...prev,
      api_key_source: source
    }));
    // Reset input to masked when switching to global; clear when switching to env
    if (source === 'global') {
      setGlobalKeyInput(globalKeyMasked || '');
    } else {
      setGlobalKeyInput('');
    }
  };

  const handleGlobalApiKeyChange = (value: string) => {
    setGlobalKeyInput(value);
  };

  const handleCopyGlobalKey = async () => {
    try {
      setCopying(true);
      const res = await fetch(`${API_BASE_URL}/api/settings/ai/global-key?llm=${encodeURIComponent(settings.llm_name)}`);
      const data = await res.json();
      const fullKey = data?.global_api_key || '';
      if (!fullKey) return;
      await navigator.clipboard.writeText(fullKey);
    } catch (_) {
      // swallow; optional UI toast can be added later
    } finally {
      setCopying(false);
    }
  };

  const handleLLMModelChange = (model: string) => {
    setSettings(prev => ({
      ...prev,
      llm_name: model
    }));
  };

  return (
    <>
      {loading && <Loader/>}
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-screen overflow-y-auto">
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold modalHead">Global AI Settings</h2>
              <p className="text-sm text-gray-600 mt-1">Configure default API keys for your AI models.</p>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>

          {/* Form Content */}
          <div className="px-6 py-4">
            <div className="space-y-4">
              {/* AI Model Selection */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  AI Model
                </label>
                <select
                  value={settings.llm_name}
                  onChange={(e) => handleLLMModelChange(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {llmModels.map(model => (
                    <option key={model.value} value={model.value}>
                      {model.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* API Key Section */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  API Key for {settings.llm_name}
                </label>
                
                <div className="relative">
                  <Key size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    value={settings.api_key_source === 'env' ? 'Using default key' : globalKeyInput}
                    onChange={(e) => handleGlobalApiKeyChange(e.target.value)}
                    disabled={settings.api_key_source === 'env'}
                    placeholder={settings.api_key_source === 'env' ? 'Using default key' : (globalKeyMasked || 'Enter your API key')}
                    className="w-full pl-10 pr-10 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:text-gray-500"
                  />
                  <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-2">
                    <button
                      type="button"
                      onClick={handleCopyGlobalKey}
                      className="text-gray-400 hover:text-gray-600"
                      disabled={settings.api_key_source === 'env' || copying}
                      title="Copy full key"
                    >
                      <Copy size={16} />
                    </button>
                  </div>
                </div>

                {/* Key status helper text */}
                <div className="mt-2 text-xs text-gray-600">
                  {settings.api_key_source === 'global'
                    ? (globalKeyMasked
                        ? 'This is GLOBAL key.'
                        : 'No global key is set. Currently using default key.')
                    : 'Using default key (.env).'}
                    
                </div>

                {/* Checkbox for .env key */}
                <div className="mt-3">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={settings.api_key_source === 'env'}
                      onChange={(e) => handleApiKeySourceChange(e.target.checked ? 'env' : 'global')}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm text-gray-700">
                      Use default key from server environment (.env)
                    </span>
                  </label>
                </div>

                {/* Info message - show only when .env key is NOT configured */}
                {!settings.has_env_key && (
                  <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-md">
                    <div className="flex items-center">
                      <Info size={16} className="text-red-600 mr-2" />
                      <span className="text-sm text-red-800">
                        An .env key is not configured on the server.
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-200 flex justify-between">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSaveSettings}
              disabled={saving || (settings.api_key_source === 'global' && !(globalKeyInput?.trim() || globalKeyMasked))}
              className="px-4 py-2 btn-primary text-white rounded-md transition-colors flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Saving...
                </>
              ) : (
                'Save Settings'
              )}
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default GlobalAISettingsModal;
