import React, { useState, useEffect } from 'react';
import { X, FileText, Save, RotateCcw, Database, Eye } from 'lucide-react';
import { updateTemplate, restartChatbot, getChatbotSchema } from '../services/api';
import { useToaster } from '../Toaster/Toaster';
import Loader from './Loader';

interface TemplateEditorProps {
  chatbotId: string;
  currentTemplate?: {
    id: number;
    name: string;
    description: string;
    content: string;
    dataset_domain?: string; // <-- add this
  };
  onClose: () => void;
  onUpdate: (template: any) => void;
}

const TemplateEditor: React.FC<TemplateEditorProps> = ({
  chatbotId,
  currentTemplate,
  onClose,
  onUpdate,
}) => {
  const [formData, setFormData] = useState({
    name: currentTemplate?.name || '',
    description: currentTemplate?.description || '',
    content: currentTemplate?.content || '',
    dataset_domain: currentTemplate?.dataset_domain || '', // <-- new field
  });
  const [includeSchema, setIncludeSchema] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [schemaPreview, setSchemaPreview] = useState<string>('');
  const [showSchemaPreview, setShowSchemaPreview] = useState(false);
  const [isLoadingSchema, setIsLoadingSchema] = useState(false);
  const [schemaLoaded, setSchemaLoaded] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const { showToast } = useToaster();

  useEffect(() => {
    // Check if current template content includes schema
    if (currentTemplate?.content && currentTemplate.content.includes('Database Schema:')) {
      setIncludeSchema(true);
    }
  }, [currentTemplate]);

  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    
    if (!formData.name.trim()) {
      newErrors.name = 'Template name is required';
    }
    if (!formData.description.trim()) {
      newErrors.description = 'Template description is required';
    }
    if (!formData.content.trim()) {
      newErrors.content = 'Template content is required';
    }
    // Dataset domain is optional, but you can uncomment to make it required:
    // if (!formData.dataset_domain.trim()) {
    //   newErrors.dataset_domain = 'Dataset domain is required';
    // }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    
    // Check if there are changes
    const hasFormChanges = 
      formData.name !== (currentTemplate?.name || '') ||
      formData.description !== (currentTemplate?.description || '') ||
      formData.content !== (currentTemplate?.content || '') ||
      formData.dataset_domain !== (currentTemplate?.dataset_domain || '');
    
    setHasChanges(hasFormChanges);
  };

  const loadSchema = async () => {
    if (schemaLoaded && schemaPreview) {
      return true; // Schema already loaded
    }
    
    setIsLoadingSchema(true);
    try {
      const response = await getChatbotSchema(chatbotId);
      setSchemaPreview(response.data.schema_summary);
      setSchemaLoaded(true);
      return true;
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || "Failed to load schema";
      showToast(errorMessage, 'error');
      return false;
    } finally {
      setIsLoadingSchema(false);
    }
  };

  const fetchSchemaPreview = async () => {
    if (schemaLoaded && schemaPreview) {
      setShowSchemaPreview(true);
      return;
    }
    
    const success = await loadSchema();
    if (success) {
      setShowSchemaPreview(true);
    }
  };

  const handleSave = async () => {
    if (!validateForm()) return;
    
    setIsLoading(true);
    try {
      const payload = {
        name: formData.name,
        description: formData.description,
        content: formData.content,
        include_schema: includeSchema,
        dataset_domain: formData.dataset_domain, // <-- new field
      };

      await updateTemplate(chatbotId, currentTemplate?.id, payload);
      await restartChatbot(chatbotId);
      
      onUpdate({
        ...currentTemplate,
        ...formData,
      });
      
      showToast('Template updated successfully', 'success');
      onClose();
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || error.message || 'Failed to update template';
      showToast(errorMessage, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {isLoading && <Loader />}
      
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-hidden">
          {/* Header */}
          <div className="px-6 py-2 border-b border-gray-200 flex items-center justify-between">
            <div className="flex items-center">
              <FileText className="w-5 h-5 mr-2 text-green-600" />
              <h2 className="text-lg font-semibold">Edit Template</h2>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>

          {/* Content */}
          <div className="px-6 py-4 overflow-y-auto max-h-[70vh]">
            <div className="space-y-4">
              {/* Template Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Template Name *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => handleInputChange('name', e.target.value)}
                  className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    errors.name ? 'border-red-300' : 'border-gray-300'
                  }`}
                  placeholder="Enter template name"
                />
                {errors.name && (
                  <p className="text-red-500 text-sm mt-1">{errors.name}</p>
                )}
              </div>

              {/* Template Description */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Template Description *
                </label>
                <input
                  type="text"
                  value={formData.description}
                  onChange={(e) => handleInputChange('description', e.target.value)}
                  className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    errors.description ? 'border-red-300' : 'border-gray-300'
                  }`}
                  placeholder="Enter template description"
                />
                {errors.description && (
                  <p className="text-red-500 text-sm mt-1">{errors.description}</p>
                )}
              </div>

              {/* Dataset Domain Field */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Dataset Domain <span className="text-gray-400">(e.g., finance, healthcare, retail)</span>
                </label>
                <input
                  type="text"
                  value={formData.dataset_domain}
                  onChange={(e) => handleInputChange('dataset_domain', e.target.value)}
                  className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    errors.dataset_domain ? 'border-red-300' : 'border-gray-300'
                  }`}
                  placeholder="Enter the domain for this template (optional)"
                />
                {errors.dataset_domain && (
                  <p className="text-red-500 text-sm mt-1">{errors.dataset_domain}</p>
                )}
              </div>

              {/* Schema Inclusion Option */}
              <div className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={includeSchema}
                      onChange={async (e) => {
                        const checked = e.target.checked;
                        setIncludeSchema(checked);
                        
                        if (checked && !schemaLoaded) {
                          // Load schema when checkbox is checked and schema not already loaded
                          await loadSchema();
                        }
                      }}
                      className="mr-2"
                    />
                    <span className="text-sm font-medium flex items-center">
                      <Database className="w-4 h-4 mr-1" />
                      Include Database Schema
                    </span>
                  </label>
                  {includeSchema && (
                    <button
                      type="button"
                      onClick={fetchSchemaPreview}
                      disabled={isLoadingSchema}
                      className={`text-sm flex items-center ${
                        isLoadingSchema 
                          ? 'text-gray-400 cursor-not-allowed' 
                          : 'text-blue-600 hover:text-blue-800'
                      }`}
                    >
                      {isLoadingSchema ? (
                        <>
                          <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full mr-1"></div>
                          Loading...
                        </>
                                             ) : (
                         <>
                           <Eye className="w-4 h-4 mr-1" />
                           {schemaLoaded ? 'Preview Schema' : 'Load Schema'}
                         </>
                       )}
                    </button>
                  )}
                </div>
                <p className="text-xs text-gray-600">
                  When enabled, the database schema will be automatically included in your template content
                </p>
              </div>

              {/* Template Content */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Template Content *
                </label>
                <textarea
                  rows={6}
                  value={formData.content}
                  onChange={(e) => handleInputChange('content', e.target.value)}
                  className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    errors.content ? 'border-red-300' : 'border-gray-300'
                  }`}
                  placeholder={includeSchema ? "Your template content will be appended after the database schema..." : "Enter your template content..."}
                />
                {errors.content && (
                  <p className="text-red-500 text-sm mt-1">{errors.content}</p>
                )}
              </div>

              {hasChanges && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                  <div className="flex items-center">
                    <RotateCcw className="w-4 h-4 text-yellow-600 mr-2" />
                    <span className="text-sm text-yellow-800">
                      Changes will restart the chatbot while preserving conversation history
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-2 border-t border-gray-200 flex justify-between">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!hasChanges || isLoading}
              className={`px-4 py-2 rounded-md transition-colors flex items-center ${
                !hasChanges || isLoading
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              }`}
            >
              <Save className="w-4 h-4 mr-2" />
              Save & Restart
            </button>
          </div>
        </div>
      </div>

      {/* Schema Preview Modal */}
      {showSchemaPreview && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[9999]">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[80vh] overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold">Database Schema Preview</h3>
              <button
                onClick={() => setShowSchemaPreview(false)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="px-6 py-4 overflow-y-auto max-h-[60vh]">
              <pre className="text-sm bg-gray-50 p-4 rounded-lg whitespace-pre-wrap">
                {schemaPreview}
              </pre>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default TemplateEditor; 