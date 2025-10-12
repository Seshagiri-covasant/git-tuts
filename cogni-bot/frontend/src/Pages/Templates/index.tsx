import React, { useState, useEffect } from 'react';
import { Plus, Search, Filter, Edit2, Eye, Trash2, AlertCircle, FileText } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { getTemplates, createGlobalTemplate, updateGlobalTemplate, deleteGlobalTemplate, getChatbots } from '../../services/api';
import { useToaster } from '../../Toaster/Toaster';
import { Template } from '../../types';

const Templates: React.FC = () => {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [filteredTemplates, setFilteredTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [visibilityFilter, setVisibilityFilter] = useState('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    content: '',
    visibility: 'private',
    shared_with: [] as string[],
    dataset_domain: '', // <-- new field
  });
  const [chatbots, setChatbots] = useState<any[]>([]);
  const [chatbotSearchTerm, setChatbotSearchTerm] = useState('');
  
  const { showToast } = useToaster();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    fetchTemplates();
    fetchChatbots();
  }, []);

  // Listen for location state changes (when header buttons are clicked)
  useEffect(() => {
    if (location.state?.refresh) {
      fetchTemplates();
      fetchChatbots();
    }
  }, [location.state]);

  useEffect(() => {
    filterTemplates();
  }, [templates, searchTerm, visibilityFilter]);

  const fetchTemplates = async () => {
    try {
      setLoading(true);
      const response = await getTemplates();
      setTemplates(response.data);
    } catch (error) {
      showToast('Failed to fetch templates', 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchChatbots = async () => {
    try {
      const response = await getChatbots();
      setChatbots(response.data || []);
    } catch (error) {
      console.error('Failed to fetch chatbots:', error);
      showToast('Failed to fetch chatbots', 'error');
    }
  };

  const filterTemplates = () => {
    let filtered = templates;

    // Apply search filter
    if (searchTerm) {
      filtered = filtered.filter(template => 
        template.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        template.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (template.dataset_domain || '').toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Apply visibility filter
    if (visibilityFilter !== 'all') {
      filtered = filtered.filter(template => template.visibility === visibilityFilter);
    }

    setFilteredTemplates(filtered);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createGlobalTemplate(formData);
      showToast('Template created successfully', 'success');
      setShowCreateModal(false);
      resetForm();
      fetchTemplates();
    } catch (error: any) {
      showToast(error.response?.data?.error || 'Failed to create template', 'error');
    }
  };

  const handleEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTemplate) return;
    
    try {
      await updateGlobalTemplate(selectedTemplate.id, formData);
      showToast('Template updated successfully', 'success');
      setShowEditModal(false);
      resetForm();
      fetchTemplates();
    } catch (error: any) {
      showToast(error.response?.data?.error || 'Failed to update template', 'error');
    }
  };

  const handleDelete = async () => {
    if (!selectedTemplate) return;
    
    try {
      await deleteGlobalTemplate(selectedTemplate.id);
      showToast('Template deleted successfully', 'success');
      setShowDeleteModal(false);
      setSelectedTemplate(null);
      fetchTemplates();
    } catch (error: any) {
      showToast(error.response?.data?.error || 'Failed to delete template', 'error');
    }
  };

  const openCreateModal = () => {
    resetForm();
    setShowCreateModal(true);
  };

  const openEditModal = (template: Template) => {
    setSelectedTemplate(template);
    setFormData({
      name: template.name,
      description: template.description,
      content: template.content,
      visibility: template.visibility,
      shared_with: template.shared_with || [],
      dataset_domain: template.dataset_domain || '', // <-- new field
    });
    setShowEditModal(true);
  };

  const openDetailModal = (template: Template) => {
    setSelectedTemplate(template);
    setShowDetailModal(true);
  };

  const openDeleteModal = (template: Template) => {
    setSelectedTemplate(template);
    setShowDeleteModal(true);
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      content: '',
      visibility: 'private',
      shared_with: [],
      dataset_domain: '', // <-- new field
    });
    setSelectedTemplate(null);
    setChatbotSearchTerm('');
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const getVisibilityBadge = (visibility: string) => {
    const colors = {
      public: 'bg-green-100 text-green-800',
      private: 'bg-gray-100 text-gray-800',
      shared: 'bg-blue-100 text-blue-800'
    };
    return colors[visibility as keyof typeof colors] || 'bg-gray-100 text-gray-800';
  };

  const getFilteredChatbots = () => {
    if (!chatbotSearchTerm) return chatbots;
    return chatbots.filter(chatbot => 
      chatbot.name.toLowerCase().includes(chatbotSearchTerm.toLowerCase()) ||
      chatbot.chatbot_id.toLowerCase().includes(chatbotSearchTerm.toLowerCase())
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-white dark:bg-gray-900">
      {/* Fixed Static Header */}
      <div className="h-[90px] bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm z-20 flex-shrink-0 sticky top-0">
        <div className="h-full px-8 py-6 flex items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Template Hub</h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">Manage your conversation templates</p>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 bg-gray-50 dark:bg-gray-900 overflow-hidden">
        <div className="h-full overflow-y-auto">
          <div className="p-8">
                    {/* Search, Filter, and New Template Button */}
          <div className="flex flex-col sm:flex-row gap-4 mb-8">
            <div className="flex-1 relative">
              <Search className="w-5 h-5 absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search Templates..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-800 shadow-sm text-sm"
              />
            </div>
            <div className="flex items-center gap-3">
              <Filter className="w-5 h-5 text-gray-400" />
              <select
                value={visibilityFilter}
                onChange={(e) => setVisibilityFilter(e.target.value)}
                className="px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-800 min-w-[160px] shadow-sm text-sm"
              >
                <option value="all">All Visibility</option>
                <option value="public">Public</option>
                <option value="private">Private</option>
                <option value="shared">Shared</option>
              </select>
            </div>
            <button
              onClick={openCreateModal}
              className="flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-all duration-200 font-medium whitespace-nowrap shadow-md hover:shadow-lg"
            >
              <Plus className="w-5 h-5 mr-2" />
              New Template
            </button>
          </div>

                {/* Templates Table */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden border border-gray-200 dark:border-gray-700">
            <div className="overflow-x-auto">
              <table className="w-full table-auto">
                <thead className="bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
                  <tr>
                    <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                      Template Name
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                      Description
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                      Owner
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                      Visibility
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                      Dataset Domain
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                      Created
                    </th>
                    <th className="px-6 py-4 text-center text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {filteredTemplates.map((template, index) => (
                    <tr
                      key={template.id}
                      className={`hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-all duration-200 ${
                        index % 2 === 0 ? 'bg-white dark:bg-gray-800' : 'bg-gray-50/30 dark:bg-gray-700/30'
                      }`}
                      onClick={() => openDetailModal(template)}
                    >
                      <td className="px-6 py-4">
                        <div className="text-sm font-semibold text-gray-900 dark:text-white">
                          {template.name}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-600 dark:text-gray-300 max-w-md truncate">
                          {template.description}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-600 dark:text-gray-300">
                          {template.owner}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getVisibilityBadge(template.visibility)}`}>
                          {template.visibility}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-200">
                        {template.dataset_domain || '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-600 dark:text-gray-300">
                          {formatDate(template.created_at)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <div className="flex items-center justify-center space-x-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              openDetailModal(template);
                            }}
                            className="p-2 text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-all duration-200"
                            title="View details"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              openEditModal(template);
                            }}
                            className="p-2 text-green-600 hover:text-green-800 dark:text-green-400 dark:hover:text-green-300 hover:bg-green-50 dark:hover:bg-green-900/20 rounded-lg transition-all duration-200"
                            title="Edit"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              openDeleteModal(template);
                            }}
                            className="p-2 text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-all duration-200"
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>
                    
            {filteredTemplates.length === 0 && (
              <div className="text-center py-16 bg-gray-50 dark:bg-gray-800/50">
                <div className="max-w-sm mx-auto">
                  <FileText className="w-16 h-16 text-gray-400 dark:text-gray-500 mx-auto mb-4" />
                  <div className="text-lg text-gray-600 dark:text-gray-400 font-medium mb-2">
                    No templates found
                  </div>
                  <p className="text-sm text-gray-500 dark:text-gray-500 mb-6">
                    Create your first template to get started with conversation management
                  </p>
                  <button
                    onClick={openCreateModal}
                    className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Create Template
                  </button>
                </div>
              </div>
            )}
      </div>
          </div>
        </div>
      </div>

      {/* Create/Edit Modal */}
      {(showCreateModal || showEditModal) && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">
                {showCreateModal ? 'Create New Template' : 'Edit Template'}
              </h2>
              
              <form onSubmit={showCreateModal ? handleCreate : handleEdit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Template Name *
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Description *
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    rows={3}
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Content *
                  </label>
                  <textarea
                    value={formData.content}
                    onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    rows={8}
                    placeholder="Write your template instructions in plain English. Example: 'You are a helpful SQL assistant that explains queries in simple terms.'"
                    required
                  />
                  <p className="text-sm text-gray-500 mt-1">
                    Write your template in plain English. The system will automatically handle adding the user's question at the end.
                  </p>
                </div>

                {/* Dataset Domain Field */}
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Dataset Domain <span className="text-gray-400">(e.g., finance, healthcare, retail)</span>
                  </label>
                  <input
                    type="text"
                    value={formData.dataset_domain}
                    onChange={(e) => setFormData({ ...formData, dataset_domain: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Enter the domain for this template (optional)"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Owner
                    </label>
                    <input
                      type="text"
                      value="admin"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
                      disabled
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Visibility
                    </label>
                    <select
                      value={formData.visibility}
                      onChange={(e) => setFormData({ ...formData, visibility: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="public">Public</option>
                      <option value="private">Private</option>
                      <option value="shared">Shared</option>
                    </select>
                  </div>
                </div>

                {formData.visibility === 'shared' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Share with Chatbots
                    </label>
                    <p className="text-sm text-gray-500 mb-3">
                      Select which chatbots should have access to this template
                    </p>
                    
                    {/* Search input for chatbots */}
                    <div className="relative mb-3">
                      <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                      <input
                        type="text"
                        placeholder="Search chatbots by name or ID..."
                        value={chatbotSearchTerm}
                        onChange={(e) => setChatbotSearchTerm(e.target.value)}
                        className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                      />
                    </div>

                    {/* Selected chatbots display */}
                    {formData.shared_with.length > 0 && (
                      <div className="mb-3">
                        <div className="text-sm font-medium text-gray-700 mb-2">Selected Chatbots ({formData.shared_with.length}):</div>
                        <div className="flex flex-wrap gap-2">
                          {formData.shared_with.map((chatbotId) => {
                            const chatbot = chatbots.find(c => c.chatbot_id === chatbotId);
                            return (
                              <span
                                key={chatbotId}
                                className="inline-flex items-center px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded-full"
                              >
                                {chatbot?.name || chatbotId}
                                <button
                                  type="button"
                                  onClick={() => {
                                    setFormData({
                                      ...formData,
                                      shared_with: formData.shared_with.filter(id => id !== chatbotId)
                                    });
                                  }}
                                  className="ml-2 text-blue-600 hover:text-blue-800"
                                >
                                  ×
                                </button>
                              </span>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Chatbot selection list */}
                    <div className="max-h-40 overflow-y-auto border border-gray-300 rounded-lg">
                      {chatbots.length === 0 ? (
                        <div className="p-4 text-center text-gray-500 text-sm">
                          <div className="mb-2">No chatbots available yet</div>
                          <div className="text-xs text-gray-400">Create some chatbots first to share templates with them</div>
                        </div>
                      ) : getFilteredChatbots().length > 0 ? (
                        getFilteredChatbots().map((chatbot) => (
                          <label 
                            key={chatbot.chatbot_id} 
                            className="flex items-center space-x-3 p-3 hover:bg-gray-50 cursor-pointer border-b border-gray-100 last:border-b-0"
                          >
                            <input
                              type="checkbox"
                              checked={formData.shared_with.includes(chatbot.chatbot_id)}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setFormData({
                                    ...formData,
                                    shared_with: [...formData.shared_with, chatbot.chatbot_id]
                                  });
                                } else {
                                  setFormData({
                                    ...formData,
                                    shared_with: formData.shared_with.filter(id => id !== chatbot.chatbot_id)
                                  });
                                }
                              }}
                              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                            />
                            <div className="flex-1">
                              <div className="text-sm font-medium text-gray-900">{chatbot.name}</div>
                              <div className="text-xs text-gray-500">ID: {chatbot.chatbot_id}</div>
                              <div className="text-xs text-gray-500">Status: {chatbot.status}</div>
                            </div>
                          </label>
                        ))
                      ) : (
                        <div className="p-4 text-center text-gray-500 text-sm">
                          No chatbots found matching "{chatbotSearchTerm}"
                        </div>
                      )}
                    </div>

                  </div>
                )}

                <div className="flex justify-end space-x-3 pt-4">
                  <button
                    type="button"
                    onClick={() => {
                      setShowCreateModal(false);
                      setShowEditModal(false);
                      resetForm();
                    }}
                    className="px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    {showCreateModal ? 'Create Template' : 'Update Template'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Detail Modal */}
      {showDetailModal && selectedTemplate && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-start mb-6">
                <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                  Template Details
                </h2>
                <button
                  onClick={() => setShowDetailModal(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ×
                </button>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Name
                  </label>
                  <p className="text-gray-900 dark:text-white">{selectedTemplate.name}</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Description
                  </label>
                  <p className="text-gray-900 dark:text-white">{selectedTemplate.description}</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Content
                  </label>
                  <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
                    <pre className="text-sm text-gray-900 dark:text-white whitespace-pre-wrap">
                      {selectedTemplate.content}
                    </pre>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Owner
                    </label>
                    <p className="text-gray-900 dark:text-white">{selectedTemplate.owner}</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Visibility
                    </label>
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getVisibilityBadge(selectedTemplate.visibility)}`}>
                      {selectedTemplate.visibility}
                    </span>
                  </div>
                </div>

                {selectedTemplate.dataset_domain && (
                  <div className="mb-2">
                    <span className="font-semibold text-gray-700 dark:text-gray-300">Dataset Domain: </span>
                    <span className="text-gray-900 dark:text-gray-100">{selectedTemplate.dataset_domain}</span>
                  </div>
                )}

                {selectedTemplate.visibility === 'shared' && selectedTemplate.shared_with && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Shared With
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {selectedTemplate.shared_with.map((chatbotId) => {
                        const chatbot = chatbots.find(c => c.id === chatbotId);
                        return (
                          <span key={chatbotId} className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">
                            {chatbot?.name || chatbotId}
                          </span>
                        );
                      })}
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Created
                    </label>
                    <p className="text-gray-900 dark:text-white">{formatDate(selectedTemplate.created_at)}</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Updated
                    </label>
                    <p className="text-gray-900 dark:text-white">{formatDate(selectedTemplate.updated_at)}</p>
                  </div>
                </div>
              </div>

              <div className="flex justify-end space-x-3 pt-6">
                <button
                  onClick={() => setShowDetailModal(false)}
                  className="px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Close
                </button>
                <button
                  onClick={() => {
                    setShowDetailModal(false);
                    openEditModal(selectedTemplate);
                  }}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Edit Template
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Modal */}
      {showDeleteModal && selectedTemplate && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md mx-4">
            <div className="p-6">
              <div className="flex items-center mb-4">
                <div className="flex-shrink-0">
                  <AlertCircle className="w-6 h-6 text-red-600" />
                </div>
                <div className="ml-3">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                    Delete Template
                  </h3>
                </div>
              </div>
              
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
                Are you sure you want to delete "{selectedTemplate.name}"? This action cannot be undone.
              </p>
              
              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => setShowDeleteModal(false)}
                  className="px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDelete}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Templates; 