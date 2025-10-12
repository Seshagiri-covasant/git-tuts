/*
 * EditSchema Page Component
 * 
 * FEATURE: View/Edit ER Diagram for Existing Chatbots
 * 
 * This component allows users to view and edit the semantic schema (ER diagram) 
 * for existing chatbots after they have been created. This addresses the limitation 
 * where semantic modeling was only available during chatbot creation.
 * 
 * Key Features:
 * - Load existing semantic schema from backend
 * - Full ER diagram editing capabilities (tables, columns, relationships)
 * - Real-time saving to database with proper validation
 * - Proper error handling and loading states
 * - Fixed layout for better UX (proper scrolling, back button visibility)
 * 
 * Navigation:
 * - Accessible from Chatbot Table: "Edit Schema" button
 * - Accessible from Chatbot Interface: "Edit Schema" button in header
 * - Route: /chatbot/:chatbotId/edit-schema
 * 
 * Technical Implementation:
 * - Uses SemanticSchemaEditor in edit mode (isEditMode=true)
 * - Sanitizes datetime fields to prevent Pydantic validation errors
 * - Maintains existing functionality while adding edit capabilities
 * 
 * @author AI Assistant
 * @date December 2024
 * @version 1.0.0
 */

import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Save, RefreshCw } from 'lucide-react';
import SemanticSchemaEditor from '../../components/SemanticSchemaEditor';
import { getSemanticSchema, updateSemanticSchema } from '../../services/api';
import { useToaster } from '../../Toaster/Toaster';
import Loader from '../../components/Loader';

interface EditSchemaProps {}

/**
 * EditSchema Component
 * 
 * Main component for editing semantic schemas of existing chatbots.
 * Provides a full-screen interface with fixed header and scrollable content.
 */
const EditSchema: React.FC<EditSchemaProps> = () => {
  const { chatbotId } = useParams<{ chatbotId: string }>();
  const navigate = useNavigate();
  const { showToast } = useToaster();
  
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [semanticSchema, setSemanticSchema] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (chatbotId) {
      loadSemanticSchema();
    }
  }, [chatbotId]);

  /**
   * Loads the existing semantic schema for the chatbot from the backend
   * 
   * This function retrieves the current semantic schema data that was previously
   * saved during chatbot creation or previous edit sessions.
   */
  const loadSemanticSchema = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      // Fetch semantic schema from backend API
      const response = await getSemanticSchema(chatbotId!);
      setSemanticSchema(response.data.semantic_schema);
    } catch (err: any) {
      console.error('Error loading semantic schema:', err);
      setError(err?.response?.data?.error || 'Failed to load schema');
      showToast('Failed to load schema', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Handles saving the updated schema to the backend
   * 
   * This function is called by the SemanticSchemaEditor when the user clicks
   * "Save Changes". The schema is already sanitized by the editor before being
   * passed to this function to prevent datetime validation errors.
   * 
   * @param updatedSchema - The modified semantic schema with sanitized datetime fields
   */
  const handleSave = async (updatedSchema: any) => {
    // No API call here; the editor already performed the PUT.
    setSemanticSchema(updatedSchema);
    showToast('Schema updated successfully!', 'success');
  };

  /**
   * Refreshes the schema from the database
   * 
   * This allows users to reload the latest schema data, useful if they want
   * to discard local changes or if the schema was updated elsewhere.
   */
  const handleRefreshSchema = async () => {
    try {
      setIsLoading(true);
      await loadSemanticSchema();
      showToast('Schema refreshed successfully!', 'success');
    } catch (err: any) {
      showToast('Failed to refresh schema', 'error');
    }
  };

  if (isLoading) {
    return (
      <div className="h-screen bg-gray-50 flex items-center justify-center">
        <Loader />
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md text-center">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Schema Loading Error</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <div className="space-y-3">
            <button
              onClick={loadSemanticSchema}
              className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Try Again
            </button>
            <button
              onClick={() => navigate('/chatbots')}
              className="w-full bg-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-300 transition-colors"
            >
              Back to Chatbots
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!semanticSchema) {
    return (
      <div className="h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md text-center">
          <div className="text-gray-400 text-6xl mb-4">📊</div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">No Schema Found</h2>
          <p className="text-gray-600 mb-6">This chatbot doesn't have a semantic schema configured yet.</p>
          <button
            onClick={() => navigate('/chatbots')}
            className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Back to Chatbots
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Header - Sticky within page scroll */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 sticky top-0 z-20">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => navigate('/chatbots')}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </button>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Edit Schema</h1>
              <p className="text-sm text-gray-600">
                Modify semantic modeling for chatbot: {semanticSchema.display_name || semanticSchema.name}
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            <button
              onClick={handleRefreshSchema}
              disabled={isLoading}
              className="flex items-center px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button
              disabled={isSaving}
              className="flex items-center px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              <Save className="w-4 h-4 mr-2" />
              {isSaving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>

      {/* Schema Editor - Content */}
      <div className="flex-1">
        <SemanticSchemaEditor
          chatbotId={chatbotId!}
          onSave={handleSave}
          onConfirm={() => {}} // Not needed for edit mode
          initialSchema={semanticSchema}
          isEditMode={true}
        />
      </div>
    </div>
  );
};

export default EditSchema;
