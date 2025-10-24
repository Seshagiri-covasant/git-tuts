import React, { useState, useEffect } from 'react';

interface AIPreference {
  id: string;
  name: string;
  description: string;
  value: string;
  category: string;
  priority: number;
}

interface AIPreferencesDialogProps {
  isOpen: boolean;
  onClose: () => void;
  preferences: AIPreference[];
  onSave: (preferences: AIPreference[]) => void;
}

const AIPreferencesDialog: React.FC<AIPreferencesDialogProps> = ({
  isOpen,
  onClose,
  preferences,
  onSave
}) => {
  const [localPreferences, setLocalPreferences] = useState<AIPreference[]>(preferences);

  // Update local preferences when props change
  useEffect(() => {
    console.log('AIPreferencesDialog: preferences prop changed:', preferences);
    setLocalPreferences(preferences);
  }, [preferences]);

  const addPreference = () => {
    console.log('Adding new AI preference, current preferences:', localPreferences);
    const newPreference: AIPreference = {
      id: Date.now().toString(),
      name: '',
      description: '',
      value: '',
      category: 'general',
      priority: 1
    };
    const updatedPreferences = [...localPreferences, newPreference];
    console.log('Updated preferences:', updatedPreferences);
    setLocalPreferences(updatedPreferences);
  };

  const removePreference = (index: number) => {
    const updated = localPreferences.filter((_, i) => i !== index);
    setLocalPreferences(updated);
  };

  const updatePreference = (index: number, field: keyof AIPreference, value: any) => {
    const updated = [...localPreferences];
    updated[index] = { ...updated[index], [field]: value };
    setLocalPreferences(updated);
  };

  const handleSave = () => {
    onSave(localPreferences);
    onClose();
  };

  if (!isOpen) return null;

  console.log('Rendering AIPreferencesDialog with preferences:', localPreferences);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold text-gray-900">AI Preferences</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          <div className="space-y-4">
            {localPreferences.map((preference, index) => (
              <div key={preference.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-medium text-gray-900">
                    Preference {index + 1}
                  </h3>
                  <button
                    onClick={() => removePreference(index)}
                    className="text-red-600 hover:text-red-800 text-sm"
                  >
                    Remove
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Name
                    </label>
                    <input
                      type="text"
                      value={preference.name}
                      onChange={(e) => updatePreference(index, 'name', e.target.value)}
                      placeholder="e.g., Default Risk Score Column"
                      className="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Category
                    </label>
                    <select
                      value={preference.category}
                      onChange={(e) => updatePreference(index, 'category', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="general">General</option>
                      <option value="risk">Risk Management</option>
                      <option value="financial">Financial</option>
                      <option value="reporting">Reporting</option>
                      <option value="security">Security</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Value
                    </label>
                    <input
                      type="text"
                      value={preference.value}
                      onChange={(e) => updatePreference(index, 'value', e.target.value)}
                      placeholder="e.g., Overall_Tran_Risk_Score"
                      className="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Priority (1-10)
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="10"
                      value={preference.priority}
                      onChange={(e) => updatePreference(index, 'priority', parseInt(e.target.value) || 1)}
                      className="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                </div>

                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <textarea
                    value={preference.description}
                    onChange={(e) => updatePreference(index, 'description', e.target.value)}
                    placeholder="Describe what this preference controls and when it should be used..."
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              </div>
            ))}

            {localPreferences.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                <p>No AI preferences configured yet.</p>
                <p className="text-sm">Click "Add Preference" to create your first preference.</p>
              </div>
            )}
          </div>

          <div className="mt-6 flex justify-between">
            <button
              onClick={addPreference}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 flex items-center"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Add Preference
            </button>

            <div className="flex space-x-3">
              <button
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Save Preferences
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIPreferencesDialog;

